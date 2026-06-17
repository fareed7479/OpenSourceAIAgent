import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Loader2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Terminal,
  FileCode,
  History,
  FileText,
  ArrowRight,
  Clock,
  GitPullRequest,
  Copy,
  Check,
  ExternalLink,
  AlertTriangle,
  Cpu,
  RefreshCw
} from "lucide-react";
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
  repository_id: string;
  issue_id: string;
  user_id: string;
  branch_name: string;
  provider: string;
  status: string;
  actual_provider?: string;
  fallback_provider?: string;
  fallback_reason?: string;
  created_at: string;
  updated_at: string;
  repository?: {
    id: string;
    name: string;
    owner: string;
    url: string;
  };
  issue?: {
    id: string;
    number: number;
    title: string;
    url: string;
  };
  logs: Array<{
    id: string;
    stage: string;
    message: string;
    data?: any;
    created_at: string;
  }>;
  pull_request?: {
    id: string;
    title: string;
    description?: string;
    url?: string;
    status: string;
    approval_status: string;
    files_changed: string[];
  } | null;
}

const ALL_STAGES = [
  { id: "issue_agent", name: "Issue Analysis" },
  { id: "assignment_agent", name: "Assignment Check" },
  { id: "planning_agent", name: "Strategy Planning" },
  { id: "context_agent", name: "Context Retrieval" },
  { id: "coding_agent", name: "Code Execution" },
  { id: "validation_agent", name: "Build Validation" },
  { id: "self_healing_loop", name: "Self-Healing QA" },
  { id: "review_agent", name: "Peer Review Loop" },
  { id: "pr_agent", name: "PR Draft Stage" },
  { id: "learning_agent", name: "Memory Consolidation" }
];

