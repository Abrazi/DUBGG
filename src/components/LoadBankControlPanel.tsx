import React, { useState } from 'react';
import { LoadBankStatus } from '../types/loadbank';
import { selectLoadbankLoad, sendLoadbankCommand, setLoadbankModbusEnabled } from '../utils/api';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';

interface LoadBankControlPanelProps {
  loadbank: LoadBankStatus;
  onUpdate: () => void;
}

export function LoadBankControlPanel({ loadbank, onUpdate }: LoadBankControlPanelProps) {
  const [resistiveKw, setResistiveKw] = useState('0');
  const [inductiveKvar, setInductiveKvar] = useState('0');
  const [capacitiveKvar, setCapacitiveKvar] = useState('0');

  const handleApplySelectLoad = async () => {
    const kW = parseInt(resistiveKw) || 0;
    const kVArL = parseInt(inductiveKvar) || 0;
    const kVArC = parseInt(capacitiveKvar) || 0;

    await selectLoadbankLoad(loadbank.id, {
      resistive_kW: kW,
      inductive_kVAr: kVArL,
      capacitive_kVAr: kVArC
    });

    onUpdate();
  };

  const handleCommand = async (cmd: 'enable_modbus_control' | 'disable_modbus_control' | 'apply_load' | 'reject_load') => {
    await sendLoadbankCommand(loadbank.id, cmd);
    onUpdate();
  };

  const handleModbusToggle = async () => {
    await setLoadbankModbusEnabled(loadbank.id, !!loadbank.modbusDisabled);
    onUpdate();
  };

  return (
    <Card className="bg-slate-900 border-slate-700 h-full">
      <CardHeader className="pb-4 border-b border-slate-800">
        <div className="flex items-center justify-between">
          <CardTitle className="text-xl font-bold text-white flex items-center gap-3">
            Load Bank {loadbank.id} Controls
          </CardTitle>
          <div className="flex gap-2">
            <span className={`px-2 py-1 text-xs rounded font-bold ${loadbank.control_on ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' : 'bg-slate-500/20 text-slate-400 border border-slate-500/50'}`}>
              MODBUS CONTROL: {loadbank.control_on ? 'ON' : 'OFF'}
            </span>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-6 space-y-8">
        {/* Modbus Control Toggle */}
        <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50">
          <h4 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Device Level Control</h4>
          <div className="flex gap-3">
             <button
              onClick={() => handleCommand('enable_modbus_control')}
              disabled={loadbank.control_on}
              className={`flex-1 py-3 px-4 rounded font-medium transition-colors ${
                loadbank.control_on
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border-none'
                  : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/50'
              }`}
            >
              Enable Control
            </button>
            <button
              onClick={() => handleCommand('disable_modbus_control')}
              disabled={!loadbank.control_on}
              className={`flex-1 py-3 px-4 rounded font-medium transition-colors ${
                !loadbank.control_on
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border-none'
                  : 'bg-slate-700 text-white hover:bg-slate-600 border border-slate-600'
              }`}
            >
              Disable Control
            </button>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-700/50 flex items-center justify-between">
            <span className="text-slate-300">Simulate Device Failure (TCP Server Online)</span>
             <button
                onClick={handleModbusToggle}
                className={`px-4 py-2 rounded text-sm font-medium ${
                  !loadbank.modbusDisabled
                    ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/50'
                    : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/50'
                }`}
              >
                {!loadbank.modbusDisabled ? 'Disable Server' : 'Enable Server'}
              </button>
          </div>
        </div>

        {/* Load Selection & Action */}
        <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50">
          <h4 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Load Management</h4>
          
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div>
              <label className="text-xs text-slate-400 block mb-1">Resistive (kW)</label>
              <input 
                type="number" 
                value={resistiveKw} 
                onChange={e => setResistiveKw(e.target.value)} 
                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                min="0"
                step="5"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Inductive (kVArL)</label>
              <input 
                type="number" 
                value={inductiveKvar} 
                onChange={e => setInductiveKvar(e.target.value)} 
                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                min="0"
                step="5"
              />
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1">Capacitive (kVArC)</label>
              <input 
                type="number" 
                value={capacitiveKvar} 
                onChange={e => setCapacitiveKvar(e.target.value)} 
                className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white"
                min="0"
                step="5"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <button
              onClick={handleApplySelectLoad}
              className="py-2 bg-blue-500 hover:bg-blue-600 text-white rounded font-medium"
            >
              Select
            </button>
            <button
              onClick={() => handleCommand('apply_load')}
              disabled={!loadbank.control_on}
              className={`py-2 rounded font-medium ${!loadbank.control_on ? 'bg-slate-800 text-slate-600 cursor-not-allowed' : 'bg-emerald-600 hover:bg-emerald-500 text-white'}`}
            >
              Apply Load
            </button>
            <button
              onClick={() => handleCommand('reject_load')}
              disabled={!loadbank.control_on}
              className={`py-2 rounded font-medium ${!loadbank.control_on ? 'bg-slate-800 text-slate-600 cursor-not-allowed' : 'bg-red-600 hover:bg-red-500 text-white'}`}
            >
              Reject Load
            </button>
          </div>
        </div>
        
        {/* Readings */}
         <div className="bg-slate-800/50 p-4 rounded-lg border border-slate-700/50">
          <h4 className="text-sm font-semibold text-slate-300 mb-4 uppercase tracking-wider">Current Readings</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
             <div className="bg-slate-900 p-3 rounded">
                <div className="text-xs text-slate-400">Total Active Power</div>
                <div className="text-xl font-bold text-white">{loadbank.activePower.toFixed(1)} kW</div>
             </div>
             <div className="bg-slate-900 p-3 rounded">
                <div className="text-xs text-slate-400">Total Reactive Power</div>
                <div className="text-xl font-bold text-white">{loadbank.reactivePower.toFixed(1)} kVAr</div>
             </div>
             <div className="bg-slate-900 p-3 rounded">
                <div className="text-xs text-slate-400">Total Apparent Power</div>
                <div className="text-xl font-bold text-white">{loadbank.apparentPower.toFixed(1)} kVA</div>
             </div>
              <div className="bg-slate-900 p-3 rounded">
                <div className="text-xs text-slate-400">Power Factor</div>
                <div className="text-xl font-bold text-white">{loadbank.powerFactor.toFixed(2)}</div>
             </div>
              <div className="bg-slate-900 p-3 rounded">
                <div className="text-xs text-slate-400">Applied (kW)</div>
                <div className="text-xl font-bold text-blue-400">{loadbank.load_applied.toFixed(1)} kW</div>
             </div>
             <div className="bg-slate-900 p-3 rounded">
                <div className="text-xs text-slate-400">Voltage (L1-L2)</div>
                <div className="text-xl font-bold text-white">{loadbank.l1l2Voltage.toFixed(1)} V</div>
             </div>
              <div className="bg-slate-900 p-3 rounded">
                <div className="text-xs text-slate-400">Frequency</div>
                <div className="text-xl font-bold text-white">{loadbank.frequency.toFixed(2)} Hz</div>
             </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
