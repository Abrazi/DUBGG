import { SystemStatus } from '../types/hmi';
import { Power, Activity, Clock, Cpu, Settings, LayoutDashboard } from 'lucide-react';
import { Button } from '../components/ui/button';
import logo from '../assets/Enersol.png';

interface HeaderProps {
  status: SystemStatus;
  onToggleSystem: () => void;
  activeView: 'dashboard' | 'admin';
  onViewChange: (view: 'dashboard' | 'admin') => void;
}

export function Header({ status, onToggleSystem, activeView, onViewChange }: HeaderProps) {
  const formatUptime = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hrs}h ${mins}m`;
  };

  return (
    <header className="bg-slate-900 border-b-4 border-slate-700 p-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <img src={logo} alt="Enersol logo" style={{ width: 212, height: 47, objectFit: 'contain' }} />
          <div className="bg-slate-800 p-3 rounded-lg">
            <Activity className={`w-8 h-8 ${status.isRunning ? 'text-emerald-400' : 'text-red-400'}`} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Enersol Generator Controller</h1>
            <p className="text-slate-400 text-sm">Industrial Process Control System</p>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-slate-800/50 p-1 rounded-lg border border-slate-700">
          <button
            onClick={() => onViewChange('dashboard')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-all ${activeView === 'dashboard'
                ? 'bg-slate-700 text-white shadow-lg'
                : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span className="text-sm font-medium">Dashboard</span>
          </button>
          <button
            onClick={() => onViewChange('admin')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-all ${activeView === 'admin'
                ? 'bg-slate-700 text-white shadow-lg'
                : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            <Settings className="w-4 h-4" />
            <span className="text-sm font-medium">Administration</span>
          </button>
        </div>

        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 bg-slate-800 px-4 py-2 rounded-lg">
            <Clock className="w-5 h-5 text-slate-400" />
            <span className="text-slate-300 font-mono">{formatUptime(status.uptime)}</span>
          </div>

          <div className="flex items-center gap-2 bg-slate-800 px-4 py-2 rounded-lg">
            <Cpu className="w-5 h-5 text-amber-400" />
            <span className="text-slate-300 font-mono">{status.cpuUsage}%</span>
          </div>

          <Button
            onClick={onToggleSystem}
            className={`${status.isRunning ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'} text-white font-semibold px-6 py-2 rounded-lg flex items-center gap-2`}
          >
            <Power className="w-5 h-5" />
            {status.isRunning ? 'STOP' : 'START'}
          </Button>
        </div>
      </div>
    </header>
  );
}