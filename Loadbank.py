import time
from typing import List, Dict

class LoadBankSimulator:
    def __init__(self):
        # Initialize registers according to the manual
        self.registers = {}
        
        # Initialize all register values based on typical load bank specifications
        self._initialize_registers()
        
        # Simulation state variables
        self.control_on = False
        self.load_applied = 0.0
        self.inductive_load_applied = 0.0
        self.capacitive_load_applied = 0.0
        
    def _initialize_registers(self):
        """Initialize all registers with default values based on the manual"""
        
        # Instrumentation registers (1001-1024)
        self.registers[1001] = 0      # Timestamp
        self.registers[1002] = 2300   # L1N Peak Voltage (230.0V * 10)
        self.registers[1003] = 2300   # L1N Voltage (230.0V * 10)
        self.registers[1004] = 2300   # L2N Voltage
        self.registers[1005] = 2300   # L3N Voltage
        self.registers[1006] = 4000   # L1L2 Voltage (400.0V * 10)
        self.registers[1007] = 4000   # L2L3 Voltage
        self.registers[1008] = 4000   # L3L1 Voltage
        self.registers[1009] = 50     # L1 Active Current (5.0A * 10)
        self.registers[1010] = 50     # L2 Active Current
        self.registers[1011] = 50     # L3 Active Current
        self.registers[1012] = 0      # L1 Reactive Current
        self.registers[1013] = 0      # L2 Reactive Current
        self.registers[1014] = 0      # L3 Reactive Current
        self.registers[1015] = 5000   # Frequency (50.0Hz * 100)
        self.registers[1016] = 57     # L1 Apparent Current (5.7A * 10)
        self.registers[1017] = 57     # L2 Apparent Current
        self.registers[1018] = 57     # L3 Apparent Current
        self.registers[1019] = 120    # Total Active Power (12.0kW * 10)
        self.registers[1020] = 0      # Total Reactive Power
        self.registers[1021] = 130    # Total Apparent Power (13.0kVA * 10)
        self.registers[1022] = 92     # Power Factor (0.92 * 100)
        self.registers[1023] = 2300   # Peak VL1N Voltage
        self.registers[1024] = 4000   # Peak VL1L2 Voltage
        
        # Load Bank Status registers (1101-1105)
        self.registers[1101] = 0x039F  # Status bits
        self.registers[1102] = 0x0000  # Error status bits
        self.registers[1103] = 0x00    # LED status (not running)
        
        # Load Capacity registers (1201-1206)
        self.registers[1201] = 50      # kWStep (5.0kW * 10)
        self.registers[1202] = 50      # kVArLStep
        self.registers[1203] = 50      # kVArCStep
        self.registers[1204] = 1000    # kWMax (100.0kW * 10)
        self.registers[1205] = 1000    # kVArLMax (100.0kVArL * 10)
        self.registers[1206] = 1000    # kVArCMax (100.0kVArC * 10)
        
        # Operating Voltage and Frequency registers (1301-1303)
        self.registers[1301] = 2300    # Operating Voltage (230.0V * 10)
        self.registers[1302] = 5000    # Operating Frequency (50.0Hz * 100)
        self.registers[1303] = 0       # Unused or reserved
        
        # Load Bank ID registers (1401-1407)
        self.registers[1401] = 0x01    # Station Number
        self.registers[1402] = 0x800F  # Configuration bits (resistive, inductive, capacitive load available)
        self.registers[1403] = 2300    # Nominal Voltage (230.0V * 10)
        self.registers[1404] = 5000    # Nominal Frequency (50.0Hz * 100)
        self.registers[1405] = 4800    # Max Voltage (480.0V * 10)
        self.registers[1406] = 0       # Reserved
        self.registers[1407] = 0       # Reserved
        
        # Inputs and Outputs registers (1501-1507)
        self.registers[1501] = 0x00    # Seven Segment Display
        self.registers[1502] = 0x0000  # Output bits (LoadOn, Fan relays etc.)
        self.registers[1503] = 0x0000  # More output bits
        self.registers[1504] = 0x0000  # Even more output bits
        self.registers[1505] = 0       # Reserved
        self.registers[1506] = 0       # Reserved
        self.registers[1507] = 0       # Reserved
        
        # Load Select and Apply registers (1601-1611)
        self.registers[1601] = 0       # W Now - Watts Applied (*10)
        self.registers[1603] = 0       # W Next - Watts Selected (*10)
        self.registers[1605] = 0       # VArL Now - Inductive Load Applied (*10)
        self.registers[1607] = 0       # VArL Next - Inductive Load Selected (*10)
        self.registers[1609] = 0       # VArC Now - Capacitive Load Applied (*10)
        self.registers[1611] = 0       # VArC Next - Capacitive Load Selected (*10)
        
        # Load Control registers (1701-1711)
        self.registers[1701] = 0x00    # Control bits
        self.registers[1702] = 0       # WSelected (*10)
        self.registers[1703] = 0       # VArLSelected (*10)
        self.registers[1704] = 0       # VArCSelected (*10)
        self.registers[1705] = 2300    # Operating Voltage (230.0V * 10)
        self.registers[1706] = 5000    # Operating Frequency (50.0Hz * 100)
        self.registers[1707] = 0       # Reserved
        self.registers[1708] = 0       # Reserved
        self.registers[1709] = 0       # Reserved
        self.registers[1710] = 0       # Reserved
        self.registers[1711] = 0       # Reserved
    
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
            "status_bits": self.registers[1101],
            "error_bits": self.registers[1102]
        }
    
    def enable_modbus_control(self):
        """Enable Modbus control (set ControlOn bit)"""
        current_value = self.read_register(1701)
        new_value = current_value | 0x8000  # Set MSB
        self.write_register(1701, new_value)
        self.control_on = True
        
    def disable_modbus_control(self):
        """Disable Modbus control (set ControlOff bit)"""
        current_value = self.read_register(1701)
        new_value = current_value | 0x4000  # Set second MSB
        self.write_register(1701, new_value)
        self.control_on = False
        
    def select_load(self, resistive_kW: int, inductive_kVAr: int = 0, capacitive_kVAr: int = 0):
        """Select load to be applied. Scaling: register value = kW * 10 (0.1kW resolution)"""
        scale_factor = 10
        w_selected = int(resistive_kW * scale_factor)
        varl_selected = int(inductive_kVAr * scale_factor)
        varc_selected = int(capacitive_kVAr * scale_factor)
        
        self.write_register(1702, w_selected)
        self.write_register(1703, varl_selected) 
        self.write_register(1704, varc_selected)
        
    def apply_load(self):
        """Apply the selected load"""
        if not self.control_on:
            return False
            
        # Set Accept bit in control register
        current_value = self.read_register(1701)
        new_value = current_value | 0x08   # Set LoadAccept bit (bit 3)
        self.write_register(1701, new_value)
        
        # Update applied load values (in kW)
        w_selected = self.read_register(1702)
        varl_selected = self.read_register(1703)
        varc_selected = self.read_register(1704)
        
        self.load_applied = float(w_selected) / 10
        self.inductive_load_applied = float(varl_selected) / 10
        self.capacitive_load_applied = float(varc_selected) / 10
        
        # Update applied registers (Now = selected, Next remains selected)
        self.write_register(1601, w_selected)  # W Now
        self.write_register(1605, varl_selected)  # VArL Now
        self.write_register(1609, varc_selected)  # VArC Now
        
        # Update instrumentation (scaled consistently)
        self.registers[1019] = w_selected  # Total Active Power *10
        reactive_net = varl_selected - varc_selected
        reactive_abs = abs(reactive_net)
        self.registers[1020] = reactive_abs  # Total Reactive Power *10 (simplified)
        apparent = int((w_selected ** 2 + reactive_abs ** 2) ** 0.5)
        self.registers[1021] = apparent  # Total Apparent Power *10
        pf = int(w_selected * 100 / apparent) if apparent > 0 else 1000
        self.registers[1022] = pf  # Power Factor *100 (max 1000?)
        
        # Update currents (approximate 3-phase, L-L voltage)
        v_ll = float(self.registers[1006]) / 10  # L1L2 Voltage in V
        apparent_kva = float(apparent) / 10
        pf_val = float(pf) / 100
        i_app = int(apparent_kva * 1000 / (1.732 * v_ll) * 10)  # Apparent current *10 per phase
        i_act = int(i_app * pf_val)  # Active current *10 per phase
        
        self.registers[1009] = self.registers[1010] = self.registers[1011] = i_act
        self.registers[1016] = self.registers[1017] = self.registers[1018] = i_app
        self.registers[1012] = self.registers[1013] = self.registers[1014] = 0  # Reactive currents (simplified)
        
        return True
    
    def reject_load(self):
        """Reject all applied load"""
        if not self.control_on:
            return False
            
        # Set Reject bit in control register
        current_value = self.read_register(1701)
        new_value = current_value | 0x04   # Set LoadReject bit (bit 2)
        self.write_register(1701, new_value)
        
        # Clear applied load values
        self.load_applied = 0.0
        self.inductive_load_applied = 0.0
        self.capacitive_load_applied = 0.0
        
        # Update applied registers to zero
        for addr in [1601, 1603, 1605, 1607, 1609, 1611]:
            self.write_register(addr, 0)
        
        # Reset instrumentation to no-load state
        self.registers[1019] = 0
        self.registers[1020] = 0
        self.registers[1021] = 0
        self.registers[1022] = 100  # PF 1.00 *100
        self.registers[1009] = self.registers[1010] = self.registers[1011] = 0
        self.registers[1012] = self.registers[1013] = self.registers[1014] = 0
        self.registers[1016] = self.registers[1017] = self.registers[1018] = 0
        
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
    print(f"Selected load values - kW reg: {lb.read_register(1702)} (={lb.read_register(1702)/10} kW), "
          f"kVArL reg: {lb.read_register(1703)} (={lb.read_register(1703)/10} kVAr), "
          f"kVArC reg: {lb.read_register(1704)} (={lb.read_register(1704)/10} kVAr)")
    
    # Step 3: Apply Load
    print("\n--- Applying Selected Load ---")
    success = lb.apply_load()
    if success:
        print("Load applied successfully!")
        print(f"Applied load status: {lb.get_load_status()}")
        print(f"Active Power reg (1019): {lb.read_register(1019)} (={lb.read_register(1019)/10} kW)")
        print(f"Apparent Power reg (1021): {lb.read_register(1021)} (={lb.read_register(1021)/10} kVA)")
        print(f"PF reg (1022): {lb.read_register(1022)} (= {lb.read_register(1022)/100:.2f})")
        print(f"L1 Active Current reg (1009): {lb.read_register(1009)} (={lb.read_register(1009)/10} A)")
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