import React, { useState, useEffect } from "react";
import { 
  Search, Loader2, BookOpen, UserPlus, RefreshCw, Sparkles, 
  CheckCircle2, ChevronRight, X, Calendar, MessageSquare, User, Tag, AlertCircle
} from "lucide-react";
import { api } from "../api/client";

interface Issue {
  id: string;
  repository_id: string;
  github_issue_id: number;
  number: number;
  title: string;
  description: string;
  url: string;
  labels: string[];
  difficulty: string;
  score: number;
  ranking_reason: string;
  status: string;
  assignment_status: string;
  assignee_username?: string;
  author_username?: string;
  github_created_at?: string;
  github_updated_at?: string;
  comments_count?: number;
}

interface Repository {
  id: string;
  owner: string;
  name: string;
}

export const Issues: React.FC = () => {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [repos, setRepos] = useState<Repository[]>([]);
  
  // Filters
  const [selectedRepo, setSelectedRepo] = useState("");
  const [selectedDiff, setSelectedDiff] = useState("");
  const [selectedLabel, setSelectedLabel] = useState("");
  const [selectedState, setSelectedState] = useState("open"); // open, closed, all
  const [search, setSearch] = useState("");
  
  // Modals and loading
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [msg, setMsg] = useState("");

  const loadData = async () => {
    try {
      // Load repos for filter dropdown
      const repoData = await api.get<Repository[]>("/repositories");
      setRepos(repoData);

      // Load issues
      let path = "/issues";
      const params: string[] = [];
      if (selectedRepo) params.push(`repository_id=${selectedRepo}`);
      if (selectedDiff) params.push(`difficulty=${selectedDiff}`);
      if (selectedLabel) params.push(`label=${encodeURIComponent(selectedLabel)}`);
      if (selectedState) params.push(`state=${selectedState}`);
      if (search) params.push(`search=${encodeURIComponent(search)}`);
      
      if (params.length > 0) {
        path += `?${params.join("&")}`;
      }
      
      const issueData = await api.get<Issue[]>(path);
      setIssues(issueData);
    } catch (err) {
      console.error("Failed to load issues:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedRepo, selectedDiff, selectedState, selectedLabel]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    loadData();
  };

  const handleRequestAssignment = async (issueId: string) => {
    setActionLoading(issueId);
    setMsg("");
    try {
      await api.post("/assignments/request", { issue_id: issueId });
      setMsg("Assignment request submitted successfully! Monitoring status changes.");
      // Refresh current issue details inside modal if open
      if (selectedIssue && selectedIssue.id === issueId) {
        setSelectedIssue({
          ...selectedIssue,
          assignment_status: "requested"
        });
      }
      loadData();
    } catch (err: any) {
      alert(err.message || "Failed to request assignment.");
    } finally {
      setActionLoading(null);
    }
  };

  const triggerManualScan = async () => {
    if (!selectedRepo) {
      alert("Please select a specific repository from the filters dropdown to scan.");
      return;
    }
    setLoading(true);
    try {
      await api.post(`/issues/scan/${selectedRepo}`);
      setMsg("Repository issues scan scheduled! Refreshing shortly.");
      setTimeout(loadData, 3000);
    } catch (err: any) {
      alert(err.message || "Failed to trigger scan.");
      setLoading(false);
    }
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return "N/A";
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6 animate-fade-in relative">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Issue Discovery</h1>
          <p className="text-gray-400 text-sm mt-1">Discovered open & closed repository issues indexed and ranked by AI suitability.</p>
        </div>
        
        <div className="flex items-center gap-3">
          {selectedRepo && (
            <button
              onClick={triggerManualScan}
              className="flex items-center gap-2 text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 hover:bg-indigo-950/40 py-2.5 px-4 rounded-xl transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Scan Repository Issues
            </button>
          )}
        </div>
      </div>

      {msg && (
        <div className="flex items-center gap-2.5 p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 text-sm rounded-xl">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{msg}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <form onSubmit={handleSearchSubmit} className="glass-panel p-5 rounded-2xl border border-gray-800/80 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
        <div className="space-y-1.5">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Repository</label>
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm transition focus:border-indigo-500"
          >
            <option value="">All Connected Repos</option>
            {repos.map((r) => (
              <option key={r.id} value={r.id}>{r.owner}/{r.name}</option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Difficulty</label>
          <select
            value={selectedDiff}
            onChange={(e) => setSelectedDiff(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm transition focus:border-indigo-500"
          >
            <option value="">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Label Filter</label>
          <input
            type="text"
            placeholder="e.g., bug, help-wanted"
            value={selectedLabel}
            onChange={(e) => setSelectedLabel(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm transition focus:border-indigo-500"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">State</label>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm transition focus:border-indigo-500"
          >
            <option value="open">Open Issues Only</option>
            <option value="closed">Closed Issues Only</option>
            <option value="all">All States</option>
          </select>
        </div>

        <div className="space-y-1.5">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Search Keywords</label>
          <div className="relative">
            <input
              type="text"
              placeholder="Search title..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 pl-3 pr-10 outline-none text-sm transition focus:border-indigo-500"
            />
            <button type="submit" className="absolute right-3 top-3 text-gray-500 hover:text-gray-300">
              <Search className="w-4 h-4" />
            </button>
          </div>
        </div>
      </form>

      {/* Issues Display */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        </div>
      ) : issues.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60 max-w-lg mx-auto">
          <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No matching issues</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">Try clearing your filters or select a repository to trigger a manual scan.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex justify-between items-center px-1">
            <h2 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Suitability Recommended List</h2>
            <span className="text-xs text-gray-500 font-semibold">{issues.length} issues loaded</span>
          </div>
          
          <div className="space-y-4">
            {issues.map((issue) => (
              <div 
                key={issue.id} 
                className={`glass-card p-5 rounded-2xl border transition-all duration-200 flex flex-col md:flex-row justify-between gap-6 cursor-pointer ${
                  issue.status === "closed" 
                    ? "border-gray-900 opacity-60 hover:opacity-100" 
                    : "border-gray-800/80 hover:border-indigo-500/20"
                }`}
                onClick={() => setSelectedIssue(issue)}
              >
                
                {/* Left Column: Details */}
                <div className="flex-1 space-y-3 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`text-[9px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                      issue.difficulty === "easy" 
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                        : issue.difficulty === "medium"
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        : "bg-red-500/10 text-red-400 border border-red-500/20"
                    }`}>
                      {issue.difficulty}
                    </span>
                    
                    <span className="flex items-center gap-1 text-[9px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-0.5 rounded-full">
                      <Sparkles className="w-2.5 h-2.5" />
                      Score: {issue.score}
                    </span>

                    <span className={`text-[9px] font-semibold px-2 py-0.5 rounded-md ${
                      issue.assignment_status === "unassigned"
                        ? "bg-gray-800 text-gray-400"
                        : issue.assignment_status === "requested"
                        ? "bg-blue-500/10 text-blue-400 border border-blue-500/20 animate-pulse"
                        : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    }`}>
                      {issue.assignment_status === "assigned_to_user" ? "assigned to you" : issue.assignment_status.replace(/_/g, " ")}
                    </span>

                    {issue.status === "closed" && (
                      <span className="text-[9px] font-bold bg-gray-900 border border-gray-800 text-gray-500 px-2 py-0.5 rounded-md uppercase">
                        Closed
                      </span>
                    )}
                  </div>

                  <div className="space-y-1">
                    <h3 className="font-extrabold text-white text-base hover:text-indigo-300 hover:underline transition truncate">
                      #{issue.number} {issue.title}
                    </h3>
                    
                    {issue.author_username && (
                      <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                        <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" /> {issue.author_username}</span>
                        {issue.comments_count !== undefined && (
                          <span className="flex items-center gap-1"><MessageSquare className="w-3.5 h-3.5" /> {issue.comments_count} comments</span>
                        )}
                        {issue.github_updated_at && (
                          <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" /> Updated {formatDate(issue.github_updated_at)}</span>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {issue.labels.map((l) => (
                      <span key={l} className="text-[9px] bg-gray-950 border border-gray-900 text-gray-400 px-2 py-0.5 rounded">
                        {l}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Right Column: CTA Buttons */}
                <div className="flex flex-row md:flex-col justify-end items-center gap-3 self-center" onClick={(e) => e.stopPropagation()}>
                  {issue.status === "open" && issue.assignment_status === "unassigned" ? (
                    <button
                      onClick={() => handleRequestAssignment(issue.id)}
                      disabled={actionLoading !== null}
                      className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold py-2 px-4 rounded-xl shadow-md text-xs transition active:scale-[0.98]"
                    >
                      {actionLoading === issue.id ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <UserPlus className="w-3.5 h-3.5" />
                      )}
                      Request Assignment
                    </button>
                  ) : (
                    <div className="text-xs text-indigo-400/80 font-bold bg-indigo-950/25 border border-indigo-500/15 py-2 px-4 rounded-xl cursor-default">
                      {issue.status === "closed" ? "Closed" : "Monitored"}
                    </div>
                  )}
                  
                  <a
                    href={issue.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition py-2 px-4 border border-gray-900 hover:border-gray-800 rounded-xl"
                  >
                    GitHub Link
                    <ChevronRight className="w-3 h-3" />
                  </a>
                </div>
                
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ISSUE DETAILS MODAL DIALOG */}
      {selectedIssue && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={() => setSelectedIssue(null)}>
          <div 
            className="glass-panel w-full max-w-3xl border border-gray-800 rounded-2xl flex flex-col max-h-[85vh] overflow-hidden shadow-2xl relative animate-fade-in"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex justify-between items-start p-6 border-b border-gray-900">
              <div className="space-y-1 max-w-[90%]">
                <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest block">Issue details</span>
                <h2 className="text-xl font-extrabold text-white">
                  #{selectedIssue.number} {selectedIssue.title}
                </h2>
                <div className="flex flex-wrap items-center gap-4 text-xs text-gray-400 pt-1">
                  {selectedIssue.author_username && (
                    <span className="flex items-center gap-1.5"><User className="w-3.5 h-3.5 text-indigo-400" /> Author: {selectedIssue.author_username}</span>
                  )}
                  {selectedIssue.comments_count !== undefined && (
                    <span className="flex items-center gap-1.5"><MessageSquare className="w-3.5 h-3.5 text-indigo-400" /> {selectedIssue.comments_count} comments</span>
                  )}
                  {selectedIssue.github_created_at && (
                    <span className="flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5 text-indigo-400" /> Created: {formatDate(selectedIssue.github_created_at)}</span>
                  )}
                </div>
              </div>
              
              <button 
                onClick={() => setSelectedIssue(null)}
                className="p-1.5 bg-gray-900 border border-gray-800 hover:bg-gray-850 hover:text-white text-gray-400 rounded-xl transition"
              >
                <X className="w-4.5 h-4.5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-6 flex-1 text-sm">
              {/* Badges Section */}
              <div className="flex flex-wrap gap-2.5 items-center">
                <span className={`text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider ${
                  selectedIssue.difficulty === "easy" 
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                    : selectedIssue.difficulty === "medium"
                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                    : "bg-red-500/10 text-red-400 border border-red-500/20"
                }`}>
                  Difficulty: {selectedIssue.difficulty}
                </span>

                <span className="flex items-center gap-1.5 text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-3 py-1 rounded-full">
                  <Sparkles className="w-3.5 h-3.5" />
                  Suitability Score: {selectedIssue.score}/100
                </span>

                <span className={`text-[10px] font-semibold px-3 py-1 rounded-md uppercase ${
                  selectedIssue.assignment_status === "unassigned"
                    ? "bg-gray-900 border border-gray-800 text-gray-400"
                    : selectedIssue.assignment_status === "requested"
                    ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                    : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                }`}>
                  Status: {selectedIssue.assignment_status.replace(/_/g, " ")}
                </span>
                
                {selectedIssue.status === "closed" && (
                  <span className="text-[10px] font-bold bg-gray-900 border border-gray-800 text-gray-500 px-3 py-1 rounded-md uppercase">
                    CLOSED ON GITHUB
                  </span>
                )}
              </div>

              {/* Suitability Score Breakdown */}
              <div className="p-4 bg-indigo-950/10 border border-indigo-500/10 rounded-2xl space-y-2.5">
                <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-300 flex items-center gap-1">
                  <Sparkles className="w-3.5 h-3.5" />
                  AI Suitability Analysis Reasons
                </h3>
                <ul className="text-xs text-gray-300 space-y-1.5 list-none pl-1">
                  {selectedIssue.ranking_reason.split(";").map((reason, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-indigo-400 font-extrabold flex-shrink-0">•</span>
                      <span>{reason.strip ? reason.strip() : reason.trim()}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Labels list */}
              {selectedIssue.labels.length > 0 && (
                <div className="space-y-1.5">
                  <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider flex items-center gap-1"><Tag className="w-3 h-3" /> Labels</span>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedIssue.labels.map((l) => (
                      <span key={l} className="text-xs bg-gray-950 border border-gray-800 text-gray-400 px-2.5 py-1 rounded-lg">
                        {l}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Description body */}
              <div className="space-y-2">
                <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider block">Description</span>
                <div className="bg-gray-950/60 border border-gray-900/60 p-5 rounded-2xl max-h-80 overflow-y-auto text-gray-300 font-mono text-xs whitespace-pre-wrap leading-relaxed">
                  {selectedIssue.description || "No description provided."}
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-6 border-t border-gray-900 flex flex-col sm:flex-row justify-between gap-3 bg-gray-950/40">
              <a 
                href={selectedIssue.url}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-gray-900 hover:bg-gray-850 text-gray-300 border border-gray-800 font-semibold py-2.5 px-5 rounded-xl text-xs flex items-center justify-center gap-1.5 transition active:scale-[0.98]"
              >
                View on GitHub
                <ChevronRight className="w-3.5 h-3.5" />
              </a>

              {selectedIssue.status === "open" && selectedIssue.assignment_status === "unassigned" ? (
                <button
                  onClick={() => handleRequestAssignment(selectedIssue.id)}
                  disabled={actionLoading !== null}
                  className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold py-2.5 px-6 rounded-xl text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-600/15 transition active:scale-[0.98]"
                >
                  {actionLoading === selectedIssue.id ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <UserPlus className="w-3.5 h-3.5" />
                  )}
                  Request Assignment
                </button>
              ) : (
                <div className="text-xs text-indigo-400 font-bold bg-indigo-950/20 border border-indigo-500/10 py-2.5 px-5 rounded-xl flex items-center justify-center cursor-default">
                  {selectedIssue.status === "closed" ? "Closed on GitHub" : "Monitored"}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
