import React from 'react';
import { GeneratorStatus } from '../types/generator';
import { Card, CardContent } from './ui/card';
import { Power, Settings, ShieldAlert, Cpu } from 'lucide-react';

interface GeneratorsOverviewProps {
  generators: GeneratorStatus[];
}

// reused from MonitoringDashboard for consistency
function getStateBadgeColor(state: string) {
  switch (state) {
    case 'running':
      return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
    case 'starting':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
    case 'fault':
      return 'bg-red-500/20 text-red-400 border-red-500/50';
    case 'shutdown':
      return 'bg-amber-500/20 text-amber-400 border-amber-500/50';
    case 'standstill':
      return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    default:
      return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
  }
}

export function GeneratorsOverview({ generators }: GeneratorsOverviewProps) {
  return (
    <div className="mb-8">
      <h3 className="text-xl text-white font-semibold mb-4 flex items-center gap-2">
        <Cpu className="w-5 h-5 text-emerald-400" />
        All Generators (G1-G22)
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
        {generators.map(gen => (
          <Card key={gen.id} className={`bg-slate-900 border-slate-800 hover:border-slate-700 transition-all cursor-pointer group ${gen.isFaulted ? 'ring-1 ring-red-500/50' : ''}`}>
            <CardContent className="p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-white font-bold text-sm">{gen.id}</span>
                <div className={`w-2 h-2 rounded-full ${
                  gen.state === 'running' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' :
                  gen.state === 'starting' ? 'bg-blue-500 animate-pulse' :
                  gen.state === 'fault' ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' :
                  'bg-slate-600'
                }`} title={gen.state} />
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between items-center">
                   <Power className={`w-3 h-3 ${gen.breakerClosed ? 'text-emerald-400' : 'text-slate-500'}`} />
                   <span className={`text-[10px] font-bold ${gen.breakerClosed ? 'text-emerald-400' : 'text-slate-500'}`}>
                     {gen.breakerClosed ? 'CB CLOSED' : 'CB OPEN'}
                   </span>
                </div>

                <div className="flex justify-between items-center">
                   <ShieldAlert className={`w-3 h-3 ${gen.isFaulted ? 'text-red-400' : 'text-slate-500'}`} />
                   <span className={`text-[10px] font-bold ${gen.isFaulted ? 'text-red-400' : 'text-slate-500'}`}>
                     {gen.isFaulted ? 'FAULT' : 'OK'}
                   </span>
                </div>

                <div className="flex justify-between items-center">
                   <Settings className={`w-3 h-3 ${gen.serviceMode === 'auto' ? 'text-blue-400' : 'text-amber-400'}`} />
                   <span className={`text-[10px] font-bold uppercase ${gen.serviceMode === 'auto' ? 'text-blue-400' : 'text-amber-400'}`}>
                     {gen.serviceMode || 'auto'}
                   </span>
                </div>
              </div>

              <div className="mt-2 pt-2 border-t border-slate-800/50">
                 <div className="text-[10px] text-slate-500 flex justify-between">
                    <span>{gen.activePower.toFixed(0)} kW</span>
                    <span>{gen.voltage.toFixed(0)} V</span>
                 </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
