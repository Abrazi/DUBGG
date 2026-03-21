import React from 'react';
import { GeneratorStatus } from '../types/generator';
import { Card, CardContent } from './ui/card';
import { Power, Settings, ShieldAlert, Cpu } from 'lucide-react';

interface GeneratorsOverviewProps {
  generators: GeneratorStatus[];
}

export function GeneratorsOverview({ generators }: GeneratorsOverviewProps) {
  const getGpsGroup = (gpsId: string) => {
    return generators.filter(gen => {
      if (gpsId === 'GPS1') {
        if (['G1', 'G2', 'G3', 'G4', 'G5'].includes(gen.id)) return gen.fcb1;
        if (['G6', 'G7', 'G8', 'G9', 'G10'].includes(gen.id)) return gen.fcb2;
        if (gen.id === 'G21') return gen.fcb1;
      }
      if (gpsId === 'GPS2') {
        if (['G1', 'G2', 'G3', 'G4', 'G5'].includes(gen.id)) return gen.fcb2;
        if (['G6', 'G7', 'G8', 'G9', 'G10'].includes(gen.id)) return gen.fcb1;
        if (gen.id === 'G22') return gen.fcb1;
      }
      if (gpsId === 'GPS3') {
        if (['G11', 'G12', 'G13', 'G14', 'G15'].includes(gen.id)) return gen.fcb1;
        if (['G16', 'G17', 'G18', 'G19', 'G20'].includes(gen.id)) return gen.fcb2;
        if (gen.id === 'G21') return gen.fcb2;
      }
      if (gpsId === 'GPS4') {
        if (['G11', 'G12', 'G13', 'G14', 'G15'].includes(gen.id)) return gen.fcb2;
        if (['G16', 'G17', 'G18', 'G19', 'G20'].includes(gen.id)) return gen.fcb1;
        if (gen.id === 'G22') return gen.fcb2;
      }
      return false;
    });
  };

  const gpsIds = ['GPS1', 'GPS2', 'GPS3', 'GPS4'];

  return (
    <div className="mb-8">
      <h3 className="text-xl text-white font-semibold mb-6 flex items-center gap-2 border-b border-slate-800 pb-2">
        <Cpu className="w-5 h-5 text-emerald-400" />
        Generators by GPS Assignment
      </h3>

      <div className="space-y-8">
        {gpsIds.map(gpsId => {
          const groupGenerators = getGpsGroup(gpsId);
          if (groupGenerators.length === 0) return null;

          return (
            <div key={gpsId}>
              <h4 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center gap-2">
                <div className="w-1 h-4 bg-blue-500 rounded-full" />
                {gpsId} Assigned Units
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
                {groupGenerators.map(gen => (
                  <GeneratorCard key={`${gpsId}-${gen.id}`} gen={gen} />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GeneratorCard({ gen }: { gen: GeneratorStatus }) {
  return (
    <Card className={`bg-slate-900 border-slate-800 hover:border-slate-700 transition-all cursor-pointer group ${gen.isFaulted ? 'ring-1 ring-red-500/50' : ''}`}>
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
  );
}
