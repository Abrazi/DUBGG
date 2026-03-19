"""
generator_sim.py
================
Orchestration layer for the DUBGG Modbus simulation.

Individual device logic lives in dedicated modules:
  - generator.py   — GeneratorController (+ shared constants/helpers)
  - switchgear.py  — SwitchgearController
  - Loadbank.py    — LoadBankSimulator

This file is responsible for:
  - IP address maps
  - LoadBankController  (thin bridge to LoadBankSimulator)
  - IndividualModbusServer  (per-device TCP server + simulation loop)
  - ModbusTCPSlaveGenRun   (top-level orchestrator)
  - main() entry point
"""

import logging
import threading
import time
import socket
from typing import Optional, List
from pymodbus.server import StartAsyncTcpServer  # noqa: F401  (kept for compatibility)
try:
    from Loadbank import LoadBankSimulator, LoadBankController
except ImportError:
    pass

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusDeviceContext, ModbusServerContext
import asyncio
import os
import subprocess
import tempfile
import platform
from utils.network_utils import NetworkUtils, NetworkScriptGenerator

# ---------------------------------------------------------------------------
# Re-export symbols used by api_server.py so that existing imports continue
# to work without any changes to api_server.py.
# ---------------------------------------------------------------------------
from generator import (          # noqa: F401
    GeneratorController,
    GeneratorState,
    StateMachine,
    STATE_MAP,
    VOLTAGE_EPSILON,
    FREQUENCY_EPSILON,
    POWER_EPSILON,
    DEAD_BUS_WINDOW_MS,
    VERBOSE,
    HEARTBEAT_LOG_LEVEL,
    LOG_LEVEL,
)
from switchgear import SwitchgearController  # noqa: F401
try:
    from Loadbank import LoadBankController  # noqa: F401
except ImportError:
    pass

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# IP address maps
# ---------------------------------------------------------------------------
GEN_IP_MAP = {
    "G1": "172.16.31.13", "G2": "172.16.31.23", "G3": "172.16.31.33", "G4": "172.16.31.43", "G5": "172.16.31.53",
    "G6": "172.16.32.13", "G7": "172.16.32.23", "G8": "172.16.32.33", "G9": "172.16.32.43", "G10": "172.16.32.53",
    "G11": "172.16.33.13", "G12": "172.16.33.23", "G13": "172.16.33.33", "G14": "172.16.33.43", "G15": "172.16.33.53",
    "G16": "172.16.34.13", "G17": "172.16.34.23", "G18": "172.16.34.33", "G19": "172.16.34.43", "G20": "172.16.34.53",
    "G21": "172.16.35.13", "G22": "172.16.35.23"
}

SWG_IP_MAP = {
    "GPS1": "172.16.31.63", "GPS2": "172.16.32.63", "GPS3": "172.16.33.63", "GPS4": "172.16.34.63"
}

LB_IP_MAP = {
    "LB1": "172.16.11.71", "LB2": "172.16.12.71", "LB3": "172.16.13.71", "LB4": "172.16.14.71"
}


