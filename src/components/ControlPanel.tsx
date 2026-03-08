import { useState, useEffect, useRef } from 'react';
import { GeneratorStatus } from '../types/generator';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Play, Square, RotateCcw, ShieldAlert, Zap, WifiOff, Wifi } from 'lucide-react';
import { sendCommand, updateGeneratorConfig, setModbusEnabled } from '../utils/api';

interface ControlPanelProps {
  generator: GeneratorStatus;
  onUpdate: () => void;
}

interface SimConfig {
  simulateFailToStart: boolean;
  failRampUp: boolean;
  failRampDown: boolean;
  failStartTime: boolean;
  startDelay: number;
  stopDelay: number;
  serviceMode: 'off' | 'manual' | 'auto';
}
export function ControlPanel({ generator, onUpdate }: ControlPanelProps) {
  const [config, setConfig] = useState<SimConfig>({
    simulateFailToStart: generator.simulateFailToStart || false,
    failRampUp: generator.failRampUp || false,
    failRampDown: generator.failRampDown || false,
    failStartTime: generator.failStartTime || false,
    startDelay: generator.startDelay || 0,
    stopDelay: generator.stopDelay || 0,
    serviceMode: generator.serviceMode || 'auto',
  });

  useEffect(() => {
    setConfig({
      simulateFailToStart: generator.simulateFailToStart || false,
      failRampUp: generator.failRampUp || false,
      failRampDown: generator.failRampDown || false,
      failStartTime: generator.failStartTime || false,
      startDelay: generator.startDelay || 0,
      stopDelay: generator.stopDelay || 0,
      serviceMode: generator.serviceMode || 'auto',
    });
  }, [generator]);

  const handleCommand = async (
    cmd:
      | 'start'
      | 'stop'
      | 'reset_fault'
      | 'open_breaker'
      | 'close_breaker'
      | 'inject_fault'
      | 'deexcite_on'
      | 'deexcite_off'
  ) => {
    const success = await sendCommand(generator.id, cmd as any);
    if (success) {
      // Trigger a refresh after a short delay to allow state change
      setTimeout(onUpdate, 500);
    }
  };

  const applyConfig = async () => {
    const success = await updateGeneratorConfig(generator.id, {
      simulate_fail_to_start: config.simulateFailToStart,
      fail_ramp_up: config.failRampUp,
      fail_ramp_down: config.failRampDown,
      fail_start_time: config.failStartTime,
      start_delay: config.startDelay,
      stop_delay: config.stopDelay,
      service_mode: config.serviceMode,
    });
    if (success) {
      setTimeout(onUpdate, 500);
    }
  };

  // whenever config object changes, push update to backend automatically
  const firstUpdate = useRef(true);
  useEffect(() => {
    if (firstUpdate.current) {
      firstUpdate.current = false;
      return;
    }
    applyConfig();
  }, [config]);

  const handleModbusToggle = async (enable: boolean) => {
    const success = await setModbusEnabled(generator.id, enable);
    if (success) {
      setTimeout(onUpdate, 600);
    }
  };

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader>
        <CardTitle className="text-slate-300 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5" />
          Manual Controls
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Button
            onClick={() => handleCommand('start')}
            disabled={generator.state === 'running' || generator.state === 'starting'}
            className="bg-emerald-600 hover:bg-emerald-700 text-white h-20 flex flex-col items-center justify-center gap-2"
          >
            <Play className="w-6 h-6" />
            <span>Start Gen</span>
          </Button>

          <Button
            onClick={() => handleCommand('stop')}
            disabled={generator.state === 'standstill' || generator.state === 'shutdown'}
            className="bg-red-600 hover:bg-red-700 text-white h-20 flex flex-col items-center justify-center gap-2"
          >
            <Square className="w-6 h-6" />
            <span>Stop Gen</span>
          </Button>

          <Button
            onClick={() => handleCommand('reset_fault')}
            disabled={!generator.isFaulted}
            className="bg-amber-600 hover:bg-amber-700 text-white h-20 flex flex-col items-center justify-center gap-2"
          >
            <RotateCcw className="w-6 h-6" />
            <span>Reset Fault</span>
          </Button>

          <Button
            onClick={() => handleCommand(generator.breakerClosed ? 'open_breaker' : 'close_breaker')}
            className={`${generator.breakerClosed ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'} text-white h-20 flex flex-col items-center justify-center gap-2`}
          >
            <Zap className="w-6 h-6" />
            <span>{generator.breakerClosed ? 'Open Breaker' : 'Close Breaker'}</span>
          </Button>
        </div>

        <div className="space-y-4">
          <Button
            onClick={() => handleCommand('deexcite_on')}
            disabled={generator.deexcited || generator.state !== 'running'}
            className="bg-purple-600 hover:bg-purple-700 text-white h-20 w-full flex items-center justify-center gap-2"
          >
            Deexcite ON
          </Button>
          <Button
            onClick={() => handleCommand('deexcite_off')}
            disabled={!generator.deexcited || generator.state !== 'running'}
            className="bg-purple-600 hover:bg-purple-700 text-white h-20 w-full flex items-center justify-center gap-2"
          >
            Deexcite OFF
          </Button>
        </div>

        <div className="space-y-4">
          <Button
            onClick={() => handleCommand('inject_fault')}
            className="bg-red-500 hover:bg-red-600 text-white h-12 w-full flex items-center justify-center gap-2"
          >
            <ShieldAlert className="w-5 h-5" />
            <span>Inject Fault</span>
          </Button>

          <div className="border-t border-slate-700 pt-4">
            <h4 className="text-slate-300 mb-2">Simulation Options</h4>
            <div className="grid grid-cols-2 gap-2">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={config.simulateFailToStart}
                  onChange={e => setConfig({ ...config, simulateFailToStart: e.target.checked })}
                />
                Fail To Start
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={config.failRampUp}
                  onChange={e => setConfig({ ...config, failRampUp: e.target.checked })}
                />
                Fail Ramp Up
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={config.failRampDown}
                  onChange={e => setConfig({ ...config, failRampDown: e.target.checked })}
                />
                Fail Ramp Down
              </label>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={config.failStartTime}
                  onChange={e => setConfig({ ...config, failStartTime: e.target.checked })}
                />
                Fail Start Time
              </label>
            </div>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <input
                type="number"
                value={config.startDelay}
                onChange={e => setConfig({ ...config, startDelay: Number(e.target.value) })}
                className="w-full bg-slate-700 text-white p-1 rounded"
                placeholder="Start Delay"
              />
              <input
                type="number"
                value={config.stopDelay}
                onChange={e => setConfig({ ...config, stopDelay: Number(e.target.value) })}
                className="w-full bg-slate-700 text-white p-1 rounded"
                placeholder="Stop Delay"
              />
            </div>
            <div className="mt-4">
              <label className="block text-sm text-slate-300 mb-1">Service Switch Mode</label>
              <select
                value={config.serviceMode}
                onChange={e => setConfig({ ...config, serviceMode: e.target.value as 'off' | 'manual' | 'auto' })}
                className="w-full bg-slate-700 text-white p-1 rounded"
              >
                <option value="auto">Auto</option>
                <option value="manual">Manual</option>
                <option value="off">Off</option>
              </select>
            </div>
            {/* button removed - config updates are applied automatically */}
          </div>
        </div>

        <div className="bg-slate-900 p-4 rounded-lg border border-slate-700">
          <h4 className="text-slate-400 text-sm font-medium mb-3">Breaker Status</h4>
          <div className="flex items-center justify-between">
            <span className="text-slate-300">Generator Circuit Breaker</span>
            <div className={`px-3 py-1 rounded-full text-sm font-medium ${generator.breakerClosed ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
              {generator.breakerClosed ? 'CLOSED' : 'OPEN'}
            </div>
          </div>
        </div>

        {/* Modbus Device Failure Simulation */}
        <div className={`p-4 rounded-lg border-2 ${generator.modbusDisabled
            ? 'bg-red-950/40 border-red-600/60'
            : 'bg-slate-900 border-slate-700'
          }`}>
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-slate-300 text-sm font-semibold flex items-center gap-2">
              {generator.modbusDisabled
                ? <WifiOff className="w-4 h-4 text-red-400" />
                : <Wifi className="w-4 h-4 text-emerald-400" />}
              Modbus Device Status
            </h4>
            <span className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide ${generator.modbusDisabled
                ? 'bg-red-600/30 text-red-300 border border-red-500/50'
                : 'bg-emerald-600/20 text-emerald-400 border border-emerald-500/30'
              }`}>
              {generator.modbusDisabled ? '⬛ OFFLINE — Device Failure' : '🟢 ONLINE'}
            </span>
          </div>
          <p className="text-slate-500 text-xs mb-3">
            {generator.modbusDisabled
              ? 'The Modbus TCP server is offline. External Modbus masters cannot reach this device. Internal simulation continues.'
              : 'The Modbus TCP server is reachable on the network. External Modbus masters can connect normally.'}
          </p>
          <div className="grid grid-cols-2 gap-2">
            <Button
              onClick={() => handleModbusToggle(false)}
              disabled={generator.modbusDisabled === true}
              className="bg-orange-700 hover:bg-orange-800 disabled:opacity-40 text-white h-12 flex items-center justify-center gap-2 text-sm"
            >
              <WifiOff className="w-4 h-4" />
              Simulate Device Failure
            </Button>
            <Button
              onClick={() => handleModbusToggle(true)}
              disabled={!generator.modbusDisabled}
              className="bg-emerald-700 hover:bg-emerald-800 disabled:opacity-40 text-white h-12 flex items-center justify-center gap-2 text-sm"
            >
              <Wifi className="w-4 h-4" />
              Enable Device
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}