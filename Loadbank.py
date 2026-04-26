import time
import logging
import threading
from typing import List, Dict, Optional
from pymodbus.datastore import ModbusDeviceContext

logger = logging.getLogger(__name__)

class LoadBankSimulator:
    def __init__(self):
        # Initialize registers according to the manual
        self.registers = {}
        
        # Initialize all register values based on typical load bank specifications
        self._initialize_registers()
        
        # Simulation state variables
        self.control_on = True
        self.load_applied = 0.0
        self.inductive_load_applied = 0.0
        self.capacitive_load_applied = 0.0
        
    def _initialize_registers(self):
        """Initialize all registers with default values based on the manual"""
        
        # Instrumentation registers (1000-1023)
        self.registers[1000] = 0      # Timestamp
        self.registers[1001] = 2300   # L1N Peak Voltage (230.0V * 10)
        self.registers[1002] = 2300   # L1N Voltage (230.0V * 10)
        self.registers[1003] = 2300   # L2N Voltage
        self.registers[1004] = 2300   # L3N Voltage
        self.registers[1005] = 4000   # L1L2 Voltage (400.0V * 10)
        self.registers[1006] = 4000   # L2L3 Voltage
        self.registers[1007] = 4000   # L3L1 Voltage
        self.registers[1008] = 00     # L1 Active Current (5.0A * 10)
        self.registers[1009] = 00     # L2 Active Current
        self.registers[1010] = 00     # L3 Active Current
        self.registers[1011] = 0      # L1 Reactive Current
        self.registers[1012] = 0      # L2 Reactive Current
        self.registers[1013] = 0      # L3 Reactive Current
        self.registers[1014] = 5000   # Frequency (50.0Hz * 100)
        self.registers[1015] = 0     # L1 Apparent Current (5.7A * 10)
        self.registers[1016] = 0     # L2 Apparent Current
        self.registers[1017] = 0     # L3 Apparent Current
        self.registers[1018] = 0    # Total Active Power (12.0kW * 10)
        self.registers[1019] = 0      # Total Reactive Power
        self.registers[1020] = 0    # Total Apparent Power (13.0kVA * 10)
        self.registers[1021] = 0     # Power Factor (0.92 * 100)
        self.registers[1022] = 2300   # Peak VL1N Voltage
        self.registers[1023] = 4000   # Peak VL1L2 Voltage
        
        # Load Bank Status registers (1100-1104)
        self.registers[1100] = 0x039F  # Status bits
        self.registers[1101] = 0x0000  # Error status bits
        self.registers[1102] = 0x00    # LED status (not running)
        
        # Load Capacity registers (1200-1205)
        self.registers[1200] = 50      # kWStep (5.0kW * 10)
        self.registers[1201] = 50      # kVArLStep
        self.registers[1202] = 50      # kVArCStep
        self.registers[1203] = 1000    # kWMax (100.0kW * 10)
        self.registers[1204] = 1000    # kVArLMax (100.0kVArL * 10)
        self.registers[1205] = 1000    # kVArCMax (100.0kVArC * 10)
        
        # Operating Voltage and Frequency registers (1300-1302)
        self.registers[1300] = 2300    # Operating Voltage (230.0V * 10)
        self.registers[1301] = 5000    # Operating Frequency (50.0Hz * 100)
        self.registers[1302] = 0       # Unused or reserved
        
        # Load Bank ID registers (1400-1406)
        self.registers[1400] = 0x01    # Station Number
        self.registers[1401] = 0x800F  # Configuration bits (resistive, inductive, capacitive load available)
        self.registers[1402] = 2300    # Nominal Voltage (230.0V * 10)
        self.registers[1403] = 5000    # Nominal Frequency (50.0Hz * 100)
        self.registers[1404] = 4800    # Max Voltage (480.0V * 10)
        self.registers[1405] = 0       # Reserved
        self.registers[1406] = 0       # Reserved
        
        # Inputs and Outputs registers (1500-1506)
        self.registers[1500] = 0x00    # Seven Segment Display
        self.registers[1501] = 0x0000  # Output bits (LoadOn, Fan relays etc.)
        self.registers[1502] = 0x0000  # More output bits
        self.registers[1503] = 0x0000  # Even more output bits
        self.registers[1504] = 0       # Reserved
        self.registers[1505] = 0       # Reserved
        self.registers[1506] = 0       # Reserved
        
        # Load Select and Apply registers (1600-1610)
        self.registers[1600] = 0       # W Now - Watts Applied (*10)
        self.registers[1602] = 0       # W Next - Watts Selected (*10)
        self.registers[1604] = 0       # VArL Now - Inductive Load Applied (*10)
        self.registers[1606] = 0       # VArL Next - Inductive Load Selected (*10)
        self.registers[1608] = 0       # VArC Now - Capacitive Load Applied (*10)
        self.registers[1610] = 0       # VArC Next - Capacitive Load Selected (*10)
        
        # Load Control registers (1700-1710)
        self.registers[1700] = 0x8000  # Control bits (Enabled by default)
        self.registers[1701] = 0       # WSelected (*10)
        self.registers[1702] = 0       # VArLSelected (*10)
        self.registers[1703] = 0       # VArCSelected (*10)
        self.registers[1704] = 2300    # Operating Voltage (230.0V * 10)
        self.registers[1705] = 5000    # Operating Frequency (50.0Hz * 100)
        self.registers[1706] = 0       # Reserved
        self.registers[1707] = 0       # Reserved
        self.registers[1708] = 0       # Reserved
        self.registers[1709] = 0       # Reserved
        self.registers[1710] = 0       # Reserved
    
    def read_register(self, address: int) -> int:
        """Read a single register value"""
        return self.registers.get(address, 0) & 0xFFFF
    
    def write_register(self, address: int, value: int) -> bool:
        """Write to a single register (always allow, clamp to 16-bit)"""
        val = value & 0xFFFF
        self.registers[address] = val
        
        # Cross-sync operating voltage and frequency across mapping variants
        if address == 1704 and self.read_register(1300) != val:
            self.write_register(1300, val)
        elif address == 1300 and self.read_register(1704) != val:
            self.write_register(1704, val)
            
        if address == 1705 and self.read_register(1301) != val:
            self.write_register(1301, val)
        elif address == 1301 and self.read_register(1705) != val:
            self.write_register(1705, val)
            
        # Dynamically update instrumentation voltages if operational voltage changes
        if address in (1300, 1704):
            # val is Operating Voltage * 10 (e.g., 4000 for 400V L-L)
            self.registers[1005] = val
            self.registers[1006] = val
            self.registers[1007] = val
            self.registers[1022] = val
            self.registers[1023] = val
            
            # L-N theoretical voltage (L-L / sqrt(3))
            v_ln = int(val / 1.732)
            self.registers[1001] = v_ln
            self.registers[1002] = v_ln
            self.registers[1003] = v_ln
            self.registers[1004] = v_ln
            
            # Re-calculate currents based on new voltage (only if a load is applied)
            if self.load_applied > 0:
                self.apply_load()
                
        # Dynamically update frequency instrumentation
        if address in (1301, 1705):
            self.registers[1014] = val
            
        return True
    
    def read_multiple_registers(self, start_address: int, count: int) -> List[int]:
        """Read multiple consecutive registers"""
        result = []
        for i in range(count):
            result.append(self.read_register(start_address + i))
        return result
    
    def write_multiple_registers(self, start_address: int, values: List[int]) -> bool:
        """Write to multiple consecutive registers"""
        success = True
        for i, value in enumerate(values):
            if not self.write_register(start_address + i, value):
                success = False
        return success
    
    def get_load_status(self) -> Dict:
        """Get current load bank status information"""
        return {
            "load_applied": self.load_applied,
            "inductive_load_applied": self.inductive_load_applied,
            "capacitive_load_applied": self.capacitive_load_applied,
            "control_on": self.control_on,
            "status_bits": self.registers[1100],
            "error_bits": self.registers[1101]
        }
    
    def enable_modbus_control(self):
        """Enable Modbus control (set ControlOn bit)"""
        current_value = self.read_register(1700)
        new_value = (current_value & ~0x4000) | 0x8000  # Clear disable, set enable
        self.write_register(1700, new_value)
        self.control_on = True
        
    def disable_modbus_control(self):
        """Disable Modbus control (set ControlOff bit)"""
        current_value = self.read_register(1700)
        new_value = (current_value & ~0x8000) | 0x4000  # Clear enable, set disable
        self.write_register(1700, new_value)
        self.control_on = False
        
    def select_load(self, resistive_kW: int, inductive_kVAr: int = 0, capacitive_kVAr: int = 0):
        """Select load to be applied. Scaling: register value = kW * 10 (0.1kW resolution)"""
        scale_factor = 10
        w_selected = int(resistive_kW * scale_factor)
        varl_selected = int(inductive_kVAr * scale_factor)
        varc_selected = int(capacitive_kVAr * scale_factor)
        
        self.write_register(1701, w_selected)
        self.write_register(1702, varl_selected) 
        self.write_register(1703, varc_selected)
        
    def apply_load(self):
        """Apply the selected load"""
        if not self.control_on:
            return False
            
        current_value = self.read_register(1700)
        if current_value & 0x08:  # Already accepted, avoid duplicate triggers
            return False
            
        # Read selected load
        w_selected = self.read_register(1701)
        varl_selected = self.read_register(1702)
        varc_selected = self.read_register(1703)
        
        # Validate and clamp against capacity limits
        max_kw = self.read_register(1203)
        max_kvarl = self.read_register(1204)
        max_kvarc = self.read_register(1205)
        
        if w_selected > max_kw:
            w_selected = max_kw
            self.write_register(1701, w_selected)
        if varl_selected > max_kvarl:
            varl_selected = max_kvarl
            self.write_register(1702, varl_selected)
        if varc_selected > max_kvarc:
            varc_selected = max_kvarc
            self.write_register(1703, varc_selected)
            
        # Set Accept bit in control register
        new_value = current_value | 0x08   # Set LoadAccept bit (bit 3)
        self.write_register(1700, new_value)
        
        # Update applied load values (in kW)
        self.load_applied = float(w_selected) / 10.0
        self.inductive_load_applied = float(varl_selected) / 10.0
        self.capacitive_load_applied = float(varc_selected) / 10.0
        
        # Update applied registers (Now = selected, Next remains selected)
        self.write_register(1600, w_selected)  # W Now
        self.write_register(1604, varl_selected)  # VArL Now
        self.write_register(1608, varc_selected)  # VArC Now
        
        # Update instrumentation (scaled consistently)
        self.registers[1018] = w_selected  # Total Active Power *10
        reactive_net = varl_selected - varc_selected
        reactive_abs = abs(reactive_net)
        self.registers[1019] = reactive_abs  # Total Reactive Power *10
        apparent = int((w_selected ** 2 + reactive_abs ** 2) ** 0.5)
        self.registers[1020] = apparent  # Total Apparent Power *10
        pf = int(w_selected * 100 / apparent) if apparent > 0 else 1000
        self.registers[1021] = pf  # Power Factor *100
        
        # Update currents (approximate 3-phase, L-L voltage)
        v_ll = float(self.registers[1005]) / 10.0
        if v_ll <= 0.1:
            v_ll = 400.0  # Safe fallback to prevent ZeroDivisionError
            
        apparent_kva = float(apparent) / 10.0
        pf_val = float(pf) / 100.0
        
        i_app = int((apparent_kva * 1000) / (1.732 * v_ll))  # Apparent current base arithmetic
        i_app_scaled = int(i_app * 10) # 10x scaled resolution 
        i_act = int(i_app_scaled * pf_val)  # Active current scaled
        i_react = int((i_app_scaled ** 2 - i_act ** 2) ** 0.5) # Reactive current scaled
        
        self.registers[1008] = self.registers[1009] = self.registers[1010] = i_act
        self.registers[1015] = self.registers[1016] = self.registers[1017] = i_app_scaled
        self.registers[1011] = self.registers[1012] = self.registers[1013] = i_react
        
        return True
    
    def reject_load(self):
        """Reject all applied load"""
        if not self.control_on:
            return False
            
        # Set Reject bit in control register
        current_value = self.read_register(1700)
        new_value = current_value | 0x04   # Set LoadReject bit (bit 2)
        self.write_register(1700, new_value)
        
        # Clear applied load values
        self.load_applied = 0.0
        self.inductive_load_applied = 0.0
        self.capacitive_load_applied = 0.0
        
        # Update applied registers to zero
        for addr in [1600, 1602, 1604, 1606, 1608, 1610]:
            self.write_register(addr, 0)
        
        # Reset instrumentation to no-load state
        self.registers[1018] = 0
        self.registers[1019] = 0
        self.registers[1020] = 0
        self.registers[1021] = 100  # PF 1.00 *100
        self.registers[1008] = self.registers[1009] = self.registers[1010] = 0
        self.registers[1011] = self.registers[1012] = self.registers[1013] = 0
        self.registers[1015] = self.registers[1016] = self.registers[1017] = 0
        
        return True

