export interface GeneratorStatus {
  id: string;
  state: 'standstill' | 'starting' | 'running' | 'shutdown' | 'fault' | 'fastTransfer';
  voltage: number;
  frequency: number;
  activePower: number;
  reactivePower: number;
  current: number;
  breakerClosed: boolean;
  isRunning: boolean;
  isFaulted: boolean;
  // simulation parameters exposed for configuration
  simulateFailToStart?: boolean;
  failRampUp?: boolean;
  failRampDown?: boolean;
  failStartTime?: boolean;
  startDelay?: number;
  stopDelay?: number;
  // de-excitation state (SSL547)
  deexcited?: boolean;
  // service switch mode: off/manual/auto (SSL425/426/427)
  serviceMode?: 'off' | 'manual' | 'auto';
  // modbus device failure simulation flag
  modbusDisabled?: boolean;
  // FCB status
  fcb1: boolean;
  fcb2: boolean;
  // heartbeat supervision (R192 Bit 7)
  heartbeatFailed?: boolean;
  secondsSinceHeartbeat?: number;
}

export interface Alarm {
  id: string;
  type: 'critical' | 'warning' | 'info';
  message: string;
  timestamp: Date;
  acknowledged: boolean;
  generatorId?: string;
}