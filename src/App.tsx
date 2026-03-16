import { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { MonitoringDashboard } from './components/MonitoringDashboard';
import { ControlPanel } from './components/ControlPanel';
import { AlarmPanel } from './components/AlarmPanel';
import { GeneratorsOverview } from './components/GeneratorsOverview';
import { GeneratorLogWindow } from './components/GeneratorLogWindow';
import { AdministrationPage } from './components/AdministrationPage';
import { LoadBanksOverview } from './components/LoadBanksOverview';
import { LoadBankControlPanel } from './components/LoadBankControlPanel';
import { LoadbankLogWindow } from './components/LoadbankLogWindow';
import { GeneratorStatus, Alarm } from './types/generator';
import { LoadBankStatus } from './types/loadbank';
import { fetchAllGenerators, fetchGenerator, fetchAllLoadbanks, fetchLoadbank } from './utils/api';
// using native select instead of custom UI component


function App() {
  const [activeView, setActiveView] = useState<'dashboard' | 'admin'>('dashboard');
  const [allGenerators, setAllGenerators] = useState<GeneratorStatus[]>([]);
  const [selectedGenId, setSelectedGenId] = useState<string>("");
  const [currentGenerator, setCurrentGenerator] = useState<GeneratorStatus | null>(null);

  const [allLoadbanks, setAllLoadbanks] = useState<LoadBankStatus[]>([]);
  const [selectedLbId, setSelectedLbId] = useState<string>("");
  const [currentLoadbank, setCurrentLoadbank] = useState<LoadBankStatus | null>(null);
  const [targetType, setTargetType] = useState<'generator' | 'loadbank'>('generator');

  const [historicalData, setHistoricalData] = useState<Array<{ time: string; voltage: number; power: number; frequency: number }>>([]);
  const [alarms, setAlarms] = useState<Alarm[]>([]);

  // Fetch all generators list
  useEffect(() => {
    const loadGenerators = async () => {
      const data = await fetchAllGenerators();
      setAllGenerators(data);
      if (data.length > 0) {
        // Use functional updates to avoid stale closure over `currentGenerator`.
        setSelectedGenId(prev => prev || data[0].id);
        setCurrentGenerator(prev => prev ?? data[0]);
      }
    };
    loadGenerators();
    const interval = setInterval(loadGenerators, 2000); // Refresh list every 2s
    return () => clearInterval(interval);
  }, []);

  // Fetch specific generator details
  const refreshCurrentGenerator = async () => {
    if (selectedGenId) {
      const data = await fetchGenerator(selectedGenId);
      if (data) {
        setCurrentGenerator(data);
        updateHistoricalData(data);
        checkForAlarms(data);
      }
    }
  };

  useEffect(() => {
    // Clear historical data when changing generators to avoid a "jump" in the chart
    setHistoricalData([]);

    refreshCurrentGenerator();
    const interval = setInterval(refreshCurrentGenerator, 1000); // High refresh rate for selected gen
    return () => clearInterval(interval);
  }, [selectedGenId]);

  // Fetch all load banks list
  useEffect(() => {
    const loadLbs = async () => {
      const data = await fetchAllLoadbanks();
      setAllLoadbanks(data);
      if (data.length > 0) {
        setSelectedLbId(prev => prev || data[0].id);
        setCurrentLoadbank(prev => prev ?? data[0]);
      }
    };
    loadLbs();
    const interval = setInterval(loadLbs, 2000); // Refresh list every 2s
    return () => clearInterval(interval);
  }, []);

  // Fetch specific load bank details
  const refreshCurrentLoadbank = async () => {
    if (selectedLbId) {
      const data = await fetchLoadbank(selectedLbId);
      if (data) {
        setCurrentLoadbank(data);
      }
    }
  };

  useEffect(() => {
    refreshCurrentLoadbank();
    const interval = setInterval(refreshCurrentLoadbank, 1000); // High refresh rate for selected lb
    return () => clearInterval(interval);
  }, [selectedLbId]);

  const updateHistoricalData = (data: GeneratorStatus) => {
    const now = new Date();
    // Use a stable ISO-like time for chart labels to avoid locale-specific formatting issues
    const timeStr = now.getHours().toString().padStart(2, '0') + ':' +
      now.getMinutes().toString().padStart(2, '0') + ':' +
      now.getSeconds().toString().padStart(2, '0');
    setHistoricalData(prev => {
      const newData = [...prev, {
        time: timeStr,
        voltage: data.voltage,
        power: data.activePower,
        frequency: data.frequency
      }];
      return newData.slice(-20); // Keep last 20 points
    });
  };

  const prevFaultStates = useRef<Record<string, Record<string, boolean>>>({});

  const checkForAlarms = (data: GeneratorStatus) => {
    const faultFlags = [
      { key: 'simulateFailToStart' as const, name: 'Fail to Start' },
      { key: 'failRampUp' as const, name: 'Fail Ramp Up' },
      { key: 'failRampDown' as const, name: 'Fail Ramp Down' },
      { key: 'failStartTime' as const, name: 'Fail Start Time' },
      { key: 'isFaulted' as const, name: 'Generator Fault' },
    ];

    if (!prevFaultStates.current[data.id]) {
      prevFaultStates.current[data.id] = {};
      faultFlags.forEach(f => {
        prevFaultStates.current[data.id][f.key] = !!data[f.key];
      });
      return;
    }

    const prev = prevFaultStates.current[data.id];
    const newAlarms: Alarm[] = [];

    faultFlags.forEach(f => {
      const currentVal = !!data[f.key];
      const prevVal = prev[f.key];

      if (currentVal && !prevVal) {
        newAlarms.push({
          id: `${data.id}-${f.key}-on-${Date.now()}`,
          type: 'warning',
          message: `Fault Injected: ${f.name}`,
          timestamp: new Date(),
          acknowledged: false,
          generatorId: data.id
        });
      } else if (!currentVal && prevVal) {
        newAlarms.push({
          id: `${data.id}-${f.key}-off-${Date.now()}`,
          type: 'info',
          message: `Fault Removed: ${f.name}`,
          timestamp: new Date(),
          acknowledged: false,
          generatorId: data.id
        });
      }
      prevFaultStates.current[data.id][f.key] = currentVal;
    });

    if (newAlarms.length > 0) {
      setAlarms(prevAlarms => [...prevAlarms, ...newAlarms]);
    }
  };

  const handleAcknowledgeAlarm = (id: string) => {
    setAlarms(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true } : a));
  };

  const handleClearAlarm = (id: string) => {
    setAlarms(prev => prev.filter(a => a.id !== id));
  };

  const handleClearAllAlarms = () => {
    setAlarms([]);
  };

  return (
    <div className="min-h-screen bg-slate-950">
      <Header
        activeView={activeView}
        onViewChange={setActiveView}
      />

      <div className="flex">
        {/* sidebar overview */}
        <aside className="w-64 bg-slate-900 p-6 flex flex-col gap-6 overflow-y-auto max-h-screen">
          {allGenerators.length > 0 && (
            <GeneratorsOverview generators={allGenerators} />
          )}
          {allLoadbanks.length > 0 && (
            <LoadBanksOverview loadbanks={allLoadbanks} />
          )}
        </aside>

        <main className="flex-1 p-6">
          {activeView === 'admin' ? (
            <AdministrationPage />
          ) : (
            <>
              {/* Target Selector */}
              <div className="mb-6 flex flex-wrap items-center gap-4">
                <div>
                  <label className="text-slate-400 text-sm font-medium mb-2 block">View Type</label>
                  <select
                    value={targetType}
                    onChange={e => setTargetType(e.target.value as 'generator' | 'loadbank')}
                    className="w-full md:w-48 bg-slate-800 border-slate-700 text-white p-2 rounded"
                  >
                    <option value="generator">Generators</option>
                    <option value="loadbank">Load Banks</option>
                  </select>
                </div>

                {targetType === 'generator' ? (
                  <div>
                    <label className="text-slate-400 text-sm font-medium mb-2 block">Select Generator</label>
                    <select
                      value={selectedGenId}
                      onChange={e => setSelectedGenId(e.target.value)}
                      className="w-full md:w-64 bg-slate-800 border-slate-700 text-white p-2 rounded"
                    >
                      {allGenerators.map(gen => (
                        <option
                          key={gen.id}
                          value={gen.id}
                          className="bg-slate-800 text-white"
                        >
                          {gen.id} - {gen.state.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </div>
                ) : (
                  <div>
                    <label className="text-slate-400 text-sm font-medium mb-2 block">Select Load Bank</label>
                    <select
                      value={selectedLbId}
                      onChange={e => setSelectedLbId(e.target.value)}
                      className="w-full md:w-64 bg-slate-800 border-slate-700 text-white p-2 rounded"
                    >
                      {allLoadbanks.map(lb => (
                        <option
                          key={lb.id}
                          value={lb.id}
                          className="bg-slate-800 text-white"
                        >
                          {lb.id} - {lb.load_applied} kW
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {targetType === 'generator' && currentGenerator && (
                <>
                  <MonitoringDashboard generator={currentGenerator} historicalData={historicalData} />

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                      <ControlPanel
                        generator={currentGenerator}
                        onUpdate={refreshCurrentGenerator}
                      />
                    </div>
                    <div>
                      <AlarmPanel
                        alarms={alarms}
                        onAcknowledge={handleAcknowledgeAlarm}
                        onClear={handleClearAlarm}
                        onClearAll={handleClearAllAlarms}
                      />
                    </div>
                  </div>

                  {/* Per-generator live event log */}
                  <GeneratorLogWindow genId={currentGenerator.id} pollInterval={1500} maxEntries={500} />
                </>
              )}

              {targetType === 'loadbank' && currentLoadbank && (
                <div className="grid grid-cols-1 gap-6 max-w-4xl">
                  <LoadBankControlPanel loadbank={currentLoadbank} onUpdate={refreshCurrentLoadbank} />
                  <LoadbankLogWindow lbId={currentLoadbank.id} pollInterval={1500} maxEntries={500} />
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;