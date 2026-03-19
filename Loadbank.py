import time
from typing import List, Dict

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
        self.registers[address] = value & 0xFFFF
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
        new_value = current_value | 0x8000  # Set MSB
        self.write_register(1700, new_value)
        self.control_on = True
        
    def disable_modbus_control(self):
        """Disable Modbus control (set ControlOff bit)"""
        current_value = self.read_register(1700)
        new_value = current_value | 0x4000  # Set second MSB
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
            
        # Set Accept bit in control register
        current_value = self.read_register(1700)
        new_value = current_value | 0x08   # Set LoadAccept bit (bit 3)
        self.write_register(1700, new_value)
        
        # Update applied load values (in kW)
        w_selected = self.read_register(1701)
        varl_selected = self.read_register(1702)
        varc_selected = self.read_register(1703)
        
        self.load_applied = float(w_selected) / 10
        self.inductive_load_applied = float(varl_selected) / 10
        self.capacitive_load_applied = float(varc_selected) / 10
        
        # Update applied registers (Now = selected, Next remains selected)
        self.write_register(1600, w_selected)  # W Now
        self.write_register(1604, varl_selected)  # VArL Now
        self.write_register(1608, varc_selected)  # VArC Now
        
        # Update instrumentation (scaled consistently)
        self.registers[1018] = w_selected  # Total Active Power *10
        reactive_net = varl_selected - varc_selected
        reactive_abs = abs(reactive_net)
        self.registers[1019] = reactive_abs  # Total Reactive Power *10 (simplified)
        apparent = int((w_selected ** 2 + reactive_abs ** 2) ** 0.5)
        self.registers[1020] = apparent  # Total Apparent Power *10
        pf = int(w_selected * 100 / apparent) if apparent > 0 else 1000
        self.registers[1021] = pf  # Power Factor *100 (max 1000?)
        
        # Update currents (approximate 3-phase, L-L voltage)
        v_ll = float(self.registers[1005]) / 10  # L1L2 Voltage in V
        apparent_kva = float(apparent) / 10
        pf_val = float(pf) / 100
        i_app = int(apparent_kva * 1000 / (1.732 * v_ll) * 10)  # Apparent current *10 per phase
        i_act = int(i_app * pf_val)  # Active current *10 per phase
        
        self.registers[1008] = self.registers[1009] = self.registers[1010] = i_act
        self.registers[1015] = self.registers[1016] = self.registers[1017] = i_app
        self.registers[1011] = self.registers[1012] = self.registers[1013] = 0  # Reactive currents (simplified)
        
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