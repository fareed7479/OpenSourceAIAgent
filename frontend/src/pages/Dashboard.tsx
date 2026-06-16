import React, { useState, useEffect } from "react";
import { 
  Plus, RefreshCw, AlertCircle, CheckCircle2, Loader2, GitFork, 
  Search, Star, Lock, Globe, ExternalLink, Calendar, Check
} from "lucide-react";
import { api } from "../api/client";

interface GithubRepo {
  name: string;
  full_name: string;
  description: string | null;
  html_url: string;
  clone_url: string;
  default_branch: string;
  fork: boolean;
  private: boolean;
  language: string | null;
  updated_at: string;
  stargazers_count: number;
  open_issues_count: number;
}

interface Repository {
  id: string;
  owner: string;
  name: string;
  url: string;
  branch: string;
  status: string;
  language?: string;
  framework?: string;
  build_system?: string;
  test_command?: string;
  lint_command?: string;
  meta_info?: {
    github_metadata?: {
      description?: string;
      fork?: boolean;
      private?: boolean;
      topics?: string[];
      stargazers_count?: number;
      open_issues_count?: number;
      updated_at?: string;
      clone_url?: string;
      html_url?: string;
    };
  };
  clone_path?: string;
  created_at: string;
}

export const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"registered" | "discover">("registered");
  const [repos, setRepos] = useState<Repository[]>([]);
  const [githubRepos, setGithubRepos] = useState<GithubRepo[]>([]);
  
  // Registration form state (for manual paste if needed)
  const [manualUrl, setManualUrl] = useState("");
  const [manualLoading, setManualLoading] = useState(false);
  
  // Async states
  const [fetchingRegistered, setFetchingRegistered] = useState(true);
  const [fetchingGithub, setFetchingGithub] = useState(false);
  const [registeringName, setRegisteringName] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  
  // Alerts and filters
  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState<"all" | "forks" | "original">("all");
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const fetchRegisteredRepos = async () => {
    try {
      const data = await api.get<Repository[]>("/repositories");
      setRepos(data);
    } catch (err: any) {
      console.error("Failed to load registered repositories:", err);
    } finally {
      setFetchingRegistered(false);
    }
  };

  const fetchGithubRepos = async () => {
    setFetchingGithub(true);
    setError("");
    try {
      const data = await api.get<GithubRepo[]>("/repositories/github");
      setGithubRepos(data);
    } catch (err: any) {
      setError(err.message || "Failed to fetch GitHub repositories. Check your token scope.");
    } finally {
      setFetchingGithub(false);
    }
  };

  useEffect(() => {
    fetchRegisteredRepos();
    // Poll registered repositories status in case they are cloning
    const interval = setInterval(fetchRegisteredRepos, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch GitHub repos when switching to discover tab
  useEffect(() => {
    if (activeTab === "discover" && githubRepos.length === 0) {
      fetchGithubRepos();
    }
  }, [activeTab]);

  const handleRegister = async (repoUrl: string, repoName: string) => {
    setRegisteringName(repoName);
    setError("");
    setSuccessMsg("");
    try {
      await api.post("/repositories/register", { url: repoUrl });
      setSuccessMsg(`Successfully registered ${repoName}! Local workspace setup started in the background.`);
      await fetchRegisteredRepos();
    } catch (err: any) {
      setError(err.message || `Failed to register repository ${repoName}.`);
    } finally {
      setRegisteringName(null);
    }
  };

  const handleManualRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!manualUrl.trim()) return;

    setManualLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      const cleanUrl = manualUrl.trim().replace(/\/+$/, "");
      await api.post("/repositories/register", { url: cleanUrl });
      setManualUrl("");
      setSuccessMsg("Repository registered successfully! Background cloning started.");
      fetchRegisteredRepos();
    } catch (err: any) {
      setError(err.message || "Failed to register repository.");
    } finally {
      setManualLoading(false);
    }
  };

  const handleSync = async (repoId: string, repoName: string) => {
    setSyncingId(repoId);
    setError("");
    setSuccessMsg("");
    try {
      await api.post(`/repositories/${repoId}/sync`);
      setSuccessMsg(`Metadata and issues synchronized for ${repoName}!`);
      fetchRegisteredRepos();
    } catch (err: any) {
      setError(err.message || `Failed to sync repository ${repoName}.`);
    } finally {
      setSyncingId(null);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete ${name} and clean up local workspace files?`)) return;
    try {
      await api.delete(`/repositories/${id}`);
      setSuccessMsg(`Deleted repository ${name}.`);
      fetchRegisteredRepos();
    } catch (err: any) {
      setError(err.message || "Failed to delete repository.");
    }
  };

  // Helper to check if a GitHub repo is already registered
  const isRegistered = (githubRepo: GithubRepo) => {
    return repos.some(
      (r) => r.owner.toLowerCase() === githubRepo.full_name.split("/")[0].toLowerCase() &&
             r.name.toLowerCase() === githubRepo.name.toLowerCase()
    );
  };

  // Filter GitHub repos based on search and selected type
  const filteredGithubRepos = githubRepos.filter((repo) => {
    const matchesSearch = repo.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (repo.description?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false);
    const matchesType = 
      filterType === "all" ||
      (filterType === "forks" && repo.fork) ||
      (filterType === "original" && !repo.fork);
    return matchesSearch && matchesType;
  });

  const formatDate = (dateStr: string) => {
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
    <div className="space-y-6 animate-fade-in">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Repositories</h1>
          <p className="text-gray-400 text-sm mt-1">Connect, synchronize, and manage your codebase workspaces for AI contribution runs.</p>
        </div>
        
        <div className="flex items-center gap-2">
          {activeTab === "discover" ? (
            <button
              onClick={fetchGithubRepos}
              disabled={fetchingGithub}
              className="flex items-center gap-2 text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 hover:bg-indigo-950/40 py-2.5 px-4 rounded-xl transition disabled:opacity-50"
            >
              {fetchingGithub ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              Fetch GitHub List
            </button>
          ) : (
            <button
              onClick={fetchRegisteredRepos}
              disabled={fetchingRegistered}
              className="flex items-center gap-2 text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 hover:bg-indigo-950/40 py-2.5 px-4 rounded-xl transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Status
            </button>
          )}
        </div>
      </div>

      {/* Global Alerts */}
      {error && (
        <div className="flex items-center gap-2.5 p-4 bg-red-500/10 border border-red-500/20 text-red-200 text-sm rounded-xl">
          <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {successMsg && (
        <div className="flex items-center gap-2.5 p-4 bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 text-sm rounded-xl">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Tab Selector Menu */}
      <div className="flex border-b border-gray-800/80">
        <button
          onClick={() => setActiveTab("registered")}
          className={`pb-4 px-6 font-bold text-sm transition relative ${
            activeTab === "registered" 
              ? "text-indigo-400 border-b-2 border-indigo-500" 
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          My Registered Repositories ({repos.length})
        </button>
        <button
          onClick={() => setActiveTab("discover")}
          className={`pb-4 px-6 font-bold text-sm transition relative ${
            activeTab === "discover" 
              ? "text-indigo-400 border-b-2 border-indigo-500" 
              : "text-gray-400 hover:text-gray-200"
          }`}
        >
          Discover GitHub Repositories
        </button>
      </div>

      {/* Tab Content Panels */}
      {activeTab === "registered" ? (
        <div className="space-y-6">
          {fetchingRegistered && repos.length === 0 ? (
            <div className="flex justify-center py-20">
              <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
            </div>
          ) : repos.length === 0 ? (
            <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60 max-w-2xl mx-auto mt-6">
              <GitFork className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <h3 className="text-white font-bold text-lg mb-1">No repositories registered</h3>
              <p className="text-gray-400 text-sm mb-6">You haven't connected any codebases to the AI workspace yet. Head over to the Discovery tab to fetch your repositories or use manual registration below.</p>
              <button
                onClick={() => setActiveTab("discover")}
                className="bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 px-5 rounded-xl transition"
              >
                Go to Discovery Tab
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              {repos.map((repo) => {
                const ghMeta = repo.meta_info?.github_metadata;
                return (
                  <div key={repo.id} className="glass-card p-6 rounded-2xl flex flex-col justify-between border border-gray-800/60 hover:border-indigo-500/25 hover:shadow-indigo-500/5 hover:shadow-2xl transition-all duration-300 relative overflow-hidden group">
                    <div className="space-y-4">
                      {/* Top Header */}
                      <div className="flex justify-between items-start">
                        <div className="flex items-center gap-3">
                          <div className="p-2.5 bg-indigo-500/10 rounded-xl border border-indigo-500/20">
                            <GitFork className="w-5 h-5 text-indigo-400" />
                          </div>
                          <div>
                            <h3 className="font-extrabold text-white text-lg group-hover:text-indigo-300 transition duration-200">{repo.name}</h3>
                            <span className="text-xs text-gray-500">{repo.owner}</span>
                          </div>
                        </div>
                        
                        <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                          repo.status === "cloned" 
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                            : repo.status === "cloning"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                            : repo.status === "failed"
                            ? "bg-red-500/10 text-red-400 border border-red-500/20"
                            : "bg-gray-800 text-gray-400 border border-gray-700/30"
                        }`}>
                          {repo.status}
                        </span>
                      </div>

                      {/* Description */}
                      <p className="text-sm text-gray-300 line-clamp-2 min-h-[2.5rem]">
                        {ghMeta?.description || "No description provided."}
                      </p>

                      {/* Metadata Details Grid */}
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 bg-gray-950/40 p-3.5 rounded-xl border border-gray-900/60 text-xs">
                        <div className="flex items-center gap-2 text-gray-400">
                          {ghMeta?.private ? <Lock className="w-3.5 h-3.5 text-amber-400" /> : <Globe className="w-3.5 h-3.5 text-emerald-400" />}
                          <span>{ghMeta?.private ? "Private" : "Public"}</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-400">
                          <Star className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500/20" />
                          <span>{ghMeta?.stargazers_count ?? 0} Stars</span>
                        </div>
                        <div className="flex items-center gap-2 text-gray-400">
                          <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                          <span>{ghMeta?.open_issues_count ?? 0} Issues</span>
                        </div>
                        <div className="col-span-2 md:col-span-3 h-[1px] bg-gray-900/60 my-1" />
                        <div className="text-gray-500">Branch: <span className="text-gray-300 font-semibold">{repo.branch}</span></div>
                        {repo.language && (
                          <div className="text-gray-500 col-span-2">Lang: <span className="text-gray-300 font-semibold">{repo.language}</span></div>
                        )}
                        {ghMeta?.updated_at && (
                          <div className="text-gray-500 col-span-2 md:col-span-3 flex items-center gap-1.5 mt-1">
                            <Calendar className="w-3.5 h-3.5" />
                            <span>Updated on GitHub: {formatDate(ghMeta.updated_at)}</span>
                          </div>
                        )}
                      </div>

                      {/* Quick Details (if compiled) */}
                      {repo.status === "cloned" && (
                        <div className="flex flex-wrap gap-2 pt-1">
                          {repo.framework && repo.framework !== "unknown" && (
                            <span className="text-[10px] bg-gray-900 border border-gray-800 text-indigo-300 px-2 py-0.5 rounded-md">
                              {repo.framework}
                            </span>
                          )}
                          {repo.build_system && (
                            <span className="text-[10px] bg-gray-900 border border-gray-800 text-blue-300 px-2 py-0.5 rounded-md">
                              {repo.build_system}
                            </span>
                          )}
                          {repo.clone_path && (
                            <span className="text-[10px] bg-gray-900 border border-gray-800 text-gray-400 px-2 py-0.5 rounded-md block truncate max-w-full">
                              Workspace: {repo.clone_path}
                            </span>
                          )}
                        </div>
                      )}

                      {repo.status === "cloning" && (
                        <div className="flex items-center gap-2 text-xs text-amber-400/80">
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Cloning workspace to local disk & indexing symbols...</span>
                        </div>
                      )}
                    </div>

                    {/* Bottom Actions */}
                    <div className="flex justify-between items-center pt-4 mt-6 border-t border-gray-900/60">
                      <button
                        onClick={() => handleSync(repo.id, repo.name)}
                        disabled={syncingId !== null || repo.status === "cloning"}
                        className="flex items-center gap-1.5 text-xs font-bold text-indigo-400 hover:text-indigo-300 disabled:opacity-50 transition"
                      >
                        {syncingId === repo.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <RefreshCw className="w-3.5 h-3.5" />
                        )}
                        Sync Now
                      </button>
                      
                      <button
                        onClick={() => handleDelete(repo.id, repo.name)}
                        className="text-xs font-bold text-red-400 hover:text-red-300 hover:underline transition"
                      >
                        Delete Workspace
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Manual Register Section */}
          <div className="glass-panel p-6 rounded-2xl border border-gray-800/80 mt-10">
            <h2 className="text-md font-bold text-white mb-2">Register Repository via URL</h2>
            <p className="text-xs text-gray-400 mb-4">Paste the HTTPS clone link of your GitHub repository fork to add it manually.</p>
            
            <form onSubmit={handleManualRegister} className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                placeholder="e.g., https://github.com/your-username/project-fork"
                value={manualUrl}
                onChange={(e) => setManualUrl(e.target.value)}
                disabled={manualLoading}
                className="flex-1 bg-gray-950/60 border border-gray-800/80 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-gray-200 rounded-xl py-2.5 px-4 outline-none transition text-sm"
              />
              <button
                type="submit"
                disabled={manualLoading || !manualUrl.trim()}
                className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold py-2.5 px-6 rounded-xl flex items-center justify-center gap-2 transition"
              >
                {manualLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4" />
                )}
                Register
              </button>
            </form>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* GitHub Repos discovery control panel */}
          <div className="flex flex-col sm:flex-row gap-4 justify-between items-start sm:items-center">
            {/* Search */}
            <div className="relative w-full sm:max-w-md">
              <Search className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search your GitHub repositories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-gray-950/60 border border-gray-800/80 focus:border-indigo-500 text-gray-200 rounded-xl pl-10 pr-4 py-2.5 outline-none transition text-sm"
              />
            </div>
            
            {/* Filters */}
            <div className="flex items-center gap-1.5 bg-gray-950/60 border border-gray-800/80 p-1 rounded-xl">
              <button
                onClick={() => setFilterType("all")}
                className={`text-xs font-semibold px-3.5 py-1.5 rounded-lg transition ${
                  filterType === "all" ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-gray-200"
                }`}
              >
                All
              </button>
              <button
                onClick={() => setFilterType("forks")}
                className={`text-xs font-semibold px-3.5 py-1.5 rounded-lg transition ${
                  filterType === "forks" ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Forks Only
              </button>
              <button
                onClick={() => setFilterType("original")}
                className={`text-xs font-semibold px-3.5 py-1.5 rounded-lg transition ${
                  filterType === "original" ? "bg-indigo-600 text-white" : "text-gray-400 hover:text-gray-200"
                }`}
              >
                Originals
              </button>
            </div>
          </div>

          {/* GitHub Repos list */}
          {fetchingGithub ? (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
              <span className="text-sm text-gray-400">Loading repositories from GitHub...</span>
            </div>
          ) : filteredGithubRepos.length === 0 ? (
            <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
              <Search className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <h3 className="text-white font-bold text-lg mb-1">No repositories found</h3>
              <p className="text-gray-400 text-sm max-w-sm mx-auto">Try checking your search filters or fetch the repository list again.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredGithubRepos.map((repo) => {
                const registered = isRegistered(repo);
                return (
                  <div 
                    key={repo.full_name} 
                    className={`glass-panel p-5 rounded-2xl border transition duration-200 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 ${
                      registered ? "border-gray-800/40 opacity-75" : "border-gray-850 hover:border-indigo-500/20"
                    }`}
                  >
                    <div className="space-y-2.5 flex-1 max-w-3xl">
                      {/* Name & Badge Row */}
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-extrabold text-white text-base flex items-center gap-2">
                          {repo.full_name}
                          <a href={repo.html_url} target="_blank" rel="noreferrer" className="text-gray-500 hover:text-indigo-400 transition">
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </span>
                        
                        {repo.fork && (
                          <span className="text-[10px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <GitFork className="w-2.5 h-2.5" />
                            Fork
                          </span>
                        )}
                        
                        {repo.private ? (
                          <span className="text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <Lock className="w-2.5 h-2.5" />
                            Private
                          </span>
                        ) : (
                          <span className="text-[10px] font-bold bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center gap-1">
                            <Globe className="w-2.5 h-2.5" />
                            Public
                          </span>
                        )}
                      </div>

                      {/* Description */}
                      <p className="text-sm text-gray-400 line-clamp-1">
                        {repo.description || "No description provided."}
                      </p>

                      {/* Stars & Issues & Updated */}
                      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-gray-500">
                        {repo.language && (
                          <span className="font-semibold text-gray-300">{repo.language}</span>
                        )}
                        <span className="flex items-center gap-1"><Star className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500/10" /> {repo.stargazers_count}</span>
                        <span className="flex items-center gap-1"><AlertCircle className="w-3.5 h-3.5 text-rose-400" /> {repo.open_issues_count} open issues</span>
                        <span>Updated: {formatDate(repo.updated_at)}</span>
                      </div>
                    </div>

                    {/* Action Button */}
                    <div className="w-full md:w-auto flex-shrink-0">
                      {registered ? (
                        <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-sm bg-emerald-500/5 border border-emerald-500/10 py-2 px-4 rounded-xl cursor-default">
                          <Check className="w-4 h-4" />
                          Registered
                        </div>
                      ) : (
                        <button
                          onClick={() => handleRegister(repo.clone_url, repo.name)}
                          disabled={registeringName !== null}
                          className="w-full md:w-auto bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2 px-5 rounded-xl transition flex items-center justify-center gap-1.5 shadow-lg shadow-indigo-600/15"
                        >
                          {registeringName === repo.name ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Plus className="w-3.5 h-3.5" />
                          )}
                          Register Repo
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
