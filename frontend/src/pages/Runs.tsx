import React, { useState, useEffect } from "react";
import { Terminal as TerminalIcon, Loader2, RefreshCw, ChevronRight } from "lucide-react";
import { api } from "../api/client";

interface AgentLog {
  id: string;
  stage: string;
  message: string;
  data?: any;
  created_at: string;
}

interface AgentRun {
  id: string;
  repository_id: string;
  issue_id: string;
  user_id: string;
  branch_name: string;
  provider: string;
  status: string;
  created_at: string;
  updated_at: string;
  logs: AgentLog[];
}

export const Runs: React.FC = () => {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchRuns = async () => {
    try {
      const data = await api.get<AgentRun[]>("/runs");
      setRuns(data);
      
      // Keep selected run logs updated
      if (selectedRun) {
        const updatedRun = data.find((r) => r.id === selectedRun.id);
        if (updatedRun) {
          setSelectedRun(updatedRun);
        }
      }
    } catch (err) {
      console.error("Failed to load runs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    // Poll runs and logs state every 3 seconds to show real-time progress
    const interval = setInterval(fetchRuns, 3000);
    return () => clearInterval(interval);
  }, [selectedRun?.id]);

  const handleSelectRun = (run: AgentRun) => {
    setSelectedRun(run);
  };

  const forceSync = async () => {
    setRefreshing(true);
    await fetchRuns();
    setRefreshing(false);
  };

  // Helper to get status color classes
  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "failed":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      case "pending":
        return "bg-gray-800 text-gray-400 border-gray-700";
      default:
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20 animate-pulse";
    }
  };

  const getStageBadgeColor = (stage: string) => {
    switch (stage) {
      case "workspace": return "text-indigo-400 bg-indigo-950/20 border-indigo-500/10";
      case "context": return "text-blue-400 bg-blue-950/20 border-blue-500/10";
      case "coding": return "text-purple-400 bg-purple-950/20 border-purple-500/10";
      case "validation": return "text-amber-400 bg-amber-950/20 border-amber-500/10";
      case "review": return "text-cyan-400 bg-cyan-950/20 border-cyan-500/10";
      case "commit": return "text-emerald-400 bg-emerald-950/20 border-emerald-500/10";
      case "pr": return "text-pink-400 bg-pink-950/20 border-pink-500/10";
      default: return "text-gray-400 bg-gray-900 border-gray-800";
    }
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-none">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Agent Runs</h1>
          <p className="text-gray-400 text-sm mt-1">Trace, audit, and inspect autonomous code generation workspace logs in real time.</p>
        </div>
        
        <button
          onClick={forceSync}
          disabled={refreshing}
          className="flex items-center gap-2 text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 hover:bg-indigo-950/40 py-2.5 px-4 rounded-xl transition"
        >
          {refreshing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          Sync Logs
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        </div>
      ) : runs.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
          <TerminalIcon className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No agent runs recorded</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">Runs are automatically triggered when an issue assignment request is approved.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* Left Panel: Runs List */}
          <div className="lg:col-span-1 space-y-4 max-h-[600px] overflow-y-auto pr-2">
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest px-1">Active Executions</h2>
            <div className="space-y-3">
              {runs.map((run) => {
                const isSelected = selectedRun?.id === run.id;
                return (
                  <button
                    key={run.id}
                    onClick={() => handleSelectRun(run)}
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      isSelected 
                        ? "bg-indigo-600/10 border-indigo-500/30 shadow-indigo-600/5 shadow" 
                        : "glass-card hover:border-gray-800 border-gray-900"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2.5">
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider border ${getStatusColor(run.status)}`}>
                        {run.status}
                      </span>
                      <span className="text-[10px] text-gray-500">{new Date(run.created_at).toLocaleTimeString()}</span>
                    </div>
                    
                    <h4 className="font-bold text-white text-xs truncate mb-1">Branch: {run.branch_name}</h4>
                    <div className="flex justify-between items-center text-[10px] text-gray-400">
                      <span>Provider: {run.provider}</span>
                      <span className="text-indigo-400 font-semibold flex items-center gap-0.5 hover:underline">
                        Logs
                        <ChevronRight className="w-3 h-3" />
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Panel: Selected Run Logs Console */}
          <div className="lg:col-span-2 space-y-4">
            {selectedRun ? (
              <div className="glass-panel rounded-2xl border border-gray-800/80 overflow-hidden flex flex-col h-[600px]">
                {/* Console Header */}
                <div className="bg-[#030712]/80 border-b border-gray-800/80 px-6 py-4 flex justify-between items-center">
                  <div>
                    <h3 className="font-bold text-white text-sm">Console Output: {selectedRun.branch_name}</h3>
                    <span className="text-[10px] text-gray-400 block mt-0.5">Run ID: {selectedRun.id}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-bold px-2.5 py-1 rounded-md border ${getStatusColor(selectedRun.status)}`}>
                      Status: {selectedRun.status}
                    </span>
                  </div>
                </div>

                {/* Console Log Body */}
                <div className="flex-1 bg-[#02050e]/95 p-6 font-mono text-xs overflow-y-auto space-y-4 text-gray-300">
                  <div className="text-gray-500 select-none border-b border-gray-900 pb-2 mb-4">
                    [System] Initializing session logs pipeline...
                  </div>
                  
                  {selectedRun.logs.length === 0 ? (
                    <div className="text-gray-500 italic">No output logs generated for this run yet.</div>
                  ) : (
                    selectedRun.logs.map((log) => (
                      <div key={log.id} className="space-y-1 animate-fade-in">
                        <div className="flex items-start gap-3">
                          <span className="text-gray-600 select-none">{new Date(log.created_at).toLocaleTimeString()}</span>
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider select-none ${getStageBadgeColor(log.stage)}`}>
                            {log.stage}
                          </span>
                          <span className="text-gray-200 font-semibold">{log.message}</span>
                        </div>
                        
                        {/* Expandable/detailed JSON data or error message log */}
                        {log.data && (
                          <div className="ml-24 p-3 bg-gray-950/60 border border-gray-900 rounded-lg max-w-full overflow-x-auto text-[11px] text-gray-400 max-h-48">
                            {typeof log.data === "string" ? (
                              <pre className="whitespace-pre-wrap">{log.data}</pre>
                            ) : (
                              <pre>{JSON.stringify(log.data, null, 2)}</pre>
                            )}
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </div>
            ) : (
              <div className="glass-panel rounded-2xl border border-gray-800/80 p-12 text-center h-[600px] flex flex-col justify-center items-center">
                <TerminalIcon className="w-12 h-12 text-gray-700 mb-4 animate-pulse" />
                <h3 className="text-white font-bold text-lg mb-1">Select an Agent Run</h3>
                <p className="text-gray-400 text-sm max-w-xs">Select any execution run from the left panel to inspect step-by-step console outputs and validation test results.</p>
              </div>
            )}
          </div>
          
        </div>
      )}
    </div>
  );
};
