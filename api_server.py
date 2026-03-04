import asyncio
import collections
import logging
import threading
import time
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import the simulation logic from the file containing your provided code
# Ensure your provided code is saved as 'generator_sim.py'
try:
    from generator_sim import ModbusTCPSlaveGenRun, GeneratorState
except ImportError:
    print("Error: Could not import 'generator_sim'. Please save the provided code as 'generator_sim.py'")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d %(levelname)s:%(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Generator HMI API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    # Allow all localhost / 127.0.0.1 origins (dev vite server or packaged EXE)
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from typing import Any

# Global simulation instance (initialized to None until started)
sim_instance: Any = None

# Per-generator circular log buffers  {gen_id: deque of log dicts}
GEN_LOG_BUFFERS: dict = {}
GEN_LOG_LOCK = threading.Lock()
MAX_LOG_ENTRIES = 200


class GenLogHandler(logging.Handler):
    """Custom logging handler that captures generator-specific log messages
    into per-generator circular buffers."""

    def emit(self, record: logging.LogRecord):
        msg = record.getMessage()
        # Generator log messages start with [G<id>] – extract gen_id
        if msg.startswith('['):
            end = msg.find(']')
            if end > 0:
                gen_id = msg[1:end]
                entry = {
                    "timestamp": datetime.utcfromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    "level": record.levelname,
                    "message": msg,
                }
                with GEN_LOG_LOCK:
                    if gen_id not in GEN_LOG_BUFFERS:
                        GEN_LOG_BUFFERS[gen_id] = collections.deque(maxlen=MAX_LOG_ENTRIES)
                    GEN_LOG_BUFFERS[gen_id].append(entry)


# Install the custom handler on the root logger so it captures everything
_gen_log_handler = GenLogHandler()
_gen_log_handler.setLevel(logging.DEBUG)
logging.getLogger().addHandler(_gen_log_handler)

class CommandRequest(BaseModel):
    command: str  # 'start','stop','reset_fault','open_breaker','close_breaker','inject_fault','deexcite_on','deexcite_off'


class ConfigRequest(BaseModel):
    simulate_fail_to_start: Optional[bool] = None
    fail_ramp_up: Optional[bool] = None
    fail_ramp_down: Optional[bool] = None
    fail_start_time: Optional[bool] = None
    start_delay: Optional[int] = None
    stop_delay: Optional[int] = None
    # allow service mode change: 'off','manual','auto'
    service_mode: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global sim_instance
    logger.info("Initializing Generator Simulation...")
    # Initialize simulation (disable network check for local dev if needed)
    sim_instance = ModbusTCPSlaveGenRun(port=502, num_generators=22)
    
    # Start simulation in a separate thread so it doesn't block FastAPI
    def run_sim():
        sim_instance.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sim_instance.stop()
            
    sim_thread = threading.Thread(target=run_sim, daemon=True)
    sim_thread.start()
    logger.info("Simulation started and API server ready.")

@app.get("/generators")
def get_generators():
    """Get status of all generators"""
    if not sim_instance:
        return []
    
    gen_list = []
    for gen in sim_instance.generators:
        # Map internal state to string
        state_str = gen.sm.state
        # determine service mode
        if gen.SSL['SSL425_ServiceSWOff']:
            svc_mode = 'off'
        elif gen.SSL['SSL426_ServiceSWManual']:
            svc_mode = 'manual'
        else:
            svc_mode = 'auto'
        
        gen_list.append({
            "id": gen.id,
            "state": state_str,
            "voltage": round(gen.SimulatedVoltage, 2),
            "frequency": round(gen.SimulatedFrequency, 2),
            "activePower": round(gen.SimulatedActivePower, 2),
            "reactivePower": round(gen.SimulatedReactivePower, 2),
            "current": round(gen.SimulatedCurrent, 2),
            "breakerClosed": gen.SSL['SSL429_GenCBClosed'],
            "isRunning": gen.state == GeneratorState.RUNNING,
            "isFaulted": gen.state == GeneratorState.FAULT,
            # simulation options exposed
            "simulateFailToStart": gen.SimulateFailToStart,
            "failRampUp": gen.FailRampUp,
            "failRampDown": gen.FailRampDown,
            "failStartTime": gen.FailStartTime,
            "startDelay": gen.StartDelay,
            "stopDelay": gen.StopDelay,
            "deexcited": gen.SSL['SSL547_GenDeexcited'],
            "serviceMode": svc_mode,
        })
    return gen_list

@app.get("/generators/{gen_id}")
def get_generator(gen_id: str):
    """Get status of a specific generator"""
    if not sim_instance:
        return None
    for gen in sim_instance.generators:
        if gen.id == gen_id:
            # determine service mode
            if gen.SSL['SSL425_ServiceSWOff']:
                svc_mode = 'off'
            elif gen.SSL['SSL426_ServiceSWManual']:
                svc_mode = 'manual'
            else:
                svc_mode = 'auto'

            return {
                "id": gen.id,
                "state": gen.sm.state,
                "voltage": round(gen.SimulatedVoltage, 2),
                "frequency": round(gen.SimulatedFrequency, 2),
                "activePower": round(gen.SimulatedActivePower, 2),
                "reactivePower": round(gen.SimulatedReactivePower, 2),
                "current": round(gen.SimulatedCurrent, 2),
                "breakerClosed": gen.SSL['SSL429_GenCBClosed'],
                "isRunning": gen.state == GeneratorState.RUNNING,
                "isFaulted": gen.state == GeneratorState.FAULT,
                "simulateFailToStart": gen.SimulateFailToStart,
                "failRampUp": gen.FailRampUp,
                "failRampDown": gen.FailRampDown,
                "failStartTime": gen.FailStartTime,
                "startDelay": gen.StartDelay,
                "stopDelay": gen.StopDelay,
                "deexcited": gen.SSL['SSL547_GenDeexcited'],
                "serviceMode": svc_mode,
            }
    return None

@app.post("/generators/{gen_id}/command")
def send_command(gen_id: str, req: CommandRequest):
    """Send control command to a specific generator"""
    if not sim_instance:
        return {"status": "error", "message": "Simulation not running"}
    
    target_gen = next((g for g in sim_instance.generators if g.id == gen_id), None)
    if not target_gen:
        return {"status": "error", "message": "Generator not found"}
    
    with target_gen.lock:
        if req.command == "start":
            # Set Demand Module Command (Bit 0 of R192)
            target_gen.SSL['SSL701_DemandModule_CMD'] = True
            logger.info(f"[{gen_id}] Start Command Sent")
        elif req.command == "stop":
            # Clear Demand Module Command
            target_gen.SSL['SSL701_DemandModule_CMD'] = False
            logger.info(f"[{gen_id}] Stop Command Sent")
        elif req.command == "reset_fault":
            # Set Reset Fault Bit (Bit 4 of R095)
            # Note: In the simulation logic, this clears faultDetected
            target_gen.faultDetected = False
            target_gen.sm.fire("faultCleared")
            logger.info(f"[{gen_id}] Fault Reset Sent")
        elif req.command == "open_breaker":
            # open circuit breaker
            target_gen.SSL['SSL429_GenCBClosed'] = False
            logger.info(f"[{gen_id}] Breaker opened")
        elif req.command == "close_breaker":
            # allow closing breaker only when service switch is in MANUAL
            if not target_gen.SSL.get('SSL426_ServiceSWManual', False):
                logger.warning(f"[{gen_id}] Close breaker denied - service switch not MANUAL")
                return {"status": "error", "message": "Service switch must be MANUAL to close breaker"}
            target_gen.SSL['SSL429_GenCBClosed'] = True
            target_gen.SSL['SSL430_GenCBOpen'] = False
            logger.info(f"[{gen_id}] Breaker closed")
        elif req.command == "inject_fault":
            target_gen.faultDetected = True
            logger.info(f"[{gen_id}] Fault injected")
        elif req.command == "deexcite_on":
            target_gen.SSL['SSL547_GenDeexcited'] = True
            logger.info(f"[{gen_id}] Deexcitation ON")
            # write R109 to datastore so Modbus clients see the deexcitation bit immediately
            server = next((s for s in sim_instance.servers if s.name == gen_id), None)
            if server and server.datastore:
                try:
                    with server.datastore_lock:
                        R109 = 0
                        if target_gen.SSL.get('SSL545_UtilityOperModuleBlocked'): R109 |= (1 << 0)
                        if target_gen.SSL.get('SSL546_GenBreakerOpenFail'): R109 |= (1 << 1)
                        if target_gen.SSL.get('SSL547_GenDeexcited'): R109 |= (1 << 2)
                        if target_gen.SSL.get('SSL548_PowerReductionActivated'): R109 |= (1 << 3)
                        if target_gen.SSL.get('SSL549_LoadRejectedGCBOpen'): R109 |= (1 << 4)
                        if target_gen.SSL.get('SSL550_GenSyncLoadReleas'): R109 |= (1 << 5)
                        server.datastore.setValues(3, target_gen.register_base + 109, [R109])
                        # Also set SSL709_GenExcitationOff_CMD (R192 bit 8) so simulation honors de-excitation
                        try:
                            r192_list = server.datastore.getValues(3, target_gen.register_base + 192, count=1)
                            current_r192 = r192_list[0] if isinstance(r192_list, list) and len(r192_list) > 0 else 0
                        except Exception:
                            current_r192 = 0
                        new_r192 = current_r192 | (1 << 8)
                        server.datastore.setValues(3, target_gen.register_base + 192, [new_r192])
                except Exception:
                    logger.exception("Failed to write R109 after deexcite_on")
        elif req.command == "deexcite_off":
            target_gen.SSL['SSL547_GenDeexcited'] = False
            logger.info(f"[{gen_id}] Deexcitation OFF")
            server = next((s for s in sim_instance.servers if s.name == gen_id), None)
            if server and server.datastore:
                try:
                    with server.datastore_lock:
                        R109 = 0
                        if target_gen.SSL.get('SSL545_UtilityOperModuleBlocked'): R109 |= (1 << 0)
                        if target_gen.SSL.get('SSL546_GenBreakerOpenFail'): R109 |= (1 << 1)
                        if target_gen.SSL.get('SSL547_GenDeexcited'): R109 |= (1 << 2)
                        if target_gen.SSL.get('SSL548_PowerReductionActivated'): R109 |= (1 << 3)
                        if target_gen.SSL.get('SSL549_LoadRejectedGCBOpen'): R109 |= (1 << 4)
                        if target_gen.SSL.get('SSL550_GenSyncLoadReleas'): R109 |= (1 << 5)
                        server.datastore.setValues(3, target_gen.register_base + 109, [R109])
                        # Also clear SSL709_GenExcitationOff_CMD (R192 bit 8)
                        try:
                            r192_list = server.datastore.getValues(3, target_gen.register_base + 192, count=1)
                            current_r192 = r192_list[0] if isinstance(r192_list, list) and len(r192_list) > 0 else 0
                        except Exception:
                            current_r192 = 0
                        new_r192 = current_r192 & ~(1 << 8)
                        server.datastore.setValues(3, target_gen.register_base + 192, [new_r192])
                except Exception:
                    logger.exception("Failed to write R109 after deexcite_off")
            
    return {"status": "success", "message": f"Command '{req.command}' sent to {gen_id}"}

@app.post("/generators/{gen_id}/config")
def update_config(gen_id: str, cfg: ConfigRequest):
    """Update simulation options for a specific generator"""
    if not sim_instance:
        return {"status": "error", "message": "Simulation not running"}
    target_gen = next((g for g in sim_instance.generators if g.id == gen_id), None)
    if not target_gen:
        return {"status": "error", "message": "Generator not found"}
    # apply provided config values and update R095 register for persistence
    if cfg.simulate_fail_to_start is not None:
        target_gen.SimulateFailToStart = cfg.simulate_fail_to_start
        target_gen._override_SimulateFailToStart = True
    if cfg.fail_ramp_up is not None:
        target_gen.FailRampUp = cfg.fail_ramp_up
        target_gen._override_FailRampUp = True
    if cfg.fail_ramp_down is not None:
        target_gen.FailRampDown = cfg.fail_ramp_down
        target_gen._override_FailRampDown = True
    if cfg.fail_start_time is not None:
        target_gen.FailStartTime = cfg.fail_start_time
        target_gen._override_FailStartTime = True
    if cfg.start_delay is not None:
        target_gen.StartDelay = cfg.start_delay
    if cfg.stop_delay is not None:
        target_gen.StopDelay = cfg.stop_delay
    if cfg.service_mode is not None:
        # enforce only one of the three service switches can be true
        target_gen.SSL['SSL425_ServiceSWOff'] = False
        target_gen.SSL['SSL426_ServiceSWManual'] = False
        target_gen.SSL['SSL427_ServiceSWAuto'] = False
        if cfg.service_mode == 'off':
            target_gen.SSL['SSL425_ServiceSWOff'] = True
        elif cfg.service_mode == 'manual':
            target_gen.SSL['SSL426_ServiceSWManual'] = True
        else:
            # default to auto
            target_gen.SSL['SSL427_ServiceSWAuto'] = True

    # also set bits in R095 register so the simulator tick doesn't override our settings
    # find corresponding server for this generator
    server = next((s for s in sim_instance.servers if s.name == gen_id), None)
    if server and server.datastore:
        with server.datastore_lock:
            try:
                r095_list = server.datastore.getValues(3, target_gen.register_base + 95, count=1)
                if isinstance(r095_list, list) and len(r095_list) > 0:
                    val = r095_list[0]
                else:
                    val = 0
            except Exception:
                val = 0
            # helper to set/clear bit
            def setbit(v, bit, flag):
                if flag:
                    return v | (1 << bit)
                else:
                    return v & ~(1 << bit)

            if cfg.simulate_fail_to_start is not None:
                val = setbit(val, 0, cfg.simulate_fail_to_start)
            if cfg.fail_ramp_up is not None:
                val = setbit(val, 1, cfg.fail_ramp_up)
            if cfg.fail_ramp_down is not None:
                val = setbit(val, 2, cfg.fail_ramp_down)
            if cfg.fail_start_time is not None:
                val = setbit(val, 3, cfg.fail_start_time)
            # write back
            server.datastore.setValues(3, target_gen.register_base + 95, [val])

            # Also write immediate R014 status word so Modbus clients see service-switch changes
            try:
                R014 = 0
                if target_gen.SSL.get('SSL425_ServiceSWOff'):
                    R014 |= (1 << 0)
                if target_gen.SSL.get('SSL426_ServiceSWManual'):
                    R014 |= (1 << 1)
                if target_gen.SSL.get('SSL427_ServiceSWAuto'):
                    R014 |= (1 << 2)
                if target_gen.SSL.get('SSL429_GenCBClosed'):
                    R014 |= (1 << 4)
                if target_gen.SSL.get('SSL430_GenCBOpen'):
                    R014 |= (1 << 5)
                if target_gen.SSL.get('SSL431_OperOn'):
                    R014 |= (1 << 6)
                if target_gen.SSL.get('SSL432_OperOff'):
                    R014 |= (1 << 7)
                if target_gen.SSL.get('SSL449_OperEngineisRunning'):
                    R014 |= (1 << 8)
                if target_gen.SSL.get('SSL441_SyncGenActivated'):
                    R014 |= (1 << 9)
                if target_gen.SSL.get('SSL435_MainsCBClosed'):
                    R014 |= (1 << 10)
                if target_gen.SSL.get('SSL452_GeneralTrip'):
                    R014 |= (1 << 11)
                if target_gen.SSL.get('SSL437_TurboChUnitGeneralTrip'):
                    R014 |= (1 << 12)
                if target_gen.SSL.get('SSL438_TurboChUnitGeneralWarn'):
                    R014 |= (1 << 13)
                if target_gen.SSL.get('SSL439_IgnSysGeneralTrip'):
                    R014 |= (1 << 14)
                if target_gen.SSL.get('SSL440_IgnSysGeneralWarn'):
                    R014 |= (1 << 15)
                server.datastore.setValues(3, target_gen.register_base + 14, [R014])
            except Exception:
                pass

    return {"status": "success", "message": f"Config updated for {gen_id}"}


@app.get("/generators/{gen_id}/logs")
def get_generator_logs(gen_id: str, limit: int = 100):
    """Return recent log entries for a specific generator."""
    with GEN_LOG_LOCK:
        buf = GEN_LOG_BUFFERS.get(gen_id)
        if buf is None:
            return []
        entries = list(buf)
    # Return newest-first, up to `limit`
    return list(reversed(entries[-limit:]))


if __name__ == "__main__":
    import uvicorn
    # Disable uvicorn access log to avoid noisy per-request INFO lines
    uvicorn.run(app, host="0.0.0.0", port=8000, access_log=False)