import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { 
  ListTodo, Loader2, CheckCircle, RefreshCw, Clock, ArrowRight, ExternalLink, 
  Folder, Tag, AlertTriangle, ShieldAlert, Calendar, Play
} from "lucide-react";
import { api } from "../api/client";

interface Assignment {
  id: string;
  assignment_id: string;
  user_id: string;
  issue_id: string;
  status: string;
  assignment_status: string;
  request_comment_id?: number;
  comment_url?: string;
  issue_url?: string;
  repository_url?: string;
  created_at: string;
  assigned_at: string;
  updated_at: string;
  issue_number?: number;
  issue_title?: string;
  repository_name?: string;
  repository_owner?: string;
  agent_run_id?: string;
  workflow_status?: string;
  current_stage?: string;
  issue?: {
    id: string;
    number: number;
    title: string;
    url: string;
    difficulty: string;
    labels?: string[];
  };
}

const SkeletonCard: React.FC = () => (
  <div className="glass-panel p-6 rounded-2xl border border-gray-800/60 space-y-4 animate-pulse">
    <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
      <div className="space-y-2 flex-1 w-full">
        <div className="h-3 bg-gray-800/80 rounded w-1/4"></div>
        <div className="h-6 bg-gray-850 rounded w-3/4"></div>
        <div className="h-4 bg-gray-800/60 rounded w-1/2"></div>
      </div>
      <div className="h-8 bg-gray-800 rounded-lg w-28"></div>
    </div>
    <div className="h-px bg-gray-800/40"></div>
    <div className="flex flex-wrap gap-2">
      <div className="h-5 bg-gray-850 rounded w-16"></div>
      <div className="h-5 bg-gray-850 rounded w-20"></div>
    </div>
    <div className="flex justify-between items-center pt-2">
      <div className="h-4 bg-gray-800/55 rounded w-1/3"></div>
      <div className="h-9 bg-gray-800 rounded-xl w-32"></div>
    </div>
  </div>
);

