import { GeneratorStatus } from '../types/generator';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Zap, Activity, Gauge, Cpu } from 'lucide-react';

interface MonitoringDashboardProps {
  generator: GeneratorStatus;
  historicalData: Array<{ time: string; voltage: number; power: number; frequency: number }>;
}

export function MonitoringDashboard({ generator, historicalData }: MonitoringDashboardProps) {
  const getStatusColor = (value: number, target: number, tolerance: number) => {
    const diff = Math.abs(value - target);
    if (diff > tolerance * 2) return 'text-red-400';
    if (diff > tolerance) return 'text-amber-400';
    return 'text-emerald-400';
  };

  const getStateBadgeColor = (state: string) => {
    switch (state) {
      case 'running': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
      case 'starting': return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      case 'fault': return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'standstill': return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
    }
  };

  return (
    <div className="space-y-6">
      {/* Status Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-white">{generator.id} Status</h2>
          <p className="text-slate-400 mt-1">Real-time monitoring</p>
        </div>
        <div className={`px-4 py-2 rounded-full border text-sm font-semibold uppercase tracking-wider ${getStateBadgeColor(generator.state)}`}>
          {generator.state}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Voltage Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-slate-300 text-sm font-medium flex items-center gap-2">
              <Zap className="w-4 h-4" />
              Voltage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-4xl font-bold ${getStatusColor(generator.voltage, 10500, 500)}`}>
              {generator.voltage.toFixed(0)} V
            </div>
            <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full transition-all duration-500 bg-blue-500"
                style={{ width: `${Math.min((generator.voltage / 12000) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-2">Target: 10,500 V</p>
          </CardContent>
        </Card>

        {/* Frequency Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-slate-300 text-sm font-medium flex items-center gap-2">
              <Activity className="w-4 h-4" />
              Frequency
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-4xl font-bold ${getStatusColor(generator.frequency, 50, 0.5)}`}>
              {generator.frequency.toFixed(2)} Hz
            </div>
            <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full transition-all duration-500 bg-purple-500"
                style={{ width: `${Math.min((generator.frequency / 60) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-2">Target: 50.00 Hz</p>
          </CardContent>
        </Card>

        {/* Active Power Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-slate-300 text-sm font-medium flex items-center gap-2">
              <Gauge className="w-4 h-4" />
              Active Power
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-emerald-400">
              {generator.activePower.toFixed(0)} kW
            </div>
            <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full transition-all duration-500 bg-emerald-500"
                style={{ width: `${Math.min((generator.activePower / 3500) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-2">Nominal: 3,500 kW</p>
          </CardContent>
        </Card>

        {/* Current Card */}
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader className="pb-3">
            <CardTitle className="text-slate-300 text-sm font-medium flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              Current
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-bold text-amber-400">
              {generator.current.toFixed(1)} A
            </div>
            <div className="mt-2 h-2 bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full transition-all duration-500 bg-amber-500"
                style={{ width: `${Math.min((generator.current / 300) * 100, 100)}%` }}
              />
            </div>
            <p className="text-xs text-slate-500 mt-2">Breaker: {generator.breakerClosed ? 'CLOSED' : 'OPEN'}</p>
          </CardContent>
        </Card>
      </div>

      {/* Historical Chart */}
      <Card className="bg-slate-800 border-slate-700">
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="text-slate-300">Performance Trends</CardTitle>
            <div className="text-xs text-slate-500">Live (Last 20 samples)</div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Ensure the container has a clear height and min-width to avoid Recharts 0-size bugs */}
          <div className="h-64 w-full min-h-[250px]">
            <ResponsiveContainer width="100%" height="100%" debounce={50}>
              <LineChart data={historicalData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis
                  dataKey="time"
                  stroke="#94a3b8"
                  fontSize={10}
                  tick={{ fill: '#94a3b8' }}
                  axisLine={{ stroke: '#334155' }}
                />
                <YAxis
                  yAxisId="left"
                  stroke="#3b82f6"
                  fontSize={10}
                  orientation="left"
                  tick={{ fill: '#3b82f6' }}
                  axisLine={{ stroke: '#334155' }}
                  label={{ value: 'Voltage (V)', angle: -90, position: 'insideLeft', fill: '#3b82f6', fontSize: 10 }}
                />
                <YAxis
                  yAxisId="right"
                  stroke="#10b981"
                  fontSize={10}
                  orientation="right"
                  tick={{ fill: '#10b981' }}
                  axisLine={{ stroke: '#334155' }}
                  label={{ value: 'Power (kW)', angle: 90, position: 'insideRight', fill: '#10b981', fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '4px' }}
                  itemStyle={{ fontSize: '12px' }}
                />
                <Legend iconType="circle" wrapperStyle={{ paddingTop: '10px', fontSize: '12px' }} />
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="voltage"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  name="Voltage"
                  dot={false}
                  isAnimationActive={false}
                />
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="power"
                  stroke="#10b981"
                  strokeWidth={2}
                  name="Power"
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}