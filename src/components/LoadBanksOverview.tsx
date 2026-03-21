import React from 'react';
import { LoadBankStatus } from '../types/loadbank';
import { Card, CardContent } from './ui/card';
import { Gauge } from 'lucide-react';

interface LoadBanksOverviewProps {
  loadbanks: LoadBankStatus[];
}

export function LoadBanksOverview({ loadbanks }: LoadBanksOverviewProps) {
  return (
    <div className="mb-8 mt-8">
      <h3 className="text-xl text-white font-semibold mb-4 flex items-center gap-2">
        <Gauge className="w-5 h-5 text-blue-400" />
        Load Banks (LB1-LB4)
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {loadbanks.map(lb => (
          <Card key={lb.id} className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-4">
                <span className="text-white font-bold">{lb.id}</span>
                <div className="flex gap-2">
                  <span className={`px-2 py-0.5 text-[10px] rounded font-bold uppercase ${lb.control_on ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'}`}>
                    {lb.control_on ? 'Modbus On' : 'Local Only'}
                  </span>
                  <span className={`px-2 py-0.5 text-[10px] rounded font-bold uppercase ${!lb.modbusDisabled ? 'bg-green-500/10 text-green-400 border border-green-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20 animate-pulse'}`}>
                    {!lb.modbusDisabled ? 'Online' : 'Offline'}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Active Power</div>
                  <div className="text-xl font-bold text-blue-400">{lb.activePower.toFixed(1)} <span className="text-xs font-normal">kW</span></div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1">Reactive Power</div>
                  <div className="text-xl font-bold text-purple-400">{lb.reactivePower.toFixed(1)} <span className="text-xs font-normal">kVAr</span></div>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-slate-800/50 flex justify-between items-center">
                 <div className="text-[10px] text-slate-500">PF: <span className="text-slate-300 font-bold">{lb.powerFactor.toFixed(2)}</span></div>
                 <div className="text-[10px] text-slate-500">Freq: <span className="text-slate-300 font-bold">{lb.frequency.toFixed(1)} Hz</span></div>
                 <div className="text-[10px] text-slate-500">Volt: <span className="text-slate-300 font-bold">{lb.l1l2Voltage.toFixed(0)} V</span></div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
