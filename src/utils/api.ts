/// <reference types="vite/client" />
import { GeneratorStatus } from '../types/generator';
import { AdminStatus } from '../types/admin';

export interface GeneratorLogEntry {
  timestamp: string;
  level: string;
  message: string;
}

// In development (Vite dev server on :3000) the API lives on :8000.
// In production the EXE serves both frontend and API on the same port,
// so a relative URL (empty string) works for any host/IP.
const API_BASE_URL =
  import.meta.env.DEV ? 'http://localhost:8000' : '';


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

export const fetchAdminStatus = async (): Promise<AdminStatus | null> => {
  try {
    const response = await fetch(`${API_BASE_URL}/admin/status`);
    if (!response.ok) throw new Error('Failed to fetch admin status');
    return await response.json();
  } catch (error) {
    console.error('Admin Status Error:', error);
    return null;
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

export const fetchGeneratorLogs = async (
  id: string,
  limit = 100
): Promise<GeneratorLogEntry[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/generators/${id}/logs?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch logs');
    return await response.json();
  } catch (error) {
    console.error('Logs Error:', error);
    return [];
  }
};

export interface ApiResult {
  status: string;
  message: string;
}

export const setModbusEnabled = async (
  id: string,
  enabled: boolean
): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await fetch(`${API_BASE_URL}/generators/${id}/modbus`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
    let result: ApiResult = { status: 'error', message: 'Unknown' };
    try {
      result = await response.json();
    } catch {
      // non-json response
    }
    const success = response.ok && result.status === 'success';
    return { success, message: result.message || '' };
  } catch (error) {
    console.error('Modbus Enable/Disable Error:', error);
    return { success: false, message: String(error) };
  }
};

export const fetchLoadbankLogs = async (
  id: string,
  limit = 100
): Promise<GeneratorLogEntry[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/loadbanks/${id}/logs?limit=${limit}`);
    if (!response.ok) throw new Error('Failed to fetch load bank logs');
    return await response.json();
  } catch (error) {
    console.error('LB Logs Error:', error);
    return [];
  }
};

// Load Bank APIs
import { LoadBankStatus } from '../types/loadbank';

export const fetchAllLoadbanks = async (): Promise<LoadBankStatus[]> => {
  try {
    const response = await fetch(`${API_BASE_URL}/loadbanks`);
    if (!response.ok) throw new Error('Failed to fetch load banks');
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    return [];
  }
};

export const fetchLoadbank = async (id: string): Promise<LoadBankStatus | null> => {
  try {
    const response = await fetch(`${API_BASE_URL}/loadbanks/${id}`);
    if (!response.ok) throw new Error('Failed to fetch load bank');
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    return null;
  }
};

export type LBCommand = 'enable_modbus_control' | 'disable_modbus_control' | 'apply_load' | 'reject_load';

export const sendLoadbankCommand = async (id: string, command: LBCommand): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/loadbanks/${id}/command`, {
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

export const selectLoadbankLoad = async (
  id: string, 
  load: { resistive_kW: number; inductive_kVAr?: number; capacitive_kVAr?: number }
): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/loadbanks/${id}/select_load`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(load),
    });
    return response.ok;
  } catch (error) {
    console.error('Select Load Error:', error);
    return false;
  }
};

export const setLoadbankModbusEnabled = async (
  id: string,
  enabled: boolean
): Promise<{ success: boolean; message: string }> => {
  try {
    const response = await fetch(`${API_BASE_URL}/loadbanks/${id}/modbus`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled }),
    });
    let result: ApiResult = { status: 'error', message: 'Unknown' };
    try {
      result = await response.json();
    } catch {
      // non-json response
    }
    const success = response.ok && result.status === 'success';
    return { success, message: result.message || '' };
  } catch (error) {
    console.error('LB Modbus Enable/Disable Error:', error);
    return { success: false, message: String(error) };
  }
};