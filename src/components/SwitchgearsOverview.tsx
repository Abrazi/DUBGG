import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Activity, ShieldCheck, ShieldAlert } from 'lucide-react';

export interface SwitchgearStatus {
  id: string;
  demand: number;
  onlineCount: number;
  modbusDisabled: boolean;
}

interface SwitchgearsOverviewProps {
  switchgears: SwitchgearStatus[];
}

export function SwitchgearsOverview({ switchgears }: SwitchgearsOverviewProps) {
  return (
    <div className="mb-8">
      <h3 className="text-xl text-white font-semibold mb-4 flex items-center gap-2">
        <Activity className="w-5 h-5 text-blue-400" />
        Switchgears (GPS)
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {switchgears.map(swg => (
          <Card key={swg.id} className={`bg-slate-900 border-slate-800 ${swg.modbusDisabled ? 'opacity-60' : ''}`}>
            <CardHeader className="p-4 border-b border-slate-800/50">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg font-bold text-white">{swg.id}</CardTitle>
                {swg.modbusDisabled ? (
                   <ShieldAlert className="w-5 h-5 text-red-500" />
                ) : (
                   <ShieldCheck className="w-5 h-5 text-emerald-500" />
                )}
              </div>
            </CardHeader>
            <CardContent className="p-4">
              <div className="space-y-4">
                <div>
                  <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Current Demand</div>
                  <div className="text-2xl font-bold text-blue-400">{swg.demand} <span className="text-sm font-normal text-slate-500">kW</span></div>
                </div>

                <div className="flex justify-between items-end">
                  <div>
                    <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Online Generators</div>
                    <div className="text-xl font-semibold text-emerald-400">{swg.onlineCount}</div>
                  </div>

                  <div className="text-right">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${swg.modbusDisabled
                      ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                      : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                    }`}>
                      {swg.modbusDisabled ? 'Offline' : 'Online'}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
