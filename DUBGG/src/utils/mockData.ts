import { SystemStatus, Alarm, ControlParameter } from '../types/hmi';

export const generateMockStatus = (): SystemStatus => ({
  isRunning: true,
  uptime: Math.floor(Math.random() * 100000) + 50000,
  cpuUsage: Math.floor(Math.random() * 60) + 20,
  memoryUsage: Math.floor(Math.random() * 40) + 30,
  temperature: Math.floor(Math.random() * 30) + 40,
  pressure: Math.floor(Math.random() * 50) + 100,
  flowRate: Math.floor(Math.random() * 20) + 80,
});

export const initialAlarms: Alarm[] = [
  {
    id: '1',
    type: 'warning',
    message: 'Temperature approaching upper limit',
    timestamp: new Date(Date.now() - 300000),
    acknowledged: false,
  },
  {
    id: '2',
    type: 'info',
    message: 'Scheduled maintenance in 2 hours',
    timestamp: new Date(Date.now() - 3600000),
    acknowledged: true,
  },
];

export const controlParameters: ControlParameter[] = [
  { id: 'temp', name: 'Target Temperature', value: 65, min: 20, max: 100, unit: '°C' },
  { id: 'pressure', name: 'Pressure Setpoint', value: 120, min: 50, max: 200, unit: 'PSI' },
  { id: 'flow', name: 'Flow Rate', value: 90, min: 0, max: 150, unit: 'L/min' },
  { id: 'speed', name: 'Motor Speed', value: 1800, min: 0, max: 3600, unit: 'RPM' },
];

export const generateHistoricalData = (points: number = 20) => {
  return Array.from({ length: points }, (_, i) => ({
    time: new Date(Date.now() - (points - i) * 5000).toLocaleTimeString(),
    temperature: Math.floor(Math.random() * 20) + 55,
    pressure: Math.floor(Math.random() * 30) + 105,
    flow: Math.floor(Math.random() * 15) + 82,
  }));
};