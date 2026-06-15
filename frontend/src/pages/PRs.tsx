import React, { useState, useEffect } from "react";
import { GitPullRequest, Loader2, CheckCircle2, XCircle, ArrowUpRight, Check, X, ShieldAlert } from "lucide-react";
import { api } from "../api/client";

interface PullRequest {
  id: string;
  agent_run_id: string;
  title: string;
  description: string;
  url?: string;
  github_pr_id?: number;
  status: string;
  files_changed: string[];
  tests_passed?: boolean;
  review_status?: string;
  approval_status: string;
  created_at: string;
  updated_at: string;
}

export const PRs: React.FC = () => {
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [selectedPr, setSelectedPr] = useState<PullRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [rejectFeedback, setRejectFeedback] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const fetchPrs = async () => {
    try {
      const data = await api.get<PullRequest[]>("/prs");
      setPrs(data);
      
      // Update selected PR details
      if (selectedPr) {
        const updated = data.find((p) => p.id === selectedPr.id);
        if (updated) {
          setSelectedPr(updated);
        }
      }
    } catch (err) {
      console.error("Failed to load PRs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPrs();
    const interval = setInterval(fetchPrs, 4000);
    return () => clearInterval(interval);
  }, [selectedPr?.id]);

  const handleApprove = async () => {
    if (!selectedPr) return;
    setActionLoading(true);
    try {
      const updatedPr = await api.post<PullRequest>(`/prs/${selectedPr.id}/approve`);
      setSelectedPr(updatedPr);
      fetchPrs();
      alert("Pull Request submitted successfully to GitHub upstream!");
    } catch (err: any) {
      alert(err.message || "Failed to submit PR.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPr || !rejectFeedback.trim()) return;
    
    setActionLoading(true);
    try {
      const updatedPr = await api.post<PullRequest>(`/prs/${selectedPr.id}/reject`, {
        approved: false,
        feedback: rejectFeedback
      });
      setSelectedPr(updatedPr);
      setRejectFeedback("");
      setShowRejectForm(false);
      fetchPrs();
      alert("PR Draft rejected with feedback.");
    } catch (err: any) {
      alert(err.message || "Failed to submit rejection.");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-none">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Pull Requests</h1>
        <p className="text-gray-400 text-sm mt-1">Review AI-generated draft contributions, check review reports, and approve submission.</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        </div>
      ) : prs.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
          <GitPullRequest className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No pull requests generated</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">Draft PRs will show up here once an agent finishes workspace execution and validations.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* PR Sidebar List */}
          <div className="lg:col-span-1 space-y-4 max-h-[600px] overflow-y-auto pr-2">
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest px-1">Draft & Submissions</h2>
            <div className="space-y-3">
              {prs.map((pr) => {
                const isSelected = selectedPr?.id === pr.id;
                return (
                  <button
                    key={pr.id}
                    onClick={() => {
                      setSelectedPr(pr);
                      setShowRejectForm(false);
                    }}
                    className={`w-full text-left p-4 rounded-xl border transition-all ${
                      isSelected 
                        ? "bg-indigo-600/10 border-indigo-500/30 shadow-indigo-600/5 shadow" 
                        : "glass-card border-gray-900"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        pr.status === "submitted" 
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                          : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      }`}>
                        {pr.status}
                      </span>
                      <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                        pr.approval_status === "approved" 
                          ? "bg-emerald-500/10 text-emerald-400" 
                          : pr.approval_status === "rejected"
                          ? "bg-red-500/10 text-red-400"
                          : "bg-gray-800 text-gray-400"
                      }`}>
                        {pr.approval_status}
                      </span>
                    </div>
                    
                    <h4 className="font-bold text-white text-xs truncate mb-1">{pr.title}</h4>
                    <span className="text-[10px] text-gray-500">Changed: {pr.files_changed.length} files</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* PR Details View */}
          <div className="lg:col-span-2 space-y-6">
            {selectedPr ? (
              <div className="glass-panel p-6 md:p-8 rounded-2xl border border-gray-800/80 space-y-6">
                
                {/* Header */}
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-gray-800/60">
                  <div>
                    <h2 className="text-xl font-bold text-white">{selectedPr.title}</h2>
                    <span className="text-xs text-gray-500 block mt-0.5">Status: {selectedPr.status} • Approval: {selectedPr.approval_status}</span>
                  </div>
                  
                  {selectedPr.status === "submitted" && selectedPr.url && (
                    <a
                      href={selectedPr.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 hover:bg-indigo-950/40 py-2.5 px-4 rounded-xl transition"
                    >
                      View on GitHub
                      <ArrowUpRight className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>

                {/* Validation and Testing Stats */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-gray-950 border border-gray-800/80 flex items-center gap-3">
                    {selectedPr.tests_passed ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                    )}
                    <div>
                      <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Test Validation</span>
                      <span className="font-semibold text-xs text-white block">
                        {selectedPr.tests_passed ? "Build & Tests Passed" : "Build/Tests Failed"}
                      </span>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-gray-950 border border-gray-800/80 flex items-center gap-3">
                    <ShieldAlert className="w-5 h-5 text-indigo-400 flex-shrink-0" />
                    <div>
                      <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Modified Code</span>
                      <span className="font-semibold text-xs text-white block">
                        {selectedPr.files_changed.length} file(s) affected
                      </span>
                    </div>
                  </div>
                </div>

                {/* Tab layout: PR Description & AI Code Review Report */}
                <div className="space-y-4">
                  <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest px-1">PR Description</h3>
                  <div className="p-5 bg-gray-950/40 border border-gray-900 rounded-xl max-h-56 overflow-y-auto">
                    <pre className="text-xs text-gray-300 font-sans whitespace-pre-wrap">{selectedPr.description}</pre>
                  </div>
                </div>

                {selectedPr.review_status && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-bold text-gray-400 uppercase tracking-widest px-1">AI Code Review Report</h3>
                    <div className="p-5 bg-indigo-950/10 border border-indigo-500/10 rounded-xl max-h-56 overflow-y-auto">
                      <pre className="text-xs text-gray-300 font-sans whitespace-pre-wrap">{selectedPr.review_status}</pre>
                    </div>
                  </div>
                )}

                {/* Human Approval buttons */}
                {selectedPr.status === "draft" && selectedPr.approval_status === "pending" && (
                  <div className="pt-6 border-t border-gray-800/60 flex flex-wrap gap-4 justify-end">
                    {!showRejectForm ? (
                      <>
                        <button
                          onClick={() => setShowRejectForm(true)}
                          className="flex items-center gap-2 text-xs font-semibold text-red-400 bg-red-950/15 hover:bg-red-950/30 border border-red-500/20 py-3 px-6 rounded-xl transition"
                        >
                          <X className="w-4 h-4" />
                          Reject Draft Fix
                        </button>
                        
                        <button
                          onClick={handleApprove}
                          disabled={actionLoading}
                          className="flex items-center gap-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 py-3 px-6 rounded-xl shadow-lg shadow-indigo-600/15 transition duration-150 hover:scale-[1.01]"
                        >
                          {actionLoading ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Check className="w-4 h-4" />
                          )}
                          Approve & Submit PR
                        </button>
                      </>
                    ) : (
                      <form onSubmit={handleReject} className="w-full space-y-3">
                        <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider">
                          Rejection Feedback
                        </label>
                        <textarea
                          placeholder="Provide details on what needs to be fixed or modified..."
                          rows={3}
                          value={rejectFeedback}
                          onChange={(e) => setRejectFeedback(e.target.value)}
                          className="w-full bg-gray-950 border border-gray-800 text-gray-200 rounded-xl p-3 outline-none text-xs"
                        />
                        <div className="flex gap-3 justify-end">
                          <button
                            type="button"
                            onClick={() => setShowRejectForm(false)}
                            className="text-xs text-gray-400 hover:text-white py-2 px-4 border border-gray-800 hover:border-gray-700 rounded-xl"
                          >
                            Cancel
                          </button>
                          <button
                            type="submit"
                            disabled={!rejectFeedback.trim() || actionLoading}
                            className="bg-red-600 hover:bg-red-500 text-white font-semibold py-2 px-5 rounded-xl text-xs transition"
                          >
                            Submit Rejection
                          </button>
                        </div>
                      </form>
                    )}
                  </div>
                )}
                
              </div>
            ) : (
              <div className="glass-panel rounded-2xl border border-gray-800/80 p-12 text-center h-[500px] flex flex-col justify-center items-center">
                <GitPullRequest className="w-12 h-12 text-gray-700 mb-4 animate-pulse" />
                <h3 className="text-white font-bold text-lg mb-1">Select a Pull Request</h3>
                <p className="text-gray-400 text-sm max-w-xs">Select any PR from the left sidebar to view test stats, changes list, code reviews, and execute final approvals.</p>
              </div>
            )}
          </div>
          
        </div>
      )}
    </div>
  );
};
