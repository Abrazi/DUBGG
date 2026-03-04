import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { MonitoringDashboard } from './components/MonitoringDashboard';
import { ControlPanel } from './components/ControlPanel';
import { AlarmPanel } from './components/AlarmPanel';
import { GeneratorsOverview } from './components/GeneratorsOverview';
import { GeneratorStatus, Alarm } from './types/generator';
import { fetchAllGenerators, fetchGenerator } from './utils/api';
// using native select instead of custom UI component


function App() {
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
    refreshCurrentGenerator();
    const interval = setInterval(refreshCurrentGenerator, 1000); // High refresh rate for selected gen
    return () => clearInterval(interval);
  }, [selectedGenId]);

  const updateHistoricalData = (data: GeneratorStatus) => {
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
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

  const checkForAlarms = (data: GeneratorStatus) => {
    if (data.isFaulted) {
      const existingAlarm = alarms.find(a => a.generatorId === data.id && a.type === 'critical');
      if (!existingAlarm) {
        setAlarms(prev => [...prev, {
          id: `${data.id}-${Date.now()}`,
          type: 'critical',
          message: `Generator ${data.id} entered FAULT state`,
          timestamp: new Date(),
          acknowledged: false,
          generatorId: data.id
        }]);
      }
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
        onToggleSystem={() => {}} 
      />
      
      <div className="flex">
        {/* sidebar overview */}
        <aside className="w-64 bg-slate-900 p-6">
          {allGenerators.length > 0 && (
            <GeneratorsOverview generators={allGenerators} />
          )}
        </aside>

        <main className="flex-1 p-6">
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
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;