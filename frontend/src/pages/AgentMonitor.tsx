import React, { useState, useEffect } from "react";
import { Loader2, CheckCircle2, Cpu, Clock, History, BarChart3 } from "lucide-react";
import { api } from "../api/client";

interface TimelineTask {
  id: string;
  task_name: string;
  description: string;
  assignee: string;
  status: string;
  result?: any;
  created_at: string;
  updated_at: string;
}

interface HealingAttempt {
  attempt_number: number;
  error_message: string;
  planned_fix: string;
  status: string;
  created_at: string;
}

interface Iteration {
  iteration_number: number;
  explanation: string;
  code_diff: string;
  test_passed: boolean;
  created_at: string;
}

interface QualityMetrics {
  security: number;
  performance: number;
  style: number;
  overall: number;
}

interface MonitorData {
  run_id: string;
  timeline: TimelineTask[];
  healing_attempts: HealingAttempt[];
  iterations: Iteration[];
  quality_metrics?: QualityMetrics;
}

interface AgentRun {
  id: string;
  branch_name: string;
  status: string;
  created_at: string;
}

export const AgentMonitor: React.FC = () => {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [monitorData, setMonitorData] = useState<MonitorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchingDetails, setFetchingDetails] = useState(false);

  useEffect(() => {
    const fetchRuns = async () => {
      try {
        const data = await api.get<AgentRun[]>("/runs");
        setRuns(data);
        if (data.length > 0 && !selectedRunId) {
          setSelectedRunId(data[0].id);
        }
      } catch (err) {
        console.error("Failed to load runs:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchRuns();
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchTimeline = async () => {
    if (!selectedRunId) return;
    setFetchingDetails(true);
    try {
      const resp = await api.get<MonitorData>(`/intelligence/run/${selectedRunId}/timeline`);
      setMonitorData(resp);
    } catch (err) {
      console.error("Failed to load timeline:", err);
      setMonitorData(null);
    } finally {
      setFetchingDetails(false);
    }
  };

  useEffect(() => {
    fetchTimeline();
    const interval = setInterval(fetchTimeline, 3000); // quick poll for active run updates
    return () => clearInterval(interval);
  }, [selectedRunId]);

  return (
    <div className="space-y-8 animate-fade-in max-w-none">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
            <Cpu className="w-8 h-8 text-indigo-400" />
            Agent Monitor
          </h1>
          <p className="text-gray-400 text-sm mt-1">Audit active agent timeline tasks, execution queues, self-healing retries, and quality scores.</p>
        </div>

        <div className="w-64 space-y-1">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Target Execution Run</label>
          <select
            value={selectedRunId}
            onChange={(e) => setSelectedRunId(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm font-semibold"
          >
            <option value="" disabled>Select Execution Run</option>
            {runs.map((r) => (
              <option key={r.id} value={r.id}>{r.branch_name} ({r.status})</option>
            ))}
          </select>
        </div>
      </div>

      {loading && runs.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60 flex items-center justify-center min-h-[300px]">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
            <span className="text-sm text-gray-400">Loading active agent runs...</span>
          </div>
        </div>
      ) : !selectedRunId ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
          <Cpu className="w-12 h-12 text-gray-600 mx-auto mb-4 animate-pulse" />
          <h3 className="text-white font-bold text-lg mb-1">No active runs recorded</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">Triggers are scheduled automatically once issue assignments are accepted.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* Left Panel: Tasks execution timeline logs (LangGraph-like trace) */}
          <div className="lg:col-span-1 glass-panel p-6 rounded-2xl border border-gray-800/80 space-y-5">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Clock className="w-4.5 h-4.5 text-indigo-400" />
              Agent Timeline Trace
            </h3>
            
            {fetchingDetails && !monitorData ? (
              <div className="flex justify-center py-10">
                <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
              </div>
            ) : monitorData?.timeline.length === 0 ? (
              <div className="text-center py-6 text-xs text-gray-500 italic">No tasks logged. Preparing node structures...</div>
            ) : (
              <div className="relative border-l border-gray-800 ml-3.5 pl-6 space-y-6">
                {monitorData?.timeline.map((task) => (
                  <div key={task.id} className="relative space-y-1 text-xs">
                    {/* Timeline Node Point Indicator */}
                    <span className={`absolute -left-[31px] top-1 p-1 rounded-full border ${
                      task.status === "completed" 
                        ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" 
                        : task.status === "running"
                        ? "bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse"
                        : "bg-gray-800 border-gray-750 text-gray-500"
                    }`}>
                      <CheckCircle2 className="w-2.5 h-2.5" />
                    </span>

                    <h4 className="font-bold text-white">{task.task_name}</h4>
                    <p className="text-gray-400 text-[11px] leading-relaxed">{task.description}</p>
                    <span className="text-[10px] text-gray-500 font-semibold block uppercase">Assignee: {task.assignee}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Panel: Self-Healing cycles, Diffs & Quality Scores */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Radar-like Quality Scores */}
            {monitorData?.quality_metrics && (
              <div className="glass-panel p-6 rounded-2xl border border-indigo-500/10 shadow-lg space-y-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <BarChart3 className="w-4.5 h-4.5 text-indigo-400" />
                  AI Review Quality Scores
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {[
                    { label: "Security Profile", val: monitorData.quality_metrics.security, color: "text-emerald-400 bg-emerald-950/20" },
                    { label: "Performance", val: monitorData.quality_metrics.performance, color: "text-blue-400 bg-blue-950/20" },
                    { label: "Code Style", val: monitorData.quality_metrics.style, color: "text-purple-400 bg-purple-950/20" },
                    { label: "Overall Quality", val: monitorData.quality_metrics.overall, color: "text-indigo-400 bg-indigo-950/20" }
                  ].map((m, idx) => (
                    <div key={idx} className="p-4 bg-gray-950/60 border border-gray-850 rounded-xl text-center space-y-1">
                      <span className="text-[10px] text-gray-500 uppercase font-bold block">{m.label}</span>
                      <span className={`inline-block text-xl font-extrabold px-3 py-1 rounded-lg ${m.color}`}>
                        {m.val}/100
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Self-Healing Dashboard */}
            <div className="glass-panel p-6 rounded-2xl border border-gray-800/80 space-y-4">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <History className="w-4.5 h-4.5 text-indigo-400" />
                Self-Healing Loop (Autonomous QA Repairs)
              </h3>
              
              {monitorData?.healing_attempts.length === 0 ? (
                <div className="p-8 text-center text-xs text-gray-500 italic bg-gray-950/40 rounded-xl border border-gray-900">
                  No repair cycles required. Compilation and validations passed clean on attempt #1.
                </div>
              ) : (
                <div className="space-y-4">
                  {monitorData?.healing_attempts.map((attempt) => (
                    <div key={attempt.attempt_number} className="border border-gray-800/60 rounded-xl overflow-hidden">
                      <div className="bg-gray-950/40 px-4 py-3 border-b border-gray-800/60 flex justify-between items-center text-xs">
                        <span className="font-bold text-white">Repair Attempt #{attempt.attempt_number}</span>
                        <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded uppercase tracking-wider ${
                          attempt.status === "succeeded" 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                            : "bg-red-500/10 text-red-400 border border-red-500/20"
                        }`}>
                          {attempt.status}
                        </span>
                      </div>
                      
                      <div className="p-4 space-y-3 bg-[#02050e]/60">
                        <div className="space-y-1">
                          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Traceback Error Logs</span>
                          <pre className="p-3 bg-black/40 border border-gray-900 text-[10px] text-red-300 font-mono overflow-x-auto max-h-32 rounded-lg whitespace-pre-wrap leading-relaxed">
                            {attempt.error_message}
                          </pre>
                        </div>
                        
                        <div className="text-xs text-gray-400">
                          <span className="font-semibold text-gray-300">Action:</span> {attempt.planned_fix}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
          
        </div>
      )}
    </div>
  );
};
