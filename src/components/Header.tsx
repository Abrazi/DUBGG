import { Settings, LayoutDashboard, Factory } from 'lucide-react';
import { Button } from '../components/ui/button';
import logo from '../assets/Enersol.png';

interface HeaderProps {
  activeView: 'overview' | 'dashboard' | 'admin';
  onViewChange: (view: 'overview' | 'dashboard' | 'admin') => void;
}

export function Header({ activeView, onViewChange }: HeaderProps) {

  return (
    <header className="bg-slate-900 border-b-4 border-slate-700 p-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-4">
          <img src={logo} alt="Enersol logo" style={{ width: 212, height: 47, objectFit: 'contain' }} />
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Enersol Generator Controller</h1>
            <p className="text-slate-400 text-sm">Industrial Process Control System</p>
          </div>
        </div>

        <div className="flex items-center gap-4 bg-slate-800/50 p-1 rounded-lg border border-slate-700">
          <button
            onClick={() => onViewChange('overview')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-all ${activeView === 'overview'
              ? 'bg-slate-700 text-white shadow-lg'
              : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            <Factory className="w-4 h-4" />
            <span className="text-sm font-medium">Plant Overview</span>
          </button>
          <button
            onClick={() => onViewChange('dashboard')}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-md transition-all ${activeView === 'dashboard'
              ? 'bg-slate-700 text-white shadow-lg'
              : 'text-slate-400 hover:text-slate-200'
              }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span className="text-sm font-medium">Unit Control</span>
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
      </div>
    </header>
  );
}