export const AgentMonitor: React.FC = () => {
  const [searchParams] = useSearchParams();
  const issueIdParam = searchParams.get("issueId");
  const runIdParam = searchParams.get("runId");

  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedRun, setSelectedRun] = useState<AgentRun | null>(null);
  const [monitorData, setMonitorData] = useState<MonitorData | null>(null);
  const [loading, setLoading] = useState(true);
  const [fetchingDetails, setFetchingDetails] = useState(false);

  const [plan, setPlan] = useState<any | null>(null);
  const [diffData, setDiffData] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<"plan" | "logs" | "diff" | "healing" | "failure" | "context-audit">("plan");
  const [feedbackText, setFeedbackText] = useState("");
  const [loadingPlan, setLoadingPlan] = useState(false);
  const [loadingDiff, setLoadingDiff] = useState(false);
  const [copied, setCopied] = useState(false);
  const [contextMetrics, setContextMetrics] = useState<any[]>([]);
  const [loadingContextMetrics, setLoadingContextMetrics] = useState(false);

  const [logFilter, setLogFilter] = useState<string>("all");

  const fetchRuns = async () => {
    try {
      const data = await api.get<AgentRun[]>("/runs");
      setRuns(data);
      if (data.length > 0) {
        if (runIdParam && data.some((r) => r.id === runIdParam)) {
          setSelectedRunId(runIdParam);
        } else if (issueIdParam && data.some((r) => r.issue_id === issueIdParam)) {
          const matchingRun = data.find((r) => r.issue_id === issueIdParam);
          if (matchingRun) setSelectedRunId(matchingRun.id);
        } else if (!selectedRunId) {
          setSelectedRunId(data[0].id);
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
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchDetails = async () => {
    if (!selectedRunId) return;
    setFetchingDetails(true);
    try {
      const [timelineResp, runResp] = await Promise.all([
        api.get<MonitorData>(`/intelligence/run/${selectedRunId}/timeline`),
        api.get<AgentRun>(`/runs/${selectedRunId}`)
      ]);
      setMonitorData(timelineResp);
      setSelectedRun(runResp);

      // Automatically switch to failure tracer if run failed
      if (runResp.status === "failed" && activeTab === "plan") {
        setActiveTab("failure");
      }
    } catch (err) {
      console.error("Failed to load timeline and run details:", err);
    } finally {
      setFetchingDetails(false);
    }
  };

  const fetchPlan = async () => {
    if (!selectedRunId) return;
    setLoadingPlan(true);
    try {
      const data = await api.get<any>(`/runs/${selectedRunId}/plan`);
      setPlan(data);
    } catch (err) {
      console.error("Failed to load plan:", err);
      setPlan(null);
    } finally {
      setLoadingPlan(false);
    }
  };

  const fetchDiff = async () => {
    if (!selectedRunId) return;
    setLoadingDiff(true);
    try {
      const data = await api.get<any>(`/runs/${selectedRunId}/diff`);
      setDiffData(data);
    } catch (err) {
      console.error("Failed to load diff:", err);
      setDiffData(null);
    } finally {
      setLoadingDiff(false);
    }
  };

  const fetchContextMetrics = async () => {
    if (!selectedRunId) return;
    setLoadingContextMetrics(true);
    try {
      const data = await api.get<any[]>(`/runs/${selectedRunId}/context-metrics`);
      setContextMetrics(data);
    } catch (err) {
      console.error("Failed to load context metrics:", err);
      setContextMetrics([]);
    } finally {
      setLoadingContextMetrics(false);
    }
  };

  useEffect(() => {
    fetchDetails();
    fetchPlan();
    fetchDiff();
    fetchContextMetrics();

    const interval = setInterval(() => {
      fetchDetails();
      fetchPlan();
      fetchDiff();
      fetchContextMetrics();
    }, 3000);

    return () => clearInterval(interval);
  }, [selectedRunId]);

  const handleApprovePlan = async () => {
    if (!selectedRunId) return;
    try {
      await api.post(`/runs/${selectedRunId}/approve-plan`);
      fetchDetails();
      fetchPlan();
    } catch (err) {
      console.error("Failed to approve plan:", err);
      alert("Failed to approve plan.");
    }
  };

  const handleRejectPlan = async () => {
    if (!selectedRunId) return;
    try {
      await api.post(`/runs/${selectedRunId}/reject-plan`, { feedback: feedbackText });
      setFeedbackText("");
      fetchDetails();
      fetchPlan();
    } catch (err) {
      console.error("Failed to reject plan:", err);
      alert("Failed to reject plan.");
    }
  };

  const handleRegeneratePlan = async () => {
    if (!selectedRunId) return;
    try {
      await api.post(`/runs/${selectedRunId}/regenerate-plan`);
      fetchDetails();
      fetchPlan();
    } catch (err) {
      console.error("Failed to regenerate plan:", err);
      alert("Failed to regenerate plan.");
    }
  };

  const handleCopyBranch = () => {
    if (selectedRun?.branch_name) {
      navigator.clipboard.writeText(selectedRun.branch_name);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const getStageStatus = (stageId: string) => {
    if (!monitorData?.timeline) return "pending";
    const task = monitorData.timeline.find((t) => t.assignee === stageId);
    if (task) {
      return task.status; // "completed", "running", "failed", etc.
    }
    return "pending";
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed": return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "failed": return "bg-red-500/10 text-red-400 border-red-500/20";
      case "pending": return "bg-gray-800 text-gray-400 border-gray-700";
      case "awaiting_plan_approval": return "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse";
      default: return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20 animate-pulse";
    }
  };

  // Find the currently active running stage or failed stage to highlight in UI
  const runningTask = monitorData?.timeline.find((t) => t.status === "running");
  const failedTask = monitorData?.timeline.find((t) => t.status === "failed");
  const activeAgentName = runningTask
    ? runningTask.task_name
    : selectedRun?.status === "awaiting_plan_approval"
    ? "Planning Agent (Paused Awaiting Approval)"
    : selectedRun?.status === "completed"
    ? "Completed Execution"
    : selectedRun?.status === "failed"
    ? "Failed Execution"
    : "Initializing Workspace";

  return (
    <div className="space-y-8 animate-fade-in max-w-none">
      {/* Header Panel */}
      <div className="flex flex-col xl:flex-row justify-between items-start xl:items-center gap-6 bg-gray-950/20 border border-gray-900 p-6 rounded-2xl">
        <div className="space-y-1">
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
            <Cpu className="w-8 h-8 text-indigo-400 animate-pulse" />
            Agent Execution Monitor
          </h1>
          <p className="text-gray-400 text-sm">
            Centralized tracing cockpit for auditing active coding iterations, logs, patch diffs, and health status.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-4 w-full xl:w-auto">
          <div className="flex-1 sm:flex-initial w-64 space-y-1">
            <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Active Execution Run</label>
            <select
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm font-semibold hover:border-gray-700 transition"
            >
              <option value="" disabled>Select Execution Run</option>
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.branch_name.substring(0, 30)}... ({r.status})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={fetchDetails}
            disabled={fetchingDetails}
            className="flex items-center justify-center gap-2 text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 hover:bg-indigo-950/40 py-2.5 px-4 rounded-xl transition self-end h-[42px]"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${fetchingDetails ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {loading && runs.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60 flex items-center justify-center min-h-[400px]">
          <div className="flex flex-col items-center gap-3">
            <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
            <span className="text-sm text-gray-400">Loading active agent runs database...</span>
          </div>
        </div>
      ) : !selectedRunId ? (
        <div className="glass-panel p-16 text-center rounded-2xl border border-gray-800/60">
          <Cpu className="w-14 h-14 text-gray-700 mx-auto mb-4 animate-pulse" />
          <h3 className="text-white font-bold text-lg mb-1">No execution runs recorded</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">
            Triggers are scheduled automatically once issue assignment requests are successfully approved.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* LEFT COLUMN: Stage Timeline Tracker */}
          <div className="lg:col-span-1 space-y-6">
            
            {/* Status Panel Card - Execution cockpit details */}
            {selectedRun && (
              <div className="glass-panel p-6 rounded-2xl border border-gray-850 space-y-5">
                <h3 className="text-xs uppercase font-extrabold text-gray-500 tracking-wider pb-2 border-b border-gray-900">
                  Execution Cockpit Details
                </h3>
                
                <div className="space-y-4 text-xs">
                  <div>
                    <span className="text-[10px] text-gray-500 font-semibold block uppercase">Execution Status</span>
                    <span className={`inline-block text-xs font-bold px-2.5 py-1 rounded-md border uppercase mt-1 ${getStatusColor(selectedRun.status)}`}>
                      {selectedRun.status.replace(/_/g, " ")}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] text-gray-500 font-semibold block uppercase">Current Agent Node</span>
                    <span className="text-sm font-bold text-white block mt-0.5 flex items-center gap-1.5">
                      <Loader2 className="w-3.5 h-3.5 text-indigo-400 animate-spin" />
                      {activeAgentName}
                    </span>
                  </div>

                  <div>
                    <span className="text-[10px] text-gray-500 font-semibold block uppercase">Target Workspace / Repo</span>
                    <span className="text-white font-semibold block mt-0.5 truncate max-w-full">
                      {selectedRun.repository ? `${selectedRun.repository.owner}/${selectedRun.repository.name}` : selectedRun.repository_id}
                    </span>
                    {selectedRun.repository?.url && (
                      <a 
                        href={selectedRun.repository.url} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="text-[10px] text-indigo-400 hover:underline flex items-center gap-0.5 mt-0.5"
                      >
                        Visit Repository <ExternalLink className="w-2 h-2" />
                      </a>
                    )}
                  </div>

                  <div>
                    <span className="text-[10px] text-gray-500 font-semibold block uppercase">Target Issue</span>
                    <span className="text-white font-semibold block mt-0.5 max-w-full truncate">
                      {selectedRun.issue ? `#${selectedRun.issue.number} ${selectedRun.issue.title}` : `Issue ${selectedRun.issue_id}`}
                    </span>
                    {selectedRun.issue?.url && (
                      <a 
                        href={selectedRun.issue.url} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="text-[10px] text-indigo-400 hover:underline flex items-center gap-0.5 mt-0.5"
                      >
                        View Issue <ExternalLink className="w-2 h-2" />
                      </a>
                    )}
                  </div>

                  <div>
                    <span className="text-[10px] text-gray-500 font-semibold block uppercase font-mono">Git Target Branch</span>
                    <div className="flex items-center gap-1.5 mt-1">
                      <span className="text-xs font-mono bg-black/40 border border-gray-900 px-2 py-1 rounded text-indigo-300 truncate max-w-[200px]">
                        {selectedRun.branch_name}
                      </span>
                      <button
                        onClick={handleCopyBranch}
                        className="text-gray-400 hover:text-white p-1 hover:bg-gray-850 rounded transition"
                        title="Copy branch name"
                      >
                        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>

                  {/* Provider Transparency Details */}
                  <div className="border-t border-gray-900 pt-4 space-y-2.5">
                    <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block">
                      Provider Configuration
                    </span>
                    <div className="grid grid-cols-2 gap-3 bg-black/10 p-2.5 rounded-lg border border-gray-900/60">
                      <div>
                        <span className="text-[9px] text-gray-500 font-semibold block">Requested</span>
                        <span className="font-bold text-gray-300">{selectedRun.provider}</span>
                      </div>
                      <div>
                        <span className="text-[9px] text-gray-500 font-semibold block">Actual Provider</span>
                        <span className="font-bold text-indigo-400">{selectedRun.actual_provider || "Pending execution"}</span>
                      </div>
                    </div>
                    {selectedRun.fallback_provider && (
                      <div className="bg-amber-950/20 border border-amber-500/10 text-[10px] p-2.5 rounded-lg text-amber-400 space-y-1">
                        <div className="font-bold flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3 text-amber-500" />
                          Provider Fallback Engaged
                        </div>
                        <p className="text-gray-400 leading-normal">
                          Fallback: <span className="font-semibold text-gray-300">{selectedRun.fallback_provider}</span>
                        </p>
                        {selectedRun.fallback_reason && (
                          <p className="text-[9px] text-gray-500 italic leading-snug">
                            Reason: {selectedRun.fallback_reason}
                          </p>
                        )}
                      </div>
                    )}
                  </div>

                  {selectedRun.pull_request && (
                    <div className="border-t border-gray-900 pt-4 space-y-1.5">
                      <span className="text-[10px] text-pink-400 font-bold uppercase tracking-wider flex items-center gap-1">
                        <GitPullRequest className="w-3.5 h-3.5" />
                        Pull Request Generated
                      </span>
                      <h4 className="text-xs font-bold text-white truncate">{selectedRun.pull_request.title}</h4>
                      <div className="flex justify-between items-center text-[10px]">
                        <span className="text-gray-400">Review status: {selectedRun.pull_request.status}</span>
                        {selectedRun.pull_request.url && (
                          <a
                            href={selectedRun.pull_request.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-indigo-400 hover:underline flex items-center gap-0.5"
                          >
                            GitHub PR
                            <ExternalLink className="w-2.5 h-2.5" />
                          </a>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Visual Workflow Timeline Viewer */}
            <div className="glass-panel p-6 rounded-2xl border border-gray-800/80 space-y-5">
              <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-900 pb-3">
                <Clock className="w-4.5 h-4.5 text-indigo-400" />
                Workflow Stage Timeline
              </h3>
              
              <div className="relative border-l border-gray-800/80 ml-3 pl-6 space-y-6">
                {ALL_STAGES.map((stage) => {
                  const status = getStageStatus(stage.id);
                  const isCurrent = runningTask?.assignee === stage.id || 
                    (stage.id === "planning_agent" && selectedRun?.status === "awaiting_plan_approval");
                  
                  return (
                    <div key={stage.id} className="relative space-y-1">
                      {/* Stepper Bullet Indicator */}
                      <span className={`absolute -left-[30px] top-0.5 p-1 rounded-full border transition-all ${
                        status === "completed" 
                          ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-lg shadow-emerald-500/5" 
                          : status === "running" || isCurrent
                          ? "bg-amber-500/10 border-amber-500/30 text-amber-400 animate-pulse shadow-lg shadow-amber-500/5"
                          : status === "failed"
                          ? "bg-red-500/10 border-red-500/30 text-red-400 shadow-lg shadow-red-500/5"
                          : "bg-gray-950 border-gray-850 text-gray-600"
                      }`}>
                        {status === "completed" ? (
                          <CheckCircle2 className="w-2.5 h-2.5" />
                        ) : status === "failed" ? (
                          <XCircle className="w-2.5 h-2.5" />
                        ) : status === "running" || isCurrent ? (
                          <Loader2 className="w-2.5 h-2.5 animate-spin" />
                        ) : (
                          <div className="w-2.5 h-2.5 rounded-full bg-gray-800" />
                        )}
                      </span>

                      <div className="flex items-center justify-between gap-2">
                        <h4 className={`font-bold text-xs ${isCurrent ? "text-indigo-400" : "text-white"}`}>
                          {stage.name}
                        </h4>
                        <span className={`text-[8px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded border select-none ${
                          status === "completed"
                            ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                            : status === "failed"
                            ? "bg-red-500/10 text-red-400 border-red-500/20"
                            : status === "running" || isCurrent
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse"
                            : "bg-gray-950 text-gray-500 border-gray-900"
                        }`}>
                          {status === "running" || isCurrent ? "running" : status}
                        </span>
                      </div>

                      {/* Display task details if it ran */}
                      {(() => {
                        const task = monitorData?.timeline.find((t) => t.assignee === stage.id);
                        if (task) {
                          return (
                            <p className="text-[10px] text-gray-400 leading-normal">
                              {task.description}
                            </p>
                          );
                        }
                        return null;
                      })()}
                    </div>
                  );
                })}
              </div>
            </div>

          </div>

          {/* RIGHT COLUMN: Action Console & Tab Viewer */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Tab Navigation */}
            <div className="flex border-b border-gray-900 bg-gray-950/20 p-1 rounded-xl gap-1">
              <button
                onClick={() => setActiveTab("plan")}
                className={`flex items-center gap-1.5 text-xs font-semibold py-2.5 px-4 rounded-lg transition-all ${
                  activeTab === "plan" ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/10" : "text-gray-400 hover:text-white"
                }`}
              >
                <FileText className="w-3.5 h-3.5" />
                Plan & Approval
              </button>
              
              <button
                onClick={() => setActiveTab("logs")}
                className={`flex items-center gap-1.5 text-xs font-semibold py-2.5 px-4 rounded-lg transition-all ${
                  activeTab === "logs" ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/10" : "text-gray-400 hover:text-white"
                }`}
              >
                <Terminal className="w-3.5 h-3.5" />
                Live Console
              </button>

              <button
                onClick={() => setActiveTab("diff")}
                className={`flex items-center gap-1.5 text-xs font-semibold py-2.5 px-4 rounded-lg transition-all ${
                  activeTab === "diff" ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/10" : "text-gray-400 hover:text-white"
                }`}
              >
                <FileCode className="w-3.5 h-3.5" />
                Code Diffs
              </button>

              <button
                onClick={() => setActiveTab("healing")}
                className={`flex items-center gap-1.5 text-xs font-semibold py-2.5 px-4 rounded-lg transition-all ${
                  activeTab === "healing" ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/10" : "text-gray-400 hover:text-white"
                }`}
              >
                <History className="w-3.5 h-3.5" />
                Healing & Review
              </button>

              <button
                onClick={() => setActiveTab("failure")}
                className={`flex items-center gap-1.5 text-xs font-semibold py-2.5 px-4 rounded-lg transition-all ${
                  activeTab === "failure" 
                    ? "bg-red-600 text-white shadow shadow-red-650/10" 
                    : selectedRun?.status === "failed"
                    ? "text-red-400 bg-red-950/20 hover:text-red-300 border border-red-500/10"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                Failure Tracer
                {selectedRun?.status === "failed" && (
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-ping" />
                )}
              </button>

              <button
                onClick={() => setActiveTab("context-audit")}
                className={`flex items-center gap-1.5 text-xs font-semibold py-2.5 px-4 rounded-lg transition-all ${
                  activeTab === "context-audit" ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/10" : "text-gray-400 hover:text-white"
                }`}
              >
                <FileCode className="w-3.5 h-3.5" />
                Context Quality
              </button>
            </div>

            {/* TAB CONTENT PANELS */}
            <div className="glass-panel p-6 rounded-2xl border border-gray-800/80 min-h-[500px] bg-black/10 flex flex-col justify-between">
              
              {/* TAB 1: Plan & Approval */}
              {activeTab === "plan" && (
                <div className="flex-1 flex flex-col justify-between h-full">
                  <div className="space-y-6">
                    <div className="border-b border-gray-900 pb-4">
                      <h3 className="font-bold text-white text-base">Execution Strategy Plan</h3>
                      <p className="text-xs text-gray-400">
                        Generated strategy outlining proposed changes and roadmap tasks to repair the issue.
                      </p>
                    </div>

                    {loadingPlan ? (
                      <div className="flex justify-center items-center py-20 flex-1">
                        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                      </div>
                    ) : plan ? (
                      <div className="space-y-5">
                        <div className="bg-indigo-950/10 border border-indigo-500/10 rounded-xl p-5 space-y-2">
                          <h4 className="text-white font-bold text-sm">{plan.title}</h4>
                          <p className="text-gray-400 text-xs leading-relaxed">{plan.description}</p>
                        </div>

                        <div className="space-y-3">
                          <h5 className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Roadmap Steps Checklist</h5>
                          <div className="border border-gray-900 rounded-xl overflow-hidden divide-y divide-gray-900 bg-black/20 text-xs">
                            {plan.steps && plan.steps.map((step: any) => (
                              <div key={step.step} className="flex justify-between items-start p-4 gap-4 hover:bg-gray-900/10 transition">
                                <div className="flex gap-3 items-start">
                                  <span className="font-mono font-bold text-indigo-400 bg-indigo-950/30 px-2 py-0.5 rounded border border-indigo-500/10 shrink-0">
                                    {step.step}
                                  </span>
                                  <span className="text-gray-300 leading-normal">{step.description}</span>
                                </div>
                                <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded border select-none shrink-0 ${
                                  step.status === "completed"
                                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                    : "bg-gray-900/80 border-gray-800 text-amber-500/80"
                                }`}>
                                  {step.status}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {selectedRun?.status === "awaiting_plan_approval" && (
                          <div className="space-y-2 pt-2">
                            <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider block">
                              Rejection / Revision Feedback
                            </label>
                            <textarea
                              value={feedbackText}
                              onChange={(e) => setFeedbackText(e.target.value)}
                              placeholder="Describe any instructions or changes you would like to make before rejecting..."
                              className="w-full bg-black/40 border border-gray-900 hover:border-gray-800 focus:border-indigo-500/40 text-gray-300 rounded-xl p-4 outline-none text-xs font-mono h-24 transition resize-none"
                            />
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-20 text-gray-500 text-xs italic">
                        No strategy plan exists for this run. Wait for the planning stage to complete.
                      </div>
                    )}
                  </div>

                  {selectedRun?.status === "awaiting_plan_approval" && plan && (
                    <div className="border-t border-gray-900 pt-5 mt-6 flex flex-col sm:flex-row justify-end items-stretch sm:items-center gap-3 bg-black/10 p-4 rounded-xl">
                      <button
                        onClick={handleRegeneratePlan}
                        className="text-xs font-semibold text-gray-300 bg-gray-950 border border-gray-850 hover:bg-gray-850 py-2.5 px-4 rounded-xl transition"
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
                        className="text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 py-2.5 px-5 rounded-xl transition shadow-lg shadow-emerald-600/10 flex items-center justify-center gap-1.5"
                      >
                        Approve Plan & Start Coding
                        <ArrowRight className="w-3.5 h-3.5 animate-pulse" />
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: Live Console Logs */}
              {activeTab === "logs" && (
                <div className="flex-1 flex flex-col h-full space-y-4">
                  <div className="flex justify-between items-center border-b border-gray-900 pb-3 flex-wrap gap-2">
                    <div>
                      <h3 className="font-bold text-white text-base">Execution Console Logs</h3>
                      <p className="text-xs text-gray-400">Detailed tracing output from agents executing stage tasks.</p>
                    </div>

                    <div className="flex items-center gap-2 text-[10px]">
                      <span className="text-gray-500 font-bold uppercase">Filter:</span>
                      <select
                        value={logFilter}
                        onChange={(e) => setLogFilter(e.target.value)}
                        className="bg-gray-950 border border-gray-800 text-gray-300 rounded-lg py-1 px-2.5 outline-none font-semibold"
                      >
                        <option value="all">All Stages</option>
                        <option value="workspace">Workspace</option>
                        <option value="context">Context</option>
                        <option value="coding">Coding</option>
                        <option value="validation">Validation</option>
                        <option value="review">Review</option>
                        <option value="pr">Pull Request</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex-1 bg-[#02050e]/95 border border-gray-900 p-5 font-mono text-[11px] overflow-y-auto max-h-[500px] min-h-[350px] rounded-xl space-y-4 text-gray-300 scrollbar-thin">
                    <div className="text-gray-500 select-none border-b border-gray-900 pb-2 mb-2">
                      [System] Subscribing to live execution stream pipeline...
                    </div>

                    {!selectedRun?.logs || selectedRun.logs.length === 0 ? (
                      <div className="text-gray-500 italic py-6">No logs written. Logs stream will populate as tasks execute.</div>
                    ) : (
                      selectedRun.logs
                        .filter((log) => logFilter === "all" || log.stage === logFilter)
                        .map((log) => (
                          <div key={log.id} className="space-y-1.5 animate-fade-in">
                            <div className="flex items-start gap-2.5">
                              <span className="text-gray-600 select-none text-[10px]">
                                {new Date(log.created_at).toLocaleTimeString()}
                              </span>
                              <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider select-none shrink-0 ${getStageBadgeColor(log.stage)}`}>
                                {log.stage}
                              </span>
                              <span className="text-gray-200 leading-normal">{log.message}</span>
                            </div>

                            {log.data && (
                              <div className="ml-20 p-3 bg-gray-950/60 border border-gray-900 rounded-lg max-w-full overflow-x-auto text-[10px] text-gray-400 max-h-48 scrollbar-thin">
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
              )}

              {/* TAB 3: Code Diffs */}
              {activeTab === "diff" && (
                <div className="flex-1 flex flex-col h-full space-y-5">
                  <div className="border-b border-gray-900 pb-3">
                    <h3 className="font-bold text-white text-base">Generated Code Diffs</h3>
                    <p className="text-xs text-gray-400">Review modifications generated by the coding execution agent.</p>
                  </div>

                  {loadingDiff ? (
                    <div className="flex justify-center items-center py-20 flex-1">
                      <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                    </div>
                  ) : diffData && (diffData.diff || diffData.files_modified?.length > 0) ? (
                    <div className="space-y-5 flex-1 flex flex-col">
                      {/* Metric widgets */}
                      <div className="grid grid-cols-3 gap-4">
                        <div className="p-4 bg-gray-950/60 border border-gray-850 rounded-xl space-y-1">
                          <span className="text-[10px] text-gray-500 uppercase font-bold block">Files Modified</span>
                          <span className="text-xl font-extrabold text-indigo-400">
                            {diffData.files_modified?.length || 0}
                          </span>
                        </div>
                        <div className="p-4 bg-gray-950/60 border border-gray-850 rounded-xl space-y-1">
                          <span className="text-[10px] text-gray-500 uppercase font-bold block">Lines Added</span>
                          <span className="text-xl font-extrabold text-emerald-400">
                            +{diffData.lines_added || 0}
                          </span>
                        </div>
                        <div className="p-4 bg-gray-950/60 border border-gray-850 rounded-xl space-y-1">
                          <span className="text-[10px] text-gray-500 uppercase font-bold block">Lines Removed</span>
                          <span className="text-xl font-extrabold text-red-400">
                            -{diffData.lines_removed || 0}
                          </span>
                        </div>
                      </div>

                      {/* File names list */}
                      {diffData.files_modified && diffData.files_modified.length > 0 && (
                        <div className="space-y-1 text-xs">
                          <span className="text-gray-500 font-bold uppercase text-[10px] tracking-wider block">Affected Files</span>
                          <div className="flex flex-wrap gap-2 pt-1">
                            {diffData.files_modified.map((file: string, idx: number) => (
                              <span key={idx} className="bg-indigo-950/20 border border-indigo-500/10 text-indigo-300 font-mono px-2 py-1 rounded">
                                {file}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Patch Preview */}
                      {diffData.diff && (
                        <div className="flex-1 space-y-1.5">
                          <span className="text-gray-500 font-bold uppercase text-[10px] tracking-wider block">Patch Preview</span>
                          <div className="bg-[#02050e]/95 border border-gray-900 rounded-xl p-4 font-mono text-[10px] leading-relaxed max-h-[350px] overflow-y-auto text-gray-300 scrollbar-thin">
                            {diffData.diff.split("\n").map((line: string, idx: number) => {
                              let style = "text-gray-400";
                              if (line.startsWith("+") && !line.startsWith("+++")) {
                                style = "text-emerald-400 bg-emerald-950/10 px-1 border-l-2 border-emerald-500";
                              } else if (line.startsWith("-") && !line.startsWith("---")) {
                                style = "text-red-400 bg-red-950/10 px-1 border-l-2 border-red-500";
                              } else if (line.startsWith("@@")) {
                                style = "text-cyan-400 bg-cyan-950/10 font-bold";
                              } else if (line.startsWith("diff --git")) {
                                style = "text-indigo-400 font-bold border-b border-gray-900 pb-1 mt-2";
                              }
                              return (
                                <div key={idx} className={`whitespace-pre ${style}`}>
                                  {line || " "}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-20 text-gray-500 text-xs italic flex-1 flex items-center justify-center">
                      No code changes generated yet. The agent writes modifications during the Coding Stage.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 4: Healing & Review */}
              {activeTab === "healing" && (
                <div className="flex-1 flex flex-col h-full space-y-6">
                  <div className="border-b border-gray-900 pb-3">
                    <h3 className="font-bold text-white text-base">Self-Healing & Quality Audits</h3>
                    <p className="text-xs text-gray-400">View compilation QA repair attempts and review scores.</p>
                  </div>

                  {/* Quality Scores */}
                  {monitorData?.quality_metrics ? (
                    <div className="bg-gray-950/30 border border-gray-900 p-5 rounded-xl space-y-4">
                      <h4 className="text-xs uppercase font-extrabold text-gray-400 tracking-wider">AI Quality Review Scores</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {[
                          { label: "Security Profile", val: monitorData.quality_metrics.security, color: "text-emerald-400 bg-emerald-950/20" },
                          { label: "Performance", val: monitorData.quality_metrics.performance, color: "text-blue-400 bg-blue-950/20" },
                          { label: "Code Style", val: monitorData.quality_metrics.style, color: "text-purple-400 bg-purple-950/20" },
                          { label: "Overall Quality", val: monitorData.quality_metrics.overall, color: "text-indigo-400 bg-indigo-950/20" }
                        ].map((m, idx) => (
                          <div key={idx} className="p-3 bg-[#030712]/50 border border-gray-850 rounded-lg text-center">
                            <span className="text-[9px] text-gray-500 uppercase font-bold block mb-1">{m.label}</span>
                            <span className={`inline-block text-base font-extrabold px-2.5 py-0.5 rounded ${m.color}`}>
                              {m.val}/100
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-950/20 border border-gray-900 p-4 rounded-xl text-center text-xs text-gray-500 italic">
                      Quality reviews will run once code modifications pass validation builds.
                    </div>
                  )}

                  {/* Self-Healing Attempts */}
                  <div className="space-y-3">
                    <h4 className="text-xs uppercase font-extrabold text-gray-400 tracking-wider">
                      Self-Healing Cycles (Autonomous QA Repairs)
                    </h4>

                    {!monitorData?.healing_attempts || monitorData.healing_attempts.length === 0 ? (
                      <div className="p-8 text-center text-xs text-gray-500 italic bg-gray-950/20 rounded-xl border border-gray-900">
                        No repair loops executed. Validations passed clean on attempt #1.
                      </div>
                    ) : (
                      <div className="space-y-4 max-h-[300px] overflow-y-auto pr-1 scrollbar-thin">
                        {monitorData.healing_attempts.map((attempt) => (
                          <div key={attempt.attempt_number} className="border border-gray-850 rounded-xl overflow-hidden text-xs bg-[#02050e]/60">
                            <div className="bg-gray-950/60 px-4 py-2.5 border-b border-gray-850 flex justify-between items-center">
                              <span className="font-bold text-white">Repair Attempt #{attempt.attempt_number}</span>
                              <span className={`text-[9px] font-bold px-2 py-0.5 rounded border ${
                                attempt.status === "succeeded"
                                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                  : "bg-red-500/10 text-red-400 border-red-500/20"
                              }`}>
                                {attempt.status}
                              </span>
                            </div>

                            <div className="p-4 space-y-3">
                              <div className="space-y-1">
                                <span className="text-[9px] text-gray-500 font-bold uppercase tracking-wider block">Traceback Log Summary</span>
                                <pre className="p-3 bg-black/40 border border-gray-900 text-[10px] text-red-300 font-mono overflow-x-auto max-h-24 rounded-lg whitespace-pre-wrap leading-relaxed">
                                  {attempt.error_message}
                                </pre>
                              </div>

                              <div className="text-xs text-gray-300">
                                <span className="font-semibold text-gray-400 uppercase text-[9px] mr-1">Action:</span>
                                {attempt.planned_fix}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 6: Context Retrieval Quality Audit */}
              {activeTab === "context-audit" && (
                <div className="flex-1 flex flex-col h-full space-y-5">
                  <div className="border-b border-gray-900 pb-3">
                    <h3 className="font-bold text-white text-base">Semantic Context Quality Audit</h3>
                    <p className="text-xs text-gray-400">
                      Audit retrieved workspace files, similarity scores, and reasoning metadata.
                    </p>
                  </div>

                  {loadingContextMetrics ? (
                    <div className="flex justify-center items-center py-20 flex-1">
                      <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                    </div>
                  ) : contextMetrics && contextMetrics.length > 0 ? (
                    <div className="space-y-4 flex-1">
                      <div className="border border-gray-900 rounded-xl overflow-hidden bg-black/20 text-xs">
                        <table className="w-full text-left border-collapse">
                          <thead>
                            <tr className="bg-gray-950 border-b border-gray-900 text-[10px] text-gray-400 uppercase font-extrabold tracking-wider">
                              <th className="py-3 px-4">Retrieved File Path</th>
                              <th className="py-3 px-4 text-center">Similarity Score</th>
                              <th className="py-3 px-4">Selection Reasoning & Intent Details</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-900">
                            {contextMetrics.map((metric, idx) => (
                              <tr key={idx} className="hover:bg-gray-900/10 transition">
                                <td className="py-3 px-4 font-mono text-gray-200">{metric.filepath}</td>
                                <td className="py-3 px-4 text-center">
                                  <span className={`inline-block font-extrabold px-2 py-0.5 rounded ${
                                    metric.score >= 0.75 
                                      ? "text-emerald-400 bg-emerald-950/20" 
                                      : metric.score >= 0.5 
                                      ? "text-blue-400 bg-blue-950/20" 
                                      : "text-gray-400 bg-gray-900"
                                  }`}>
                                    {(metric.score * 100).toFixed(2)}%
                                  </span>
                                </td>
                                <td className="py-3 px-4 text-gray-300 leading-normal">{metric.reason}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="text-[10px] text-gray-500 leading-relaxed italic">
                        * Note: Only the top 4 highly relevant files are injected into the agent context window to minimize model context bloat and ensure optimal code generation.
                      </p>
                    </div>
                  ) : (
                    <div className="text-center py-20 text-gray-500 text-xs italic flex-1 flex items-center justify-center">
                      No semantic search audit data is available. This panel populates during the Context Retrieval Stage.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 5: Failure Tracer */}
              {activeTab === "failure" && (
                <div className="flex-1 flex flex-col h-full space-y-5">
                  <div className="border-b border-gray-950 pb-3">
                    <h3 className="font-bold text-white text-base">Failure Details Tracer</h3>
                    <p className="text-xs text-gray-400">Detailed traceback audits for crashed nodes.</p>
                  </div>

                  {failedTask ? (
                    <div className="space-y-5 flex-1 flex flex-col">
                      <div className="bg-red-950/20 border border-red-500/10 rounded-xl p-5 flex items-start gap-4">
                        <AlertCircle className="w-8 h-8 text-red-400 shrink-0 mt-0.5" />
                        <div className="space-y-1 text-xs">
                          <h4 className="text-red-400 font-extrabold text-sm">
                            Agent Crash Detected: {failedTask.task_name}
                          </h4>
                          <div className="text-gray-400 space-y-1 mt-2">
                            <div>
                              <span className="font-semibold text-gray-300">Failed Agent:</span> {failedTask.assignee}
                            </div>
                            <div>
                              <span className="font-semibold text-gray-300">Timestamp:</span>{" "}
                              {new Date(failedTask.updated_at).toLocaleString()}
                            </div>
                            <div className="text-red-300 font-medium mt-1">
                              <span className="font-semibold text-gray-300">Error Payload:</span>{" "}
                              {failedTask.result?.error || "Unknown execution exception."}
                            </div>
                          </div>
                        </div>
                      </div>

                      {failedTask.result?.traceback && (
                        <div className="flex-1 flex flex-col space-y-1.5">
                          <span className="text-gray-500 font-bold uppercase text-[10px] tracking-wider">
                            Engine Stack Trace
                          </span>
                          <pre className="flex-1 p-4 bg-[#02050e]/95 border border-gray-900 rounded-xl text-[10px] text-red-300 font-mono overflow-x-auto overflow-y-auto max-h-[300px] scrollbar-thin whitespace-pre leading-relaxed select-text">
                            {failedTask.result.traceback}
                          </pre>
                        </div>
                      )}
                    </div>
                  ) : selectedRun?.status === "failed" ? (
                    <div className="bg-red-950/20 border border-red-500/10 rounded-xl p-5 flex items-start gap-4 flex-1">
                      <AlertCircle className="w-8 h-8 text-red-400 shrink-0 mt-0.5" />
                      <div className="space-y-1 text-xs">
                        <h4 className="text-red-400 font-extrabold text-sm">Execution Run Aborted / Cancelled</h4>
                        <p className="text-gray-400 leading-relaxed mt-2">
                          The orchestration workflow was marked as failed, possibly due to planning rejection or external cancellation. No traceback logs are registered in task history.
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-20 text-gray-500 text-xs italic flex-1 flex flex-col justify-center items-center gap-2">
                      <CheckCircle2 className="w-10 h-10 text-emerald-500" />
                      No failures or crashes registered for this execution.
                    </div>
                  )}
                </div>
              )}

            </div>

          </div>

        </div>
      )}
    </div>
  );
};
