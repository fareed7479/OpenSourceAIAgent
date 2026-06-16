import React, { useState, useEffect } from "react";
import { ListTodo, Loader2, CheckCircle, RefreshCw, Clock, ArrowRight, ExternalLink } from "lucide-react";
import { api } from "../api/client";

interface Assignment {
  id: string;
  user_id: string;
  issue_id: string;
  status: string;
  request_comment_id?: number;
  comment_url?: string;
  issue_url?: string;
  repository_url?: string;
  created_at: string;
  issue?: {
    number: number;
    title: string;
    url: string;
    difficulty: string;
  };
}

export const Assignments: React.FC = () => {
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchAssignments = async () => {
    try {
      const data = await api.get<Assignment[]>("/assignments");
      setAssignments(data);
    } catch (err) {
      console.error("Failed to load assignments:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAssignments();
    // Poll assignment state updates every 5 seconds
    const interval = setInterval(fetchAssignments, 5000);
    return () => clearInterval(interval);
  }, []);

  const triggerSync = async () => {
    setSyncing(true);
    try {
      await api.post("/assignments/monitor");
      // Wait for background tasks to finish polling and reload
      setTimeout(fetchAssignments, 2000);
    } catch (err) {
      console.error("Sync failed:", err);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Assignments</h1>
          <p className="text-gray-400 text-sm mt-1">Assignments request statuses and polling monitoring.</p>
        </div>
        
        <button
          onClick={triggerSync}
          disabled={syncing}
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

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        </div>
      ) : assignments.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
          <ListTodo className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No assignment requests</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">Go to 'Issue Discovery', find an open issue, and click 'Request Assignment' to start.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {assignments.map((assignment) => (
            <div key={assignment.id} className="glass-card p-6 rounded-2xl border border-gray-800 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
              
              <div className="space-y-3 flex-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                    assignment.status === "assigned" 
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                      : assignment.status === "in_progress" 
                      ? "bg-indigo-500/10 text-indigo-400 border border-indigo-500/20" 
                      : assignment.status === "comment_posted" 
                      ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" 
                      : assignment.status === "requested"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : "bg-red-500/10 text-red-400 border border-red-500/20"
                  }`}>
                    {assignment.status.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] text-gray-500">Requested: {new Date(assignment.created_at).toLocaleDateString()}</span>
                </div>
                
                {assignment.issue && (
                  <div className="space-y-2">
                    <h3 className="font-bold text-white text-base flex items-center gap-2">
                      #{assignment.issue.number} {assignment.issue.title}
                      <a href={assignment.issue.url} target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-300 transition-colors">
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    </h3>
                    
                    <p className="text-xs text-gray-400">
                      {assignment.status === "requested" && (
                        <span className="flex items-center gap-1.5 text-amber-400/80">
                          <Clock className="w-3.5 h-3.5" />
                          Waiting to post GitHub request comment.
                        </span>
                      )}
                      {assignment.status === "comment_posted" && (
                        <span className="flex items-center gap-1.5 text-blue-400/80">
                          <Clock className="w-3.5 h-3.5 animate-pulse" />
                          Request comment posted. Waiting for repository maintainers to assign this issue.
                        </span>
                      )}
                      {assignment.status === "assigned" && (
                        <span className="flex items-center gap-1.5 text-emerald-400/80">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Assigned successfully! Coding workspace is being initialized.
                        </span>
                      )}
                      {assignment.status === "in_progress" && (
                        <span className="flex items-center gap-1.5 text-indigo-400/80 font-semibold">
                          <CheckCircle className="w-3.5 h-3.5" />
                          Assigned successfully! Agent coding flow is currently running.
                        </span>
                      )}
                      {assignment.status === "rejected" && (
                        <span className="text-red-400/80">
                          Issue was assigned to another contributor or closed.
                        </span>
                      )}
                    </p>

                    <div className="flex flex-wrap gap-4 pt-1 text-xs font-semibold">
                      {assignment.repository_url && (
                        <a href={assignment.repository_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors hover:underline">
                          <ExternalLink className="w-3 h-3" />
                          Repository Page
                        </a>
                      )}
                      {assignment.comment_url && (
                        <a href={assignment.comment_url} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors hover:underline">
                          <ExternalLink className="w-3 h-3" />
                          View Comment on GitHub
                        </a>
                      )}
                    </div>
                  </div>
                )}
              </div>
              
              {(assignment.status === "assigned" || assignment.status === "in_progress") && (
                <div className="flex items-center">
                  <span className="text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 py-2 px-4 rounded-xl flex items-center gap-1.5">
                    Coding Loop Triggered
                    <ArrowRight className="w-3.5 h-3.5 animate-pulse" />
                  </span>
                </div>
              )}
              
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