# ---------------------------------------------------------------------------
# Load bank controller (thin bridge to LoadBankSimulator)
# ---------------------------------------------------------------------------
class LoadBankController:
    def __init__(self, lb_id: str, register_base: int, ip_address: str = ""):
        self.id = lb_id
        self.register_base = register_base
        self.ip_address = ip_address
        self._last_event_log: Optional[str] = None
        self.simulator = LoadBankSimulator()
        self.lock = threading.Lock()

    def log(self, message: str):
        log_msg = f"[{self.id}] {message}"
        if log_msg != self._last_event_log:
            logger.info(log_msg)
            self._last_event_log = log_msg

    def tick(self, datastore: ModbusDeviceContext):
        with self.lock:
            # First tick initialisation: Push all simulator defaults into the Modbus datastore
            # so we don't mistake uninitialised 0 values as Modbus client writes!
            if getattr(self, '_first_tick', True):
                self._first_tick = False
                write_ranges = [
                    (1000, 25), (1100, 6), (1200, 7), (1300, 3),
                    (1400, 7), (1500, 7), (1600, 12), (1700, 12)
                ]
                for start, count in write_ranges:
                    block_vals = [self.simulator.read_register(start + i) for i in range(count)]
                    datastore.setValues(3, self.register_base + start, block_vals)
                return

            # 1. READ datastore for external Modbus client writes FIRST
            # By reading first, we ensure we don't overwrite client changes before processing them.
            sync_ranges = [
                (1200, 7),   # Capacity and Resolution
                (1300, 3),   # Operating V/Hz
                (1400, 7),   # Configuration Base
                (1500, 7),   # Controls
                (1600, 12),  # Target Values (W Next, etc.)
                (1700, 12)   # Exec Control Word and Ops Config
            ]
            
            for start, count in sync_ranges:
                ds_vals = datastore.getValues(3, self.register_base + start, count=count)
                if isinstance(ds_vals, list) and len(ds_vals) == count:
                    for i in range(count):
                        addr = start + i
                        datastore_val = ds_vals[i]
                        # Sync datastore values over to simulator if the Modbus Client changed them
                        if datastore_val != self.simulator.read_register(addr):
                            self.simulator.write_register(addr, datastore_val)
                            
            # Process Apply / Reject load commands specifically from 1700
            control_word = self.simulator.read_register(1700)
            
            # Handle Enable / Disable commands
            if control_word & 0x4000:  # Modbus Control Disable
                self.simulator.disable_modbus_control()
                self.simulator.reject_load()
            elif control_word & 0x8000:  # Modbus Control Enable
                if not self.simulator.control_on:
                    self.simulator.enable_modbus_control()
                    
            if control_word & 0x08:  # LoadAccept bit set by remote
                self.simulator.apply_load()
                # Clear Accept bit locally to avoid infinite apply
                new_ctrl = self.simulator.read_register(1700) & ~0x08
                self.simulator.write_register(1700, new_ctrl)
            elif control_word & 0x04:  # LoadReject bit set by remote
                self.simulator.reject_load()
                # Clear Reject bit locally
                new_ctrl = self.simulator.read_register(1700) & ~0x04
                self.simulator.write_register(1700, new_ctrl)

            # 2. WRITE back to datastore (sync simulator state to Modbus)
            write_ranges = [
                (1000, 25),
                (1100, 6),
                (1200, 7),
                (1300, 3),
                (1400, 7),
                (1500, 7),
                (1600, 12),
                (1700, 12)
            ]
            
            for start, count in write_ranges:
                block_vals = []
                for i in range(start, start + count):
                    block_vals.append(self.simulator.read_register(i))
                datastore.setValues(3, self.register_base + start, block_vals)


