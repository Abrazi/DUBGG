import { useState, useEffect } from 'react';
import { fetchAdminStatus } from '../utils/api';
import { AdminStatus } from '../types/admin';
import { Activity, Server, Cpu, HardDrive, CheckCircle2, XCircle, Globe } from 'lucide-react';

export function AdministrationPage() {
    const [status, setStatus] = useState<AdminStatus | null>(null);
    const [loading, setLoading] = useState(true);

    const refreshStatus = async () => {
        const data = await fetchAdminStatus();
        if (data) setStatus(data);
        setLoading(false);
    };

    useEffect(() => {
        refreshStatus();
        const interval = setInterval(refreshStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    if (loading && !status) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-slate-400 animate-pulse">Loading administration data...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <Activity className="w-6 h-6 text-emerald-400" />
                    <h2 className="text-2xl font-bold text-white">System Administration</h2>
                </div>
                <div className="text-slate-400 text-sm">
                    Last updated: {new Date().toLocaleTimeString()}
                </div>
            </div>

            {/* System Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                    <div className="flex items-center gap-3 mb-2 text-slate-400">
                        <Cpu className="w-4 h-4" />
                        <span className="text-sm font-medium">CPU Usage</span>
                    </div>
                    <div className="text-2xl font-bold text-white font-mono">
                        {status?.system.cpu_percent}%
                    </div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                    <div className="flex items-center gap-3 mb-2 text-slate-400">
                        <HardDrive className="w-4 h-4" />
                        <span className="text-sm font-medium">Memory Usage</span>
                    </div>
                    <div className="text-2xl font-bold text-white font-mono">
                        {status?.system.memory_percent}%
                    </div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                    <div className="flex items-center gap-3 mb-2 text-slate-400">
                        <Server className="w-4 h-4" />
                        <span className="text-sm font-medium">Process Uptime</span>
                    </div>
                    <div className="text-2xl font-bold text-white font-mono text-lg">
                        {Math.floor((status?.system.process_uptime || 0) / 3600)}h {Math.floor(((status?.system.process_uptime || 0) % 3600) / 60)}m
                    </div>
                </div>
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                    <div className="flex items-center gap-3 mb-2 text-slate-400">
                        <Globe className="w-4 h-4" />
                        <span className="text-sm font-medium">Platform</span>
                    </div>
                    <div className="text-2xl font-bold text-white truncate text-lg">
                        {status?.system.platform}
                    </div>
                </div>
            </div>

            {/* Servers Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800 flex justify-between items-center">
                    <h3 className="font-semibold text-white">Backend Modbus Servers Status</h3>
                    <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 text-xs rounded border border-emerald-500/20">
                        {status?.servers.length} Active Servers
                    </span>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead>
                            <tr className="bg-slate-950/50 text-slate-400 text-xs uppercase tracking-wider">
                                <th className="px-6 py-3 font-medium">Name</th>
                                <th className="px-6 py-3 font-medium">Type</th>
                                <th className="px-6 py-3 font-medium">IP Address</th>
                                <th className="px-6 py-3 font-medium">Port</th>
                                <th className="px-6 py-3 font-medium text-center">Server Process</th>
                                <th className="px-6 py-3 font-medium text-center">Port Accessible</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {status?.servers.map((server) => (
                                <tr key={server.name} className="hover:bg-slate-800/50 transition-colors">
                                    <td className="px-6 py-4 text-white font-semibold">{server.name}</td>
                                    <td className="px-6 py-4">
                                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${server.type === 'generator' ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'
                                            }`}>
                                            {server.type}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-slate-300 font-mono">{server.ip}</td>
                                    <td className="px-6 py-4 text-slate-300 font-mono">{server.port}</td>
                                    <td className="px-6 py-4">
                                        <div className="flex justify-center">
                                            {server.is_running ? (
                                                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                                            ) : (
                                                <XCircle className="w-5 h-5 text-red-500" />
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex justify-center">
                                            {server.is_port_open ? (
                                                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                                            ) : (
                                                <XCircle className="w-5 h-5 text-red-500" />
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl text-slate-400 text-sm">
                <p><strong>Note:</strong> Port Accessible check (502) verifies if the Modbus server is truly listening on the specified IP address. If "Server Process" is green but "Port Accessible" is red, there might be an IP binding issue or a firewall blocking the connection.</p>
            </div>
        </div>
    );
}
