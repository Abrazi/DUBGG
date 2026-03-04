import { Alarm } from '../types/hmi';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Bell, AlertTriangle, Info, Check, X } from 'lucide-react';

interface AlarmPanelProps {
  alarms: Alarm[];
  onAcknowledge: (id: string) => void;
  onClear: (id: string) => void;
  onClearAll: () => void;
}

export function AlarmPanel({ alarms, onAcknowledge, onClear, onClearAll }: AlarmPanelProps) {
  const getAlarmIcon = (type: Alarm['type']) => {
    switch (type) {
      case 'critical':
        return <X className="w-5 h-5" />;
      case 'warning':
        return <AlertTriangle className="w-5 h-5" />;
      case 'info':
        return <Info className="w-5 h-5" />;
    }
  };

  const getAlarmColor = (type: Alarm['type']) => {
    switch (type) {
      case 'critical':
        return 'bg-red-500/20 border-red-500 text-red-400';
      case 'warning':
        return 'bg-amber-500/20 border-amber-500 text-amber-400';
      case 'info':
        return 'bg-blue-500/20 border-blue-500 text-blue-400';
    }
  };

  const activeAlarms = alarms.filter(a => !a.acknowledged);
  const acknowledgedAlarms = alarms.filter(a => a.acknowledged);

  return (
    <Card className="bg-slate-800 border-slate-700">
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-slate-300 flex items-center gap-2">
          <Bell className="w-5 h-5" />
          Alarms & Notifications
          {activeAlarms.length > 0 && (
            <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
              {activeAlarms.length}
            </span>
          )}
        </CardTitle>
        <Button onClick={onClearAll} variant="outline" size="sm" className="bg-slate-700 text-slate-300 border-slate-600 hover:bg-slate-600">
          Clear All
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Active Alarms */}
          {activeAlarms.length > 0 && (
            <div>
              <h3 className="text-slate-400 text-sm font-medium mb-3">Active</h3>
              <div className="space-y-2">
                {activeAlarms.map((alarm) => (
                  <div key={alarm.id} className={`p-4 rounded-lg border ${getAlarmColor(alarm.type)} ${alarm.acknowledged ? 'opacity-50' : ''}`}>
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">{getAlarmIcon(alarm.type)}</div>
                        <div>
                          <p className="font-medium">{alarm.message}</p>
                          <p className="text-sm opacity-75 mt-1">
                            {alarm.timestamp.toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => onAcknowledge(alarm.id)}
                          size="sm"
                          variant="outline"
                          className="bg-transparent border-current hover:bg-current/20"
                        >
                          <Check className="w-4 h-4" />
                        </Button>
                        <Button
                          onClick={() => onClear(alarm.id)}
                          size="sm"
                          variant="outline"
                          className="bg-transparent border-current hover:bg-current/20"
                        >
                          <X className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Acknowledged Alarms */}
          {acknowledgedAlarms.length > 0 && (
            <div>
              <h3 className="text-slate-400 text-sm font-medium mb-3">Acknowledged</h3>
              <div className="space-y-2">
                {acknowledgedAlarms.map((alarm) => (
                  <div key={alarm.id} className={`p-4 rounded-lg border ${getAlarmColor(alarm.type)} opacity-50`}>
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className="mt-0.5">{getAlarmIcon(alarm.type)}</div>
                        <div>
                          <p className="font-medium">{alarm.message}</p>
                          <p className="text-sm opacity-75 mt-1">
                            {alarm.timestamp.toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                      <Button
                        onClick={() => onClear(alarm.id)}
                        size="sm"
                        variant="outline"
                        className="bg-transparent border-current hover:bg-current/20"
                      >
                        <X className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {alarms.length === 0 && (
            <div className="text-center py-8 text-slate-500">
              <Bell className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No active alarms</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}