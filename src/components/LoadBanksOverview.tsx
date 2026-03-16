import React from 'react';
import { LoadBankStatus } from '../types/loadbank';
import { Card, CardContent } from './ui/card';

interface LoadBanksOverviewProps {
  loadbanks: LoadBankStatus[];
}

export function LoadBanksOverview({ loadbanks }: LoadBanksOverviewProps) {
  return (
    <div className="mb-8 mt-8">
      <h3 className="text-xl text-white font-semibold mb-4">Load Banks</h3>
      <div className="flex flex-col gap-2">
        {loadbanks.map(lb => (
          <Card key={lb.id} className="bg-slate-800 border-slate-700">
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <span className="text-white font-medium">{lb.id}</span>
                <div className="flex gap-2">
                  <span className={`px-2 py-1 text-xs rounded font-bold ${lb.control_on ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' : 'bg-slate-500/20 text-slate-400 border border-slate-500/50'}`}>
                    {lb.control_on ? 'CTRL: ON' : 'CTRL: OFF'}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded font-bold ${!lb.modbusDisabled ? 'bg-green-500/20 text-green-400 border border-green-500/50' : 'bg-red-500/20 text-red-500 border border-red-500/50 animate-pulse'}`}>
                    {!lb.modbusDisabled ? 'ONLINE' : 'OFFLINE'}
                  </span>
                </div>
              </div>
              <div className="mt-2 flex items-center justify-between gap-4">
                <div>
                  <div className="text-sm text-slate-300">Applied</div>
                  <div className={`text-xs font-semibold ${lb.load_applied > 0 ? 'text-blue-400' : 'text-slate-400'}`}>
                    {lb.load_applied} kW
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-sm text-slate-300">Total Pwr</div>
                  <div className="text-xs font-semibold text-slate-300">
                    {lb.activePower} kW
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
