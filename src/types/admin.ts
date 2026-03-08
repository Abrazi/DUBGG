export interface ServerStatus {
    name: string;
    ip: string;
    port: number;
    is_running: boolean;
    is_port_open: boolean;
    type: 'generator' | 'switchgear';
}

export interface SystemInfo {
    cpu_percent: number;
    memory_percent: number;
    platform: string;
    uptime: number;
    process_uptime: number;
}

export interface AdminStatus {
    servers: ServerStatus[];
    system: SystemInfo;
}
