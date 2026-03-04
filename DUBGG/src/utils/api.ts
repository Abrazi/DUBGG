import { GeneratorStatus } from '../types/generator';

const API_BASE_URL = 'http://localhost:8000';

export const fetchAllGenerators = async (): Promise<GeneratorStatus[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/generators`);
    if (!response.ok) throw new Error('Failed to fetch generators');
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    return [];
  }
};

export const fetchGenerator = async (id: string): Promise<GeneratorStatus | null> => {
  try {
    const response = await fetch(`${API_BASE_URL}/generators/${id}`);
    if (!response.ok) throw new Error('Failed to fetch generator');
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    return null;
  }
};

export type GenCommand =
  | 'start'
  | 'stop'
  | 'reset_fault'
  | 'open_breaker'
  | 'close_breaker'
  | 'inject_fault'
  | 'deexcite_on'
  | 'deexcite_off';


interface ConfigPayload {
  simulate_fail_to_start?: boolean;
  fail_ramp_up?: boolean;
  fail_ramp_down?: boolean;
  fail_start_time?: boolean;
  start_delay?: number;
  stop_delay?: number;
  // optional service switch mode value
  service_mode?: 'off' | 'manual' | 'auto';
}

export const sendCommand = async (id: string, command: GenCommand): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/generators/${id}/command`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    });
    return response.ok;
  } catch (error) {
    console.error('Command Error:', error);
    return false;
  }
};

export const updateGeneratorConfig = async (id: string, config: ConfigPayload): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/generators/${id}/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    return response.ok;
  } catch (error) {
    console.error('Config Error:', error);
    return false;
  }
};