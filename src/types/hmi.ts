export interface SystemStatus {
  isRunning: boolean;
  uptime: number;
  cpuUsage: number;
  memoryUsage: number;
  temperature: number;
  pressure: number;
  flowRate: number;
}

export interface Alarm {
  id: string;
  type: 'critical' | 'warning' | 'info';
  message: string;
  timestamp: Date;
  acknowledged: boolean;
}

export interface ControlParameter {
  id: string;
  name: string;
  value: number;
  min: number;
  max: number;
  unit: string;
}