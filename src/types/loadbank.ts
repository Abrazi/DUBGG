export interface LoadBankStatus {
  id: string;
  load_applied: number;
  inductive_load_applied: number;
  capacitive_load_applied: number;
  control_on: boolean;
  status_bits: number;
  error_bits: number;
  activePower: number;
  reactivePower: number;
  apparentPower: number;
  powerFactor: number;
  l1l2Voltage: number;
  frequency: number;
  modbusDisabled: boolean;
}
