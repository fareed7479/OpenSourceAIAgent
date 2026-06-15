import React, { useState, useEffect } from "react";
import { Search, Loader2, BookOpen, UserPlus, RefreshCw, Sparkles, CheckCircle2, ChevronRight } from "lucide-react";
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
  const [search, setSearch] = useState("");
  
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
  }, [selectedRepo, selectedDiff]);

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
      setMsg("Assignment request submitted! Monitoring status changes.");
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
      setMsg("Repository scan scheduled! Refreshing issues shortly.");
      setTimeout(loadData, 3000);
    } catch (err: any) {
      alert(err.message || "Failed to trigger scan.");
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Issue Discovery</h1>
          <p className="text-gray-400 text-sm mt-1">Discovered open repository issues indexed and ranked by AI compatibility.</p>
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
        <div className="flex items-center gap-2 p-3 bg-indigo-500/10 border border-indigo-500/20 text-indigo-200 text-xs rounded-xl">
          <CheckCircle2 className="w-4 h-4 text-indigo-400 flex-shrink-0" />
          <span>{msg}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <form onSubmit={handleSearchSubmit} className="glass-panel p-4 rounded-xl border border-gray-800/80 flex flex-col md:flex-row gap-4 items-end">
        <div className="flex-1 w-full space-y-1.5">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Repository</label>
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm"
          >
            <option value="">All Connected Repos</option>
            {repos.map((r) => (
              <option key={r.id} value={r.id}>{r.owner}/{r.name}</option>
            ))}
          </select>
        </div>

        <div className="w-full md:w-48 space-y-1.5">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Difficulty</label>
          <select
            value={selectedDiff}
            onChange={(e) => setSelectedDiff(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm"
          >
            <option value="">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        <div className="flex-1 w-full space-y-1.5">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Keyword Search</label>
          <div className="relative">
            <input
              type="text"
              placeholder="Search in titles/descriptions..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 pl-3 pr-10 outline-none text-sm"
            />
            <button type="submit" className="absolute right-3 top-2.5 text-gray-500 hover:text-gray-300">
              <Search className="w-4.5 h-4.5" />
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
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
          <BookOpen className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No issues indexed</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">Select a repository from filters and click 'Scan Repository Issues' to crawl open issues.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-widest px-1">Recommended Issues Priority List</h2>
          {issues.map((issue) => (
            <div key={issue.id} className="glass-card p-6 rounded-2xl border border-gray-800 hover:border-indigo-500/20 transition-all flex flex-col md:flex-row justify-between gap-6">
              
              {/* Left Column: Details */}
              <div className="flex-1 space-y-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                    issue.difficulty === "easy" 
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                      : issue.difficulty === "medium"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : "bg-red-500/10 text-red-400 border border-red-500/20"
                  }`}>
                    {issue.difficulty}
                  </span>
                  
                  {/* Score badge */}
                  <span className="flex items-center gap-1 text-[10px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-0.5 rounded-full">
                    <Sparkles className="w-3 h-3" />
                    Score: {issue.score}
                  </span>

                  {/* Assignment Status badge */}
                  <span className={`text-[10px] font-semibold px-2.5 py-0.5 rounded-md ${
                    issue.assignment_status === "unassigned"
                      ? "bg-gray-800 text-gray-400"
                      : issue.assignment_status === "requested"
                      ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                      : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                  }`}>
                    {issue.assignment_status === "assigned_to_user" ? "assigned to you" : issue.assignment_status}
                  </span>
                </div>

                <div>
                  <h3 className="font-bold text-white text-base hover:text-indigo-400 hover:underline transition">
                    <a href={issue.url} target="_blank" rel="noopener noreferrer">
                      #{issue.number} {issue.title}
                    </a>
                  </h3>
                  <p className="text-xs text-gray-500 font-semibold mt-0.5">Reasoning: {issue.ranking_reason}</p>
                </div>

                <div className="flex flex-wrap gap-1.5 pt-1">
                  {issue.labels.map((l) => (
                    <span key={l} className="text-[10px] bg-gray-950 border border-gray-800/80 text-gray-400 px-2.5 py-0.5 rounded">
                      {l}
                    </span>
                  ))}
                </div>
              </div>

              {/* Right Column: CTA Buttons */}
              <div className="flex flex-row md:flex-col justify-end items-center gap-3">
                {issue.assignment_status === "unassigned" ? (
                  <button
                    onClick={() => handleRequestAssignment(issue.id)}
                    disabled={actionLoading !== null}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold py-2.5 px-5 rounded-xl shadow-md text-xs transition hover:scale-[1.01]"
                  >
                    {actionLoading === issue.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <UserPlus className="w-3.5 h-3.5" />
                    )}
                    Request Assignment
                  </button>
                ) : (
                  <div className="flex items-center gap-1.5 text-xs text-indigo-400/90 font-semibold bg-indigo-950/20 border border-indigo-500/10 py-2 px-4 rounded-xl">
                    <span>Monitored</span>
                  </div>
                )}
                
                <a
                  href={issue.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-xs text-gray-400 hover:text-white transition py-2 px-4 border border-gray-800 hover:border-gray-700 rounded-xl"
                >
                  GitHub Link
                  <ChevronRight className="w-3 h-3" />
                </a>
              </div>
              
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
