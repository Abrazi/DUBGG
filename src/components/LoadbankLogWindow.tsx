import { useEffect, useRef, useState, useCallback } from 'react';
import { GeneratorLogEntry, fetchLoadbankLogs } from '../utils/api';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Terminal, Pause, Play, Trash2, Copy } from 'lucide-react';

interface LoadbankLogWindowProps {
    lbId: string;
    /** How often (ms) to poll the backend for new log entries. Default 1500. */
    pollInterval?: number;
    /** Max entries shown in the window. Default 500. */
    maxEntries?: number;
}

function levelColor(level: string): string {
    switch (level.toUpperCase()) {
        case 'ERROR':
        case 'CRITICAL':
            return 'text-red-400';
        case 'WARNING':
            return 'text-amber-400';
        case 'DEBUG':
            return 'text-slate-500';
        default:
            return 'text-blue-400';
    }
}

function levelBadge(level: string): string {
    switch (level.toUpperCase()) {
        case 'ERROR':
        case 'CRITICAL':
            return 'bg-red-500/20 text-red-400 border border-red-500/40';
        case 'WARNING':
            return 'bg-amber-500/20 text-amber-400 border border-amber-500/40';
        case 'DEBUG':
            return 'bg-slate-700/60 text-slate-500 border border-slate-600/40';
        default:
            return 'bg-blue-500/20 text-blue-400 border border-blue-500/40';
    }
}

export function LoadbankLogWindow({
    lbId,
    pollInterval = 1500,
    maxEntries = 500,
}: LoadbankLogWindowProps) {
    const [entries, setEntries] = useState<GeneratorLogEntry[]>([]);
    const [paused, setPaused] = useState(false);
    const [copied, setCopied] = useState(false);
    const [autoScroll, setAutoScroll] = useState(true);
    const scrollRef = useRef<HTMLDivElement>(null);
    const pausedRef = useRef(paused);
    pausedRef.current = paused;

    // Fetch logs from backend
    const refresh = useCallback(async () => {
        if (pausedRef.current) return;
        const logs = await fetchLoadbankLogs(lbId, maxEntries);
        setEntries(logs);
    }, [lbId, maxEntries]);

    useEffect(() => {
        refresh();
        const id = setInterval(refresh, pollInterval);
        return () => clearInterval(id);
    }, [refresh, pollInterval]);

    // Auto-scroll to bottom when new entries arrive
    useEffect(() => {
        if (autoScroll && scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [entries, autoScroll]);

    // Detect manual scroll up to disengage auto-scroll
    const handleScroll = () => {
        if (!scrollRef.current) return;
        const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
        const atBottom = scrollHeight - scrollTop - clientHeight < 8;
        setAutoScroll(atBottom);
    };

    const handleClear = () => setEntries([]);

    const handleCopy = async () => {
        const text = entries
            .map(e => `[${e.timestamp}] [${e.level}] ${e.message}`)
            .join('\n');
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    return (
        <Card className="bg-slate-900 border-slate-700 flex flex-col mt-6">
            <CardHeader className="pb-2 pt-3 px-4 border-b border-slate-700/60">
                <div className="flex items-center justify-between gap-2">
                    <CardTitle className="text-slate-200 text-sm font-semibold flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-blue-400" />
                        Load Bank Event Log — <span className="text-blue-300">{lbId}</span>
                    </CardTitle>
                    <div className="flex items-center gap-1">
                        {/* Pause / Resume */}
                        <button
                            onClick={() => setPaused(p => !p)}
                            title={paused ? 'Resume' : 'Pause'}
                            className={`p-1.5 rounded transition-colors ${paused
                                ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                                : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                                }`}
                        >
                            {paused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
                        </button>

                        {/* Copy */}
                        <button
                            onClick={handleCopy}
                            title="Copy all logs"
                            className="p-1.5 rounded text-slate-400 hover:bg-slate-700 hover:text-slate-200 transition-colors"
                        >
                            {copied ? (
                                <span className="text-xs text-emerald-400 px-1">Copied!</span>
                            ) : (
                                <Copy className="w-3.5 h-3.5" />
                            )}
                        </button>

                        {/* Clear */}
                        <button
                            onClick={handleClear}
                            title="Clear log"
                            className="p-1.5 rounded text-slate-400 hover:bg-red-500/20 hover:text-red-400 transition-colors"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    </div>
                </div>

                {/* Status bar */}
                <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-slate-500">
                        {entries.length} entr{entries.length === 1 ? 'y' : 'ies'}
                    </span>
                    {paused && (
                        <span className="text-xs text-amber-400 animate-pulse font-medium">● PAUSED</span>
                    )}
                    {!autoScroll && !paused && (
                        <button
                            onClick={() => {
                                setAutoScroll(true);
                                if (scrollRef.current) {
                                    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                                }
                            }}
                            className="text-xs text-blue-400 underline"
                        >
                            Scroll to bottom
                        </button>
                    )}
                </div>
            </CardHeader>

            <CardContent className="p-0 overflow-hidden">
                <div
                    ref={scrollRef}
                    onScroll={handleScroll}
                    className="h-64 overflow-y-auto font-mono text-xs leading-relaxed"
                    style={{ background: 'linear-gradient(to bottom, #0f172a, #0d1526)' }}
                >
                    {entries.length === 0 ? (
                        <div className="flex items-center justify-center h-full text-slate-600">
                            <span>No load bank events yet…</span>
                        </div>
                    ) : (
                        <table className="w-full border-collapse">
                            <tbody>
                                {entries.map((e, i) => (
                                    <tr
                                        key={i}
                                        className={`border-b border-slate-800/50 transition-colors hover:bg-slate-800/40 ${i === 0 && !paused ? 'animate-pulse-once' : ''
                                            }`}
                                    >
                                        {/* Timestamp */}
                                        <td className="pl-3 pr-2 py-0.5 whitespace-nowrap text-slate-600 align-top w-[160px]">
                                            {e.timestamp.split(' ')[1]}
                                        </td>

                                        {/* Level badge */}
                                        <td className="pr-2 py-0.5 whitespace-nowrap align-top w-[80px]">
                                            <span className={`px-1.5 py-0 rounded text-[10px] font-semibold tracking-wide ${levelBadge(e.level)}`}>
                                                {e.level.slice(0, 4)}
                                            </span>
                                        </td>

                                        {/* Message */}
                                        <td className={`pr-3 py-0.5 break-all ${levelColor(e.level)}`}>
                                            {e.message}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