# ---------------------------------------------------------------------------
# Per-device Modbus TCP server + simulation loop
# ---------------------------------------------------------------------------
class IndividualModbusServer:
    """Individual Modbus TCP server for a single generator or switchgear"""
    def __init__(self, name: str, ip_address: str, port: int, controller):
        self.name = name
        self.ip_address = ip_address
        self.port = port
        self.controller = controller
        self.datastore: Optional[ModbusDeviceContext] = None
        self.context: Optional[ModbusServerContext] = None
        self.running = False
        self.datastore_lock = threading.Lock()
        # Device failure simulation: when True the TCP listener is offline
        self.modbus_disabled = False
        self._server_loop: Optional[asyncio.AbstractEventLoop] = None
        self._server_task: Optional[asyncio.Task] = None
        self._server_thread: Optional[threading.Thread] = None
        self._server_stop_event = threading.Event()
        self._server_ready_event = threading.Event()  # Signals when server is actually listening
        self._server_startup_error: Optional[str] = None  # Tracks startup errors

    def _initialize_registers(self) -> ModbusDeviceContext:
        num_registers = 2000
        hr = ModbusSequentialDataBlock(0, [0] * num_registers)
        store = ModbusDeviceContext(
            di=ModbusSequentialDataBlock(0, [0] * num_registers),
            co=ModbusSequentialDataBlock(0, [0] * num_registers),
            hr=hr,
            ir=ModbusSequentialDataBlock(0, [0] * num_registers)
        )
        # Initialize command registers to 0
        store.setValues(3, 95, [0])   # R095 - Fault simulation flags
        store.setValues(3, 192, [0])  # R192 - Command word
        return store

    async def _run_server_async(self):
        # create the server ourselves so we can keep a handle for shutdown
        if self.context is None:
            raise RuntimeError("Server context not initialized")
        logger.info(f"Starting Modbus server for {self.name} on {self.ip_address}:{self.port}")
        from pymodbus.server import ModbusTcpServer
        server = ModbusTcpServer(self.context, address=(self.ip_address, self.port))
        # store to instance so disable_modbus can close it
        self._pymodbus_server = server
        try:
            await server.serve_forever()
        except Exception as e:
            # Clear ready flag if startup fails
            self._server_ready_event.clear()
            self._server_startup_error = str(e)
            raise
        finally:
            self._pymodbus_server = None

    def _check_port_ready(self):
        """Check if the server port is actually open and listening. Returns True when ready."""
        max_attempts = 30  # Maximum 3 seconds of checking (30 × 100ms)
        for attempt in range(max_attempts):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.1)
                    result = s.connect_ex((self.ip_address, self.port))
                    if result == 0:
                        logger.info(f"[{self.name}] ✓ Port {self.port} confirmed OPEN on {self.ip_address} (attempt {attempt + 1})")
                        return True
                    else:
                        logger.debug(f"[{self.name}] Port check {attempt + 1}/{max_attempts}: connection refused/not ready")
            except Exception as e:
                logger.debug(f"[{self.name}] Port check exception (attempt {attempt + 1}): {type(e).__name__}: {e}")
            time.sleep(0.1)
        logger.error(f"[{self.name}] ✗ Port {self.port} on {self.ip_address} failed to open after {max_attempts} attempts ({max_attempts * 0.1:.1f}s)")
        return False

    def _run_server_thread(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._server_loop = loop
            try:
                self._server_task = loop.create_task(self._run_server_async())

                # Start a separate thread to monitor port readiness
                def monitor_port():
                    logger.debug(f"[{self.name}] Port monitor starting - checking for server on {self.ip_address}:{self.port}")
                    try:
                        if self._check_port_ready():
                            self._server_ready_event.set()
                            logger.info(f"[{self.name}] ✓ Port monitor: Server READY - port is open and accepting connections")
                        else:
                            logger.error(f"[{self.name}] ✗ Port monitor: Server FAILED - port never became open")
                            self._server_startup_error = "Port binding failed - port never became accessible"
                            # Cancel the task if port didn't open
                            if self._server_task and not self._server_task.done():
                                try:
                                    loop.call_soon_threadsafe(self._server_task.cancel)
                                    logger.debug(f"[{self.name}] Cancelled server task due to port check failure")
                                except Exception as e:
                                    logger.debug(f"[{self.name}] Error cancelling task: {e}")
                    except Exception as e:
                        logger.error(f"[{self.name}] Port monitor exception: {e}")
                        self._server_startup_error = f"Port monitor error: {str(e)}"

                port_monitor = threading.Thread(target=monitor_port, daemon=True, name=f"PortMonitor-{self.name}")
                port_monitor.start()
                logger.debug(f"[{self.name}] Port monitor thread started")

                loop.run_until_complete(self._server_task)
            except asyncio.CancelledError:
                logger.info(f"[{self.name}] Modbus TCP server stopped (device disabled)")
                self._server_ready_event.clear()
            except Exception as e:
                self._server_ready_event.clear()
                self._server_startup_error = str(e)
                if not self.modbus_disabled:
                    logger.error(f"[{self.name}] Server startup error: {e}")
                else:
                    logger.debug(f"[{self.name}] Server error during shutdown (expected): {e}")
            finally:
                # make sure any outstanding async generators finish
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception as e:
                    logger.debug(f"[{self.name}] Error closing loop: {e}")
                self._server_loop = None
                self._server_task = None
        finally:
            self._server_stop_event.set()

    def _simulation_loop(self):
        while self.running:
            if self.datastore is None:
                time.sleep(0.1)
                continue
            try:
                with self.datastore_lock:
                    if hasattr(self.controller, 'tick'):
                        if isinstance(self.controller, GeneratorController):
                            self.controller.tick(self.datastore)
                        elif isinstance(self.controller, SwitchgearController):
                            # Switchgear needs generator list - will be set by parent
                            pass
                        elif isinstance(self.controller, LoadBankController):
                            self.controller.tick(self.datastore)
            except Exception as e:
                logger.error(f"Simulation error for {self.name}: {e}", exc_info=True)
            time.sleep(0.1)

    def disable_modbus(self):
        """Stop the TCP listener to simulate device failure. Simulation keeps running."""
        if self.modbus_disabled:
            logger.info(f"[{self.name}] Modbus already disabled")
            return
        self.modbus_disabled = True
        logger.info(f"[{self.name}] Simulating device failure: stopping Modbus TCP server")

        # Ask the async server to shut down cleanly via its own object reference.
        loop = self._server_loop
        task = self._server_task
        if loop:
            def _shutdown_server():
                try:
                    srv = self._pymodbus_server
                    if srv:
                        logger.debug(f"[{self.name}] Calling pymodbus server.shutdown()")
                        loop.create_task(srv.shutdown())
                except Exception as e:
                    logger.debug(f"[{self.name}] Error scheduling server shutdown: {e}")
            try:
                loop.call_soon_threadsafe(_shutdown_server)
            except Exception as e:
                logger.debug(f"[{self.name}] Could not schedule server shutdown: {e}")

        if loop and task and not task.done():
            try:
                logger.debug(f"[{self.name}] Cancelling server task as fallback...")
                loop.call_soon_threadsafe(task.cancel)
                # also stop the loop in case the task is stuck in accept
                try:
                    loop.call_soon_threadsafe(loop.stop)
                except Exception:
                    pass
            except Exception as e:
                logger.debug(f"[{self.name}] Error cancelling task: {e}")
            # wait for the helper thread to signal it has cleaned up
            if not self._server_stop_event.wait(timeout=5.0):
                logger.warning(f"[{self.name}] Server thread did not exit within 5 seconds after cancel/shutdown")
            # also join the thread to be absolutely sure
            if self._server_thread and self._server_thread.is_alive():
                try:
                    self._server_thread.join(timeout=1.0)
                except Exception:
                    pass
        else:
            logger.debug(f"[{self.name}] No active task to cancel (loop={loop is not None}, task={task is not None}, done={task.done() if task else 'N/A'})")

        # Clear the ready event to indicate server is now offline
        self._server_ready_event.clear()
        logger.debug(f"[{self.name}] Cleared ready event")

    def enable_modbus(self):
        """Restart the TCP listener after a simulated device failure."""
        if not self.modbus_disabled:
            logger.info(f"[{self.name}] Modbus already enabled")
            return

        logger.info(f"[{self.name}] Enabling device: restarting Modbus TCP server on {self.ip_address}:{self.port}")

        # Force kill old thread if it exists (stronger cleanup)
        old_thread = self._server_thread
        if old_thread and old_thread.is_alive():
            logger.debug(f"[{self.name}] Stopping old server thread...")
            # Cancel the running task to force thread exit
            old_loop = self._server_loop
            old_task = self._server_task
            if old_loop and old_task and not old_task.done():
                try:
                    old_loop.call_soon_threadsafe(old_task.cancel)
                except Exception as e:
                    logger.debug(f"[{self.name}] Could not cancel old task: {e}")

            # Wait for thread with longer timeout
            if not self._server_stop_event.wait(timeout=5.0):
                logger.warning(f"[{self.name}] Old thread still alive after 5s - forcing ahead")

        # Before attempting to bind again, wait until the old socket isn't stuck in CLOSE_WAIT.
        logger.debug(f"[{self.name}] Waiting for OS to release port {self.port} (no CLOSE_WAIT or TIME_WAIT)...")
        start = time.time()
        while True:
            try:
                import psutil
                conns = [c for c in psutil.net_connections(kind='inet')
                         if c.laddr and c.laddr.ip == self.ip_address and c.laddr.port == self.port
                         and c.status in ('CLOSE_WAIT', 'TIME_WAIT')]
                if not conns:
                    break
            except Exception:
                # if psutil fails just fall back to a simple sleep
                pass
            if time.time() - start > 5.0:
                logger.debug(f"[{self.name}] timed out waiting for CLOSE_WAIT/TIME_WAIT to clear")
                break
            time.sleep(0.1)
        # additional fixed delay as a safety
        time.sleep(0.2)

        # Re-create context from existing datastore
        if self.datastore is not None:
            self.context = ModbusServerContext(devices={1: self.datastore}, single=False)

        # Reset the stop event and ready event for the new thread
        self._server_stop_event.clear()
        self._server_ready_event.clear()
        self._server_startup_error = None

        # Start new server thread
        new_thread = threading.Thread(
            target=self._run_server_thread,
            daemon=True,
            name=f"Server-{self.name}"
        )
        self._server_thread = new_thread
        new_thread.start()
        logger.debug(f"[{self.name}] New server thread started, waiting for server to bind (up to 10 seconds)...")

        # Wait for server to be ready (with 10-second timeout to account for port checking + startup)
        if self._server_ready_event.wait(timeout=10.0):
            # initial success; verify thread is still alive and port remains open briefly
            time.sleep(0.5)  # Longer wait to ensure server is stable
            still_running = self._server_thread and self._server_thread.is_alive()
            port_ok = False
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.1)
                    port_ok = s.connect_ex((self.ip_address, self.port)) == 0
            except Exception:
                port_ok = False

            if still_running and port_ok and not self._server_startup_error:
                self.modbus_disabled = False
                logger.info(f"[{self.name}] ✓ Modbus device ENABLED - server is listening on {self.ip_address}:{self.port}")
                # Verify loop is still running
                try:
                    loop_ok = self._server_loop is not None and self._server_loop.is_running()
                    logger.info(f"[{self.name}] Server loop running: {loop_ok}")
                except Exception as e:
                    logger.debug(f"[{self.name}] Could not check loop status: {e}")
                # Diagnostic: log all listeners on this port
                try:
                    import psutil
                    conns = psutil.net_connections(kind='inet')
                    for c in conns:
                        if c.laddr and c.laddr.port == self.port:
                            logger.debug(f"[{self.name}] LISTENER: {c.laddr} status={c.status}")
                except Exception as e:
                    logger.debug(f"[{self.name}] net_connections failed: {e}")
            else:
                # Something went wrong after initial ready event
                reason = self._server_startup_error or "server thread exited or port closed immediately"
                logger.error(f"[{self.name}] ✗ Server appeared to start but then failed: {reason}")
                logger.error(f"[{self.name}]   Thread alive: {still_running}, Port open: {port_ok}, Error: {self._server_startup_error}")
                self.modbus_disabled = True
                logger.error(f"[{self.name}] Device REMAINS OFFLINE after failed startup check")
        else:
            # Server failed to start within timeout
            error_msg = self._server_startup_error or "Server binding timeout - port check exceeded 10 seconds"
            logger.error(f"[{self.name}] ✗ FAILED to enable Modbus server: {error_msg}")
            self.modbus_disabled = True  # Keep disabled if startup failed
            logger.error(f"[{self.name}] Device REMAINS OFFLINE due to startup failure. Check if IP {self.ip_address} is available on network.")

    def start(self):
        self.datastore = self._initialize_registers()
        self.context = ModbusServerContext(devices={1: self.datastore}, single=False)
        self.running = True
        self._server_stop_event.clear()
        self._server_ready_event.clear()
        self._server_startup_error = None
        self._server_thread = threading.Thread(target=self._run_server_thread, daemon=True, name=f"Server-{self.name}")
        self._server_thread.start()
        threading.Thread(target=self._simulation_loop, daemon=True, name=f"Sim-{self.name}").start()
        logger.info(f"✓ {self.name} started on {self.ip_address}:{self.port}")

    def stop(self):
        self.running = False
        loop = self._server_loop
        task = self._server_task
        if loop and task and not task.done():
            try:
                loop.call_soon_threadsafe(task.cancel)
            except Exception as e:
                logger.debug(f"[{self.name}] Error cancelling task during stop: {e}")


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------
class ModbusTCPSlaveGenRun:
    def __init__(self, port: int = 502, num_generators: int = 22, scan_interval: float = 0.1):
        self.port = port
        self.scan_interval = scan_interval
        self.running = False
        self.generators: List[GeneratorController] = []
        self.switchgears: List[SwitchgearController] = []
        self.loadbanks: List[LoadBankController] = []
        self.servers: List[IndividualModbusServer] = []

        # Create generators with register base 0 (each has own server)
        for i in range(1, num_generators + 1):
            gen_id = f"G{i}"
            ip_address = GEN_IP_MAP.get(gen_id, "127.0.0.1")
            gen = GeneratorController(gen_id, register_base=0, ip_address=ip_address)
            self.generators.append(gen)

            # Create individual server for this generator
            server = IndividualModbusServer(gen_id, ip_address, self.port, gen)
            self.servers.append(server)

        # Create switchgears with register base 0 (each has own server)
        for i in range(1, 5):
            gps_id = f"GPS{i}"
            ip_address = SWG_IP_MAP.get(gps_id, "127.0.0.1")
            swg = SwitchgearController(gps_id, register_base=0, ip_address=ip_address)
            self.switchgears.append(swg)

            # Create individual server for this switchgear
            server = IndividualModbusServer(gps_id, ip_address, self.port, swg)
            self.servers.append(server)

        # Create loadbanks with register base 0 (each has own server)
        for i in range(1, 5):
            lb_id = f"LB{i}"
            ip_address = LB_IP_MAP.get(lb_id, "127.0.0.1")
            lb = LoadBankController(lb_id, register_base=0, ip_address=ip_address)
            self.loadbanks.append(lb)

            # Create individual server for this loadbank
            server = IndividualModbusServer(lb_id, ip_address, self.port, lb)
            self.servers.append(server)

        logger.info(f"Initialized {len(self.generators)} generators, {len(self.switchgears)} switchgears, and {len(self.loadbanks)} load banks")

    def _global_simulation_loop(self):
        """Coordinate switchgear logic across all generators"""
        while self.running:
            try:
                for swg_server in [s for s in self.servers if isinstance(s.controller, SwitchgearController)]:
                    if swg_server.datastore:
                        with swg_server.datastore_lock:
                            swg_server.controller.tick(self.generators, swg_server.datastore)
            except Exception as e:
                logger.error(f"Global simulation error: {e}", exc_info=True)
            time.sleep(self.scan_interval)

    def check_network_availability(self) -> bool:
        """
        Checks if the required IPs are available on the network or on the local computer.
        Logs errors if an IP is occupied by another device on the network.
        Asks user to select an adapter to add missing IPs.
        """
        all_ips = list(GEN_IP_MAP.values()) + list(SWG_IP_MAP.values()) + list(LB_IP_MAP.values())
        unique_ips = sorted(list(set(all_ips)))

        try:
            local_interfaces = NetworkUtils.get_network_interfaces()
        except Exception as e:
            logger.error(f"Failed to get network interfaces: {e}")
            return True  # Proceed anyway, maybe it works

        local_ips = []
        for iface in local_interfaces:
            if hasattr(iface, 'all_ips'):
                local_ips.extend(iface.all_ips)
            else:
                local_ips.append(iface.ip_address)

        ips_to_add = []
        occupied_on_network = []

        logger.info("Checking network availability for simulation IPs...")
        for ip in unique_ips:
            if ip == "127.0.0.1" or ip == "0.0.0.0":
                continue

            is_local = ip in local_ips

            # Check if reachable on network
            is_reachable = NetworkUtils.check_host_reachable(ip)

            if is_reachable and not is_local:
                logger.error(f"IP {ip} is available on network but NOT on this computer. This IP is NOT available for simulation!")
                occupied_on_network.append(ip)
            elif not is_reachable and not is_local:
                ips_to_add.append(ip)

        if occupied_on_network:
            print(f"\nCRITICAL: The following IPs are occupied by other devices on the network:")
            for ip in occupied_on_network:
                print(f" - {ip}")
            print("These IPs will not be able to host Modbus servers on this machine.\n")

        if ips_to_add:
            print(f"\nThe following IP addresses are missing from this computer and need to be added:")
            for ip in ips_to_add:
                print(f" - {ip}")

            print(f"\nAvailable Network Adapters:")
            # Filter for interfaces that are up and have an IP (ignoring loopback if possible)
            valid_ifaces = [i for i in local_interfaces if i.is_up and i.ip_address != "127.0.0.1"]
            if not valid_ifaces:
                valid_ifaces = local_interfaces

            for i, iface in enumerate(valid_ifaces):
                print(f"{i+1}. {iface.name} (Current IP: {iface.ip_address})")

            while True:
                choice = input(f"\nSelect adapter number to add these IPs (1-{len(valid_ifaces)}) or 's' to skip/cancel: ")
                if choice.lower() == 's':
                    logger.warning("Network adapter selection skipped by user.")
                    return True  # Continue anyway

                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(valid_ifaces):
                        selected_adapter = valid_ifaces[idx].name
                        return self.add_ips_to_adapter(ips_to_add, selected_adapter)
                    else:
                        print(f"Please enter a number between 1 and {len(valid_ifaces)}")
                except ValueError:
                    print("Invalid input. Please enter a number or 's'.")

        return True

    def add_ips_to_adapter(self, ips: List[str], adapter_name: str) -> bool:
        """Generates and runs a script to add IPs to the selected adapter."""
        logger.info(f"Adding {len(ips)} IP addresses to adapter '{adapter_name}'...")
        system = platform.system().lower()

        if system == "windows":
            script_content = NetworkScriptGenerator.generate_windows_batch(ips, adapter_name)
            ext = ".bat"
        else:
            script_content = NetworkScriptGenerator.generate_linux_script(ips, adapter_name)
            ext = ".sh"

        # Write script to temporary file
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"scada_scout_network_config{ext}")

        try:
            with open(temp_path, "w") as f:
                f.write(script_content)

            if system == "windows":
                # Execute as administrator using PowerShell Start-Process
                ps_cmd = f"Start-Process cmd -ArgumentList '/c', '{temp_path}' -Verb RunAs -Wait"
                logger.info("Triggering Windows UAC elevation prompt for network configuration...")
                result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
            else:
                # On Linux, make it executable and run with pkexec or sudo
                os.chmod(temp_path, 0o755)
                if os.path.exists("/usr/bin/pkexec"):
                    cmd = ["pkexec", temp_path]
                else:
                    cmd = [temp_path]

                logger.info("Running network configuration script...")
                result = subprocess.run(cmd, capture_output=True)

            if result.returncode == 0:
                logger.info("IP addition script completed successfully.")
                # Brief pause to let OS catch up
                time.sleep(1)
                return True
            else:
                stderr = result.stderr.decode(errors='ignore')
                stdout = result.stdout.decode(errors='ignore')
                logger.error(f"Failed to run configuration command. RC: {result.returncode}")
                if stderr: logger.error(f"Stderr: {stderr}")
                if stdout: logger.debug(f"Stdout: {stdout}")
                return False
        except Exception as e:
            logger.error(f"Error while adding IP addresses: {e}")
            return False
        finally:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    def start(self):
        # Check network availability before starting servers
        self.check_network_availability()

        self.running = True
        logger.info("Starting all Modbus TCP servers...")

        # Start all individual servers
        for server in self.servers:
            server.start()
            time.sleep(0.1)  # Small delay between server starts

        # Start global coordination loop
        threading.Thread(target=self._global_simulation_loop, daemon=True, name="GlobalSim").start()

        logger.info(f"✓ All {len(self.servers)} servers started successfully")

    def stop(self):
        self.running = False
        logger.info("Stopping all servers...")
        for server in self.servers:
            server.stop()


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s:%(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    slave = ModbusTCPSlaveGenRun()
    try:
        slave.start()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        slave.stop()


if __name__ == "__main__":
    main()
