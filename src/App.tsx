import { useState, useEffect, useRef } from 'react';
import { Header } from './components/Header';
import { MonitoringDashboard } from './components/MonitoringDashboard';
import { ControlPanel } from './components/ControlPanel';
import { AlarmPanel } from './components/AlarmPanel';
import { GeneratorsOverview } from './components/GeneratorsOverview';
import { GeneratorLogWindow } from './components/GeneratorLogWindow';
import { AdministrationPage } from './components/AdministrationPage';
import { GeneratorStatus, Alarm } from './types/generator';
import { fetchAllGenerators, fetchGenerator } from './utils/api';
// using native select instead of custom UI component


function App() {
  const [activeView, setActiveView] = useState<'dashboard' | 'admin'>('dashboard');
  const [allGenerators, setAllGenerators] = useState<GeneratorStatus[]>([]);
  const [selectedGenId, setSelectedGenId] = useState<string>("");
  const [currentGenerator, setCurrentGenerator] = useState<GeneratorStatus | null>(null);
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
        status={{
          isRunning: currentGenerator?.isRunning || false,
          uptime: 0,
          cpuUsage: 0,
          memoryUsage: 0,
          temperature: 0,
          pressure: 0,
          flowRate: 0
        }}
        onToggleSystem={() => { }}
        activeView={activeView}
        onViewChange={setActiveView}
      />

      <div className="flex">
        {/* sidebar overview */}
        <aside className="w-64 bg-slate-900 p-6">
          {allGenerators.length > 0 && (
            <GeneratorsOverview generators={allGenerators} />
          )}
        </aside>

        <main className="flex-1 p-6">
          {activeView === 'admin' ? (
            <AdministrationPage />
          ) : (
            <>
              {/* Generator Selector */}
              <div className="mb-6">
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

              {currentGenerator && (
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
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;