# Example usage function
def simulate_load_bank_operations():
    """Demonstrate the load bank simulation with typical operations"""
    
    # Create simulator instance
    lb = LoadBankSimulator()
    
    print("=== ASCO Sigma 2 Load Bank Simulation ===")
    print(f"Initial status: {lb.get_load_status()}")
    
    # Step 1: Enable Modbus Control
    print("\n--- Enabling Modbus Control ---")
    lb.enable_modbus_control()
    print(f"After enabling control: {lb.get_load_status()}")
    
    # Step 2: Select Load (50kW resistive)
    print("\n--- Selecting 50kW Load ---")
    lb.select_load(50, 0, 0)  # 50kW resistive
    print(f"Selected load values - kW reg: {lb.read_register(1701)} (={lb.read_register(1701)/10} kW), "
          f"kVArL reg: {lb.read_register(1702)} (={lb.read_register(1702)/10} kVAr), "
          f"kVArC reg: {lb.read_register(1703)} (={lb.read_register(1703)/10} kVAr)")
    
    # Step 3: Apply Load
    print("\n--- Applying Selected Load ---")
    success = lb.apply_load()
    if success:
        print("Load applied successfully!")
        print(f"Applied load status: {lb.get_load_status()}")
        print(f"Active Power reg (1018): {lb.read_register(1018)} (={lb.read_register(1018)/10} kW)")
        print(f"Apparent Power reg (1020): {lb.read_register(1020)} (={lb.read_register(1020)/10} kVA)")
        print(f"PF reg (1021): {lb.read_register(1021)} (= {lb.read_register(1021)/100:.2f})")
        print(f"L1 Active Current reg (1008): {lb.read_register(1008)} (={lb.read_register(1008)/10} A)")
    else:
        print("Failed to apply load - control not enabled")
    
    # Step 4: Simulate some time passing
    print("\n--- Waiting for Load Application ---")
    time.sleep(1)
    
    # Step 5: Reject Load
    print("\n--- Rejecting Load ---")
    success = lb.reject_load()
    if success:
        print("Load rejected successfully!")
        print(f"Applied load status after rejection: {lb.get_load_status()}")
    else:
        print("Failed to reject load - control not enabled")

if __name__ == "__main__":
    simulate_load_bank_operations()