export const Assignments: React.FC = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  const fetchAssignments = async (isPoll: boolean = false) => {
    try {
      const data = await api.get<Assignment[]>("/assignments");
      setAssignments(data);
      setError(null);
    } catch (err: any) {
      console.error("Failed to load assignments:", err);
      // Only set error state if it's the initial page load to prevent disrupting background polls
      if (!isPoll) {
        setError(err.message || "Failed to fetch assignments from API. Please verify connectivity.");
      }
    } finally {
      if (!isPoll) {
        setLoading(false);
      }
    }
  };

  useEffect(() => {
    fetchAssignments();
    // Poll assignment state updates every 5 seconds
    const interval = setInterval(() => fetchAssignments(true), 5000);
    return () => clearInterval(interval);
  }, []);

  const triggerSync = async () => {
    setSyncing(true);
    try {
      await api.post("/assignments/monitor");
      // Wait for background tasks to finish polling and reload
      setTimeout(() => fetchAssignments(true), 2000);
    } catch (err: any) {
      console.error("Sync failed:", err);
      alert(err.message || "Failed to trigger background synchronization.");
    } finally {
      setSyncing(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "N/A";
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch (e) {
      return dateStr;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "assigned":
      case "active":
      case "approved":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "in_progress":
      case "monitoring":
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
      case "comment_posted":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "requested":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      case "completed":
        return "bg-teal-500/10 text-teal-400 border-teal-500/20";
      case "failed":
      case "rejected":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      default:
        return "bg-gray-800 text-gray-400 border-gray-700";
    }
  };

  const getWorkflowStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return "bg-teal-500/10 text-teal-400 border-teal-500/20";
      case "failed":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      case "pending":
        return "bg-amber-500/10 text-amber-400 border-amber-500/20";
      default: // running, validating, reviewing, etc.
        return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Assignments</h1>
          <p className="text-gray-400 text-sm mt-1">Assignments request statuses and polling monitoring.</p>
        </div>
        
        <button
          onClick={triggerSync}
          disabled={syncing || loading || !!error}
          className="flex items-center gap-2 text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 hover:bg-indigo-950/40 py-2.5 px-4 rounded-xl transition disabled:opacity-40"
        >
          {syncing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <RefreshCw className="w-3.5 h-3.5" />
          )}
          Sync Assignment Status
        </button>
      </div>

      {/* Error state */}
      {error ? (
        <div className="glass-panel p-8 text-center rounded-2xl border border-red-500/20 bg-red-950/5 max-w-2xl mx-auto space-y-4">
          <ShieldAlert className="w-12 h-12 text-red-400 mx-auto" />
          <h3 className="text-white font-bold text-lg">Failed to Load Assignments</h3>
          <p className="text-red-200/80 text-sm max-w-md mx-auto">{error}</p>
          <button
            onClick={() => {
              setLoading(true);
              fetchAssignments();
            }}
            className="flex items-center gap-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 py-2.5 px-5 rounded-xl transition mx-auto shadow-md shadow-indigo-600/10"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry Loading
          </button>
        </div>
      ) : loading ? (
        /* Loading Skeletons */
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      ) : assignments.length === 0 ? (
        /* Empty State */
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60 max-w-2xl mx-auto">
          <ListTodo className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No assigned issues yet</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto mb-6">
            Go to the Issues page, select an open issue, and click 'Request Assignment' to begin.
          </p>
          <Link
            to="/issues"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 py-2.5 px-5 rounded-xl transition shadow-md shadow-indigo-600/15"
          >
            Go to Issue Discovery
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      ) : (
        /* Assignments List */
        <div className="space-y-4">
          {assignments.map((assignment) => {
            const hasAgentRun = !!assignment.agent_run_id;
            const repoOwner = assignment.repository_owner || assignment.issue?.url?.replace("https://github.com/", "").split("/")[0] || "Unknown";
            const repoName = assignment.repository_name || assignment.issue?.url?.replace("https://github.com/", "").split("/")[1] || "Repository";
            const issueNum = assignment.issue_number || assignment.issue?.number;
            const issueTitle = assignment.issue_title || assignment.issue?.title || "Issue Title";
            const issueUrl = assignment.issue_url || assignment.issue?.url;
            
            return (
              <div 
                key={assignment.id} 
                className="glass-card p-6 rounded-2xl border border-gray-800/80 hover:border-gray-700/80 transition-all duration-300 flex flex-col gap-6"
              >
                {/* Top Row: Repository and Badges */}
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                  <div className="space-y-1">
                    {/* Repository Name */}
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400">
                      <Folder className="w-3.5 h-3.5 text-indigo-500" />
                      <span>{repoOwner}</span>
                      <span className="text-gray-600">/</span>
                      <span>{repoName}</span>
                    </div>
                    {/* Issue Title and Link */}
                    <h3 className="font-bold text-white text-base md:text-lg flex items-center gap-2 flex-wrap">
                      <span className="text-gray-400">#{issueNum}</span>
                      <span>{issueTitle}</span>
                      {issueUrl && (
                        <a 
                          href={issueUrl} 
                          target="_blank" 
                          rel="noopener noreferrer" 
                          className="text-gray-500 hover:text-indigo-400 transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </h3>
                  </div>

                  {/* Status Badges */}
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Assignment:</span>
                      <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border ${getStatusColor(assignment.status)}`}>
                        {(assignment.status || "").replace(/_/g, " ")}
                      </span>
                    </div>

                    {assignment.workflow_status && (
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider">Workflow:</span>
                        <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider border flex items-center gap-1 ${getWorkflowStatusColor(assignment.workflow_status)}`}>
                          {["pending", "running", "validating", "reviewing"].includes(assignment.workflow_status.toLowerCase()) && (
                            <Loader2 className="w-2.5 h-2.5 animate-spin" />
                          )}
                          {assignment.workflow_status}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Divider */}
                <div className="h-px bg-gray-800/40"></div>

                {/* Middle Section: Labels & Helper Logs */}
                <div className="space-y-4">
                  {/* Issue Labels */}
                  {((assignment.issue?.difficulty) || (assignment.issue?.labels && assignment.issue.labels.length > 0)) && (
                    <div className="flex flex-wrap gap-1.5">
                      {assignment.issue?.difficulty && (
                        <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider border ${
                          assignment.issue.difficulty === "easy" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                          assignment.issue.difficulty === "medium" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                          assignment.issue.difficulty === "hard" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                          "bg-gray-800 text-gray-400 border-gray-700"
                        }`}>
                          {assignment.issue.difficulty}
                        </span>
                      )}
                      {assignment.issue?.labels && assignment.issue.labels.map((lbl, idx) => (
                        <span 
                          key={idx} 
                          className="text-[10px] bg-gray-900/90 text-gray-400 border border-gray-800 px-2 py-0.5 rounded font-semibold flex items-center gap-1"
                        >
                          <Tag className="w-2.5 h-2.5" />
                          {lbl}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Status Descriptive Message */}
                  <div className="space-y-2">
                    <p className="text-xs text-gray-400 leading-relaxed">
                      {assignment.status === "requested" && (
                        <span className="flex items-center gap-1.5 text-amber-400/80">
                          <Clock className="w-3.5 h-3.5" />
                          Waiting to post GitHub request comment.
                        </span>
                      )}
                      {assignment.status === "comment_posted" && (
                        <span className="flex items-center gap-1.5 text-blue-400/80">
                          <Clock className="w-3.5 h-3.5 animate-pulse" />
                          Request comment posted on GitHub. Waiting for repository maintainers to approve and assign this issue.
                        </span>
                      )}
                      {(assignment.status === "assigned" || assignment.status === "active" || assignment.status === "approved") && !hasAgentRun && (
                        <span className="flex items-center gap-1.5 text-emerald-400/80">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Assigned successfully! Initialization and code cloning in progress.
                        </span>
                      )}
                      {hasAgentRun && (
                        <span className="flex items-center gap-1.5 text-indigo-400/80 font-medium">
                          <CheckCircle className="w-3.5 h-3.5 text-indigo-500" />
                          Assigned! Autonomous coding flow execution is in state '{assignment.workflow_status}'.
                        </span>
                      )}
                      {assignment.status === "rejected" && (
                        <span className="flex items-center gap-1.5 text-red-400/80">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          Issue assignment was declined, assigned to another contributor, or the issue was closed.
                        </span>
                      )}
                    </p>

                    {/* Current Stage Indicator */}
                    {hasAgentRun && assignment.current_stage && (
                      <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-950/20 border border-indigo-500/10 text-indigo-300">
                        <span className="w-2 h-2 rounded-full bg-indigo-500 animate-ping"></span>
                        <span className="text-[10px] text-gray-400 uppercase tracking-wider mr-1">Current Stage:</span>
                        <span className="capitalize text-white">{(assignment.current_stage || "").replace(/_/g, " ")}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Bottom Row: Date & Action Links */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-gray-800/30">
                  {/* Timestamp */}
                  <div className="flex items-center gap-1.5 text-xs text-gray-500">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Requested: {formatDate(assignment.created_at)}</span>
                  </div>

                  {/* Links / Monitor Trigger */}
                  <div className="flex flex-wrap items-center gap-4">
                    {assignment.repository_url && (
                      <a 
                        href={assignment.repository_url} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="text-xs text-gray-400 hover:text-white transition-colors hover:underline flex items-center gap-1"
                      >
                        <Folder className="w-3 h-3" />
                        Repository Homepage
                      </a>
                    )}
                    {assignment.comment_url && (
                      <a 
                        href={assignment.comment_url} 
                        target="_blank" 
                        rel="noopener noreferrer" 
                        className="text-xs text-gray-400 hover:text-white transition-colors hover:underline flex items-center gap-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        View Request Comment
                      </a>
                    )}
                    
                    {hasAgentRun && (
                      <Link
                        to={`/agent-monitor?issueId=${assignment.issue_id}&runId=${assignment.agent_run_id}`}
                        className="text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 py-2 px-3.5 rounded-xl flex items-center gap-1.5 transition-all shadow-md shadow-indigo-600/15"
                      >
                        <Play className="w-3 h-3 fill-current" />
                        Monitor Agent
                      </Link>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

