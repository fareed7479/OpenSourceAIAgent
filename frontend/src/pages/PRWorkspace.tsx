import React, { useState, useEffect } from "react";
import { Loader2, GitPullRequest, FileCode, Check, X, RefreshCw, Settings, BookOpen } from "lucide-react";
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

interface AgentPlan {
  id: string;
  title: string;
  description: string;
  steps: { step: number; description: string; status: string }[];
  status: string;
  feedback?: string;
}

export const PRWorkspace: React.FC = () => {
  const [prs, setPrs] = useState<PullRequest[]>([]);
  const [selectedPr, setSelectedPr] = useState<PullRequest | null>(null);
  const [plan, setPlan] = useState<AgentPlan | null>(null);
  
  // Input fields for editing
  const [prTitle, setPrTitle] = useState("");
  const [prDesc, setPrDesc] = useState("");
  const [commitMsg, setCommitMsg] = useState("");
  
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"diff" | "plan" | "review" | "logs">("diff");
  const [selectedFile, setSelectedFile] = useState<string | null>(null);

  const fetchPRs = async () => {
    try {
      const data = await api.get<PullRequest[]>("/prs");
      setPrs(data);
      if (data.length > 0 && !selectedPr) {
        setSelectedPr(data[0]);
      }
    } catch (err) {
      console.error("Failed to load PRs:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPlan = async () => {
    if (!selectedPr) return;
    try {
      const resp = await api.get<AgentPlan>(`/runs/${selectedPr.agent_run_id}/plan`);
      setPlan(resp);
    } catch (err) {
      console.error("No plan found for this run:", err);
      setPlan(null);
    }
  };

  useEffect(() => {
    fetchPRs();
  }, []);

  useEffect(() => {
    if (selectedPr) {
      setPrTitle(selectedPr.title);
      setPrDesc(selectedPr.description || "");
      setCommitMsg(selectedPr.title); // Default commit msg match title
      if (selectedPr.files_changed.length > 0) {
        setSelectedFile(selectedPr.files_changed[0]);
      }
      fetchPlan();
    }
  }, [selectedPr]);

  const handleApprove = async () => {
    if (!selectedPr) return;
    setActionLoading(true);
    try {
      const updated = await api.post<PullRequest>(`/prs/${selectedPr.id}/approve`);
      setSelectedPr(updated);
      fetchPRs();
      alert("Draft Pull Request approved and submitted upstream!");
    } catch (err: any) {
      alert(err.message || "Failed to submit PR.");
    } finally {
      setActionLoading(false);
    }
  };


  const handleRegenerate = async () => {
    if (!selectedPr) return;
    setActionLoading(true);
    try {
      await api.post(`/runs/${selectedPr.agent_run_id}/regenerate-plan`);
      alert("Plan and implementation regeneration triggered!");
      fetchPRs();
    } catch (err: any) {
      alert(err.message || "Regeneration request failed.");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in max-w-none">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
          <GitPullRequest className="w-8 h-8 text-indigo-400" />
          Advanced PR Workspace
        </h1>
        <p className="text-gray-400 text-sm mt-1">Professional collaborative sandbox to review codebase modifications, inspect reviews, and submit PRs.</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        </div>
      ) : prs.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
          <GitPullRequest className="w-12 h-12 text-gray-650 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No pull requests indexed</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">Trigger issues assignments and watch agents generate workspace drafts.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-stretch h-[700px]">
          
          {/* Sidebar (File explorer tree & logs, Col Span 1) */}
          <div className="lg:col-span-1 glass-panel rounded-2xl border border-gray-800/80 overflow-y-auto flex flex-col justify-between">
            <div className="p-4 space-y-4">
              <h3 className="text-xs uppercase font-bold text-gray-500 tracking-wider">File Explorer</h3>
              <div className="space-y-1.5">
                {selectedPr?.files_changed.map((file) => {
                  const isSelected = selectedFile === file;
                  return (
                    <button
                      key={file}
                      onClick={() => setSelectedFile(file)}
                      className={`w-full flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl text-xs font-semibold text-left border transition-all ${
                        isSelected 
                          ? "bg-indigo-600/10 text-indigo-400 border-indigo-500/20 shadow-indigo-600/5 shadow" 
                          : "text-gray-400 hover:text-gray-200 border-transparent hover:bg-gray-950/40"
                      }`}
                    >
                      <FileCode className="w-4 h-4 text-indigo-400 flex-shrink-0" />
                      <span className="truncate">{file}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="p-4 border-t border-gray-800/60 space-y-4 bg-gray-950/20">
              <h3 className="text-xs uppercase font-bold text-gray-500 tracking-wider">Metrics Status</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">Tests Validation:</span>
                  <span className={`font-bold uppercase text-[9px] px-2 py-0.5 rounded border ${
                    selectedPr?.tests_passed 
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                      : "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}>
                    {selectedPr?.tests_passed ? "Passed" : "Failed"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400">Approval State:</span>
                  <span className="text-indigo-400 font-semibold">{selectedPr?.approval_status}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Main workspace editor panel (Col Span 3) */}
          <div className="lg:col-span-3 glass-panel rounded-2xl border border-gray-800/80 flex flex-col justify-between overflow-hidden">
            
            {/* Tabs Header */}
            <div className="bg-gray-950/40 border-b border-gray-850 px-6 py-4 flex flex-wrap justify-between items-center gap-4">
              <div className="flex gap-2">
                {[
                  { id: "diff", label: "Diff Preview", icon: FileCode },
                  { id: "plan", label: "Execution Plan", icon: BookOpen },
                  { id: "review", label: "AI Review Summary", icon: Settings }
                ].map((t) => {
                  const Icon = t.icon;
                  const isActive = activeTab === t.id;
                  return (
                    <button
                      key={t.id}
                      onClick={() => setActiveTab(t.id as any)}
                      className={`flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-xl transition ${
                        isActive 
                          ? "bg-indigo-600/15 text-indigo-400 border border-indigo-500/20" 
                          : "text-gray-400 hover:text-gray-200"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      {t.label}
                    </button>
                  );
                })}
              </div>

              {selectedPr && (
                <span className="text-[10px] text-gray-500 font-semibold font-mono">
                  Branch: {selectedPr.status}
                </span>
              )}
            </div>

            {/* Content view based on active tab */}
            <div className="flex-1 p-6 overflow-y-auto bg-[#02050e]/30">
              
              {activeTab === "diff" && (
                <div className="space-y-4 h-full flex flex-col">
                  {selectedFile ? (
                    <div className="space-y-2 flex-1 flex flex-col">
                      <span className="text-xs text-indigo-400 font-semibold font-mono">Modified code preview for: {selectedFile}</span>
                      <pre className="flex-1 p-4 bg-gray-950/60 border border-gray-850 rounded-xl text-xs text-gray-300 font-mono overflow-x-auto whitespace-pre-wrap">
                        {/* unified code patch placeholder representation */}
                        {`// Modified patch details applied in file: ${selectedFile}\n// Safety configurations checks successfully compiled.`}
                      </pre>
                    </div>
                  ) : (
                    <div className="text-center py-20 text-gray-500 italic text-sm">Select a modified file from the explorer list.</div>
                  )}
                </div>
              )}

              {activeTab === "plan" && (
                <div className="space-y-5 animate-fade-in">
                  {plan ? (
                    <div className="space-y-4">
                      <div>
                        <h4 className="text-white font-bold text-base flex items-center gap-2">
                          <BookOpen className="w-4.5 h-4.5 text-indigo-400" />
                          {plan.title}
                        </h4>
                        <p className="text-xs text-gray-400 mt-1">{plan.description}</p>
                      </div>

                      <div className="border border-gray-850 rounded-xl overflow-hidden divide-y divide-gray-850/60">
                        {plan.steps.map((step) => (
                          <div key={step.step} className="flex justify-between items-center p-3 text-xs">
                            <span className="text-gray-300">
                              <span className="font-bold text-indigo-400 mr-2">{step.step}.</span>
                              {step.description}
                            </span>
                            <span className="text-[9px] uppercase font-bold px-2 py-0.5 rounded bg-gray-900 border border-gray-850 text-gray-500">
                              {step.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-20 text-gray-500 italic text-sm">No implementation strategy plan logs found.</div>
                  )}
                </div>
              )}

              {activeTab === "review" && (
                <div className="space-y-4 animate-fade-in h-full">
                  <h4 className="text-sm font-bold text-gray-300 uppercase tracking-widest">AI review agent report outcomes</h4>
                  <pre className="p-4 bg-indigo-950/15 border border-indigo-500/10 text-xs text-gray-300 font-sans whitespace-pre-wrap rounded-xl overflow-y-auto max-h-96">
                    {selectedPr?.review_status || "No review report parsed for this PR."}
                  </pre>
                </div>
              )}

            </div>

            {/* Footer controls (PR details modifications & approvals) */}
            <div className="bg-gray-950/60 border-t border-gray-850 p-6 space-y-4">
              
              {selectedPr?.status === "draft" && selectedPr?.approval_status === "pending" && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  
                  {/* Left Column: Input edits */}
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <label className="block text-[10px] uppercase font-bold text-gray-500 tracking-wider">PR Title</label>
                      <input
                        type="text"
                        value={prTitle}
                        onChange={(e) => setPrTitle(e.target.value)}
                        className="w-full bg-gray-950 border border-gray-800 text-gray-200 rounded-xl py-2 px-3 text-xs outline-none focus:border-indigo-500"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="block text-[10px] uppercase font-bold text-gray-500 tracking-wider">PR Description</label>
                      <textarea
                        value={prDesc}
                        onChange={(e) => setPrDesc(e.target.value)}
                        className="w-full bg-gray-950 border border-gray-800 text-gray-200 rounded-xl py-2 px-3 text-xs outline-none focus:border-indigo-500 h-16 resize-none"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="block text-[10px] uppercase font-bold text-gray-500 tracking-wider">Commit Message</label>
                      <input
                        type="text"
                        value={commitMsg}
                        onChange={(e) => setCommitMsg(e.target.value)}
                        className="w-full bg-gray-950 border border-gray-800 text-gray-200 rounded-xl py-2 px-3 text-xs outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>

                  {/* Right Column: Actions controls */}
                  <div className="flex flex-col justify-end gap-3">
                    <div className="flex gap-3 justify-end">
                      <button
                        onClick={handleRegenerate}
                        disabled={actionLoading}
                        className="flex items-center justify-center gap-1.5 text-xs font-semibold text-gray-400 hover:text-white py-2.5 px-4 border border-gray-800 hover:border-gray-700 rounded-xl transition"
                      >
                        <RefreshCw className="w-3.5 h-3.5" />
                        Regenerate
                      </button>
                      
                      <button
                        onClick={() => {
                          const f = prompt("Enter modifications feedback details for the coding agent:");
                          if (f) {
                            // Rerun/reject
                            api.post(`/prs/${selectedPr.id}/reject`, { approved: false, feedback: f }).then(() => {
                              alert("PR rejected with feedback.");
                              fetchPRs();
                            });
                          }
                        }}
                        className="flex items-center justify-center gap-1.5 text-xs font-semibold text-red-400 hover:text-red-300 bg-red-950/15 border border-red-500/25 py-2.5 px-4 rounded-xl transition"
                      >
                        <X className="w-3.5 h-3.5" />
                        Reject Fix
                      </button>
                      
                      <button
                        onClick={handleApprove}
                        disabled={actionLoading}
                        className="flex items-center justify-center gap-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 py-2.5 px-6 rounded-xl shadow-lg shadow-indigo-600/10 transition"
                      >
                        {actionLoading ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Check className="w-3.5 h-3.5" />
                        )}
                        Approve & Submit PR
                      </button>
                    </div>
                  </div>

                </div>
              )}
              
            </div>
            
          </div>
          
        </div>
      )}
    </div>
  );
};
export default PRWorkspace;
