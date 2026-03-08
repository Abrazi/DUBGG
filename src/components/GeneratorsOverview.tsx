import React from 'react';
import { GeneratorStatus } from '../types/generator';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';

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
    case 'standstill':
      return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    default:
      return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
  }
}

export function GeneratorsOverview({ generators }: GeneratorsOverviewProps) {
  return (
    <div className="mb-8">
      <h3 className="text-xl text-white font-semibold mb-4">All Generators</h3>
      <div className="flex flex-col gap-2">
        {generators.map(gen => (
          <Card key={gen.id} className="bg-slate-800 border-slate-700">
            <CardContent className="p-3">
              <div className="flex items-center justify-between">
                <span className="text-white font-medium">{gen.id}</span>
                <div className="flex gap-2">
                  <span className={`px-2 py-1 text-xs rounded font-bold ${gen.heartbeatFailed ? 'bg-red-500/20 text-red-500 border border-red-500/50 animate-pulse' : 'bg-green-500/20 text-green-400 border border-green-500/50'}`}>
                    {gen.heartbeatFailed ? 'HB LOST' : `HB OK (${gen.secondsSinceHeartbeat ?? 0}s)`}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded ${getStateBadgeColor(gen.state)}`}>{gen.state}</span>
                </div>
              </div>
              <div className="mt-2 flex items-center justify-between gap-4">
                <div>
                  <div className="text-sm text-slate-300">Breaker</div>
                  <div className={`text-xs font-semibold ${gen.breakerClosed ? 'text-emerald-400' : 'text-red-400'}`}>
                    {gen.breakerClosed ? 'CLOSED' : 'OPEN'}
                  </div>
                </div>

                <div>
                  <div className="text-sm text-slate-300">De-excited</div>
                  <div className={`text-xs font-semibold ${gen.deexcited ? 'text-amber-400' : 'text-slate-400'}`}>
                    {gen.deexcited ? 'YES' : 'NO'}
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-sm text-slate-300">Service Mode</div>
                  <div className="text-xs font-semibold text-slate-300">{gen.serviceMode || 'auto'}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
