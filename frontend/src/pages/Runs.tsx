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

  const [plan, setPlan] = useState<any | null>(null);
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");

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

  const fetchPlan = async (runId: string) => {
    setLoadingPlan(true);
    try {
      const data = await api.get<any>(`/runs/${runId}/plan`);
      setPlan(data);
    } catch (err) {
      console.error("Failed to load plan:", err);
      setPlan(null);
    } finally {
      setLoadingPlan(false);
    }
  };

  useEffect(() => {
    fetchRuns();
    // Poll runs and logs state every 3 seconds to show real-time progress
    const interval = setInterval(fetchRuns, 3000);
    return () => clearInterval(interval);
  }, [selectedRun?.id]);

  useEffect(() => {
    if (selectedRun?.status === "awaiting_plan_approval") {
      fetchPlan(selectedRun.id);
    } else {
      setPlan(null);
    }
  }, [selectedRun?.id, selectedRun?.status]);

  const handleSelectRun = (run: AgentRun) => {
    setSelectedRun(run);
  };

  const forceSync = async () => {
    setRefreshing(true);
    await fetchRuns();
    setRefreshing(false);
  };

  const handleApprovePlan = async () => {
    if (!selectedRun) return;
    try {
      await api.post(`/runs/${selectedRun.id}/approve-plan`);
      await fetchRuns();
    } catch (err) {
      console.error("Failed to approve plan:", err);
      alert("Failed to approve plan.");
    }
  };

  const handleRejectPlan = async () => {
    if (!selectedRun) return;
    try {
      await api.post(`/runs/${selectedRun.id}/reject-plan`, { feedback: feedbackText });
      setFeedbackText("");
      await fetchRuns();
    } catch (err) {
      console.error("Failed to reject plan:", err);
      alert("Failed to reject plan.");
    }
  };

  const handleRegeneratePlan = async () => {
    if (!selectedRun) return;
    try {
      await api.post(`/runs/${selectedRun.id}/regenerate-plan`);
      await fetchRuns();
    } catch (err) {
      console.error("Failed to regenerate plan:", err);
      alert("Failed to regenerate plan.");
    }
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
      case "awaiting_plan_approval":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse";
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
              selectedRun.status === "awaiting_plan_approval" ? (
                <div className="glass-panel rounded-2xl border border-amber-500/20 overflow-hidden flex flex-col h-[600px] bg-gray-950/20">
                  {/* Plan Header */}
                  <div className="bg-[#030712]/80 border-b border-gray-800/80 px-6 py-4 flex justify-between items-center">
                    <div>
                      <h3 className="font-bold text-white text-sm flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                        Awaiting Implementation Plan Approval
                      </h3>
                      <span className="text-[10px] text-gray-400 block mt-0.5">Run ID: {selectedRun.id}</span>
                    </div>
                  </div>

                  {/* Plan Body */}
                  <div className="flex-1 p-6 overflow-y-auto space-y-6">
                    {loadingPlan ? (
                      <div className="flex justify-center items-center h-full">
                        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                      </div>
                    ) : plan ? (
                      <div className="space-y-6">
                        <div className="bg-indigo-950/10 border border-indigo-500/10 rounded-xl p-5 space-y-2">
                          <h4 className="text-white font-bold text-base">{plan.title}</h4>
                          <p className="text-gray-400 text-xs leading-relaxed">{plan.description}</p>
                        </div>

                        <div className="space-y-3">
                          <h5 className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Proposed Roadmap Steps</h5>
                          <div className="border border-gray-900 rounded-xl overflow-hidden divide-y divide-gray-900/60 bg-black/20">
                            {plan.steps && plan.steps.map((step: any) => (
                              <div key={step.step} className="flex justify-between items-start p-4 text-xs gap-4 hover:bg-gray-900/20 transition-colors">
                                <div className="flex gap-3 items-start">
                                  <span className="font-bold text-indigo-400 font-mono bg-indigo-950/30 px-2 py-0.5 rounded border border-indigo-500/10">
                                    {step.step}
                                  </span>
                                  <span className="text-gray-300 leading-relaxed">{step.description}</span>
                                </div>
                                <span className="text-[9px] uppercase font-bold px-2 py-0.5 rounded bg-gray-900/80 border border-gray-800 text-amber-500/80 select-none shrink-0">
                                  {step.status}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Plan Feedback input */}
                        <div className="space-y-2">
                          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider block">Rejection Feedback / Adjustments</label>
                          <textarea
                            value={feedbackText}
                            onChange={(e) => setFeedbackText(e.target.value)}
                            placeholder="Describe any necessary revisions or strategy changes if rejecting this plan..."
                            className="w-full bg-black/40 border border-gray-900 hover:border-gray-800 focus:border-indigo-500/40 text-gray-300 rounded-xl p-4 outline-none text-xs font-mono h-20 transition"
                          />
                        </div>
                      </div>
                    ) : (
                      <div className="text-center text-gray-500 italic text-xs py-10">
                        Failed to load plan details. Try Syncing Logs or regenerating the plan.
                      </div>
                    )}
                  </div>

                  {/* Plan Footer Actions */}
                  <div className="bg-[#030712]/80 border-t border-gray-800/80 px-6 py-4 flex flex-col sm:flex-row justify-end items-stretch sm:items-center gap-3">
                    <button
                      onClick={handleRegeneratePlan}
                      className="text-xs font-semibold text-gray-300 bg-gray-900 border border-gray-850 hover:bg-gray-850 py-2.5 px-4 rounded-xl transition"
                    >
                      Regenerate Plan
                    </button>
                    <button
                      onClick={handleRejectPlan}
                      disabled={!feedbackText.trim()}
                      className="text-xs font-semibold text-red-400 bg-red-950/20 border border-red-500/20 hover:bg-red-950/40 disabled:opacity-40 disabled:hover:bg-red-950/20 py-2.5 px-4 rounded-xl transition"
                    >
                      Reject Plan
                    </button>
                    <button
                      onClick={handleApprovePlan}
                      className="text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 py-2.5 px-5 rounded-xl transition shadow-lg shadow-emerald-600/10"
                    >
                      Approve & Start Coding
                    </button>
                  </div>
                </div>
              ) : (
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
              )
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
