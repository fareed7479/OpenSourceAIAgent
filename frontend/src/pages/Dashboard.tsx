import React, { useState, useEffect } from "react";
import { Plus, RefreshCw, AlertCircle, CheckCircle2, Loader2, GitFork } from "lucide-react";
import { api } from "../api/client";

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
  created_at: string;
}

export const Dashboard: React.FC = () => {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const fetchRepos = async () => {
    try {
      const data = await api.get<Repository[]>("/repositories");
      setRepos(data);
    } catch (err: any) {
      console.error("Failed to load repositories:", err);
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    fetchRepos();
    // Poll repositories status every 4 seconds in case they are cloning
    const interval = setInterval(fetchRepos, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      await api.post("/repositories/register", { url });
      setUrl("");
      setSuccessMsg("Repository registered! Local workspace setup started in the background.");
      fetchRepos();
    } catch (err: any) {
      setError(err.message || "Failed to register repository.");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this repository and clean up local files?")) return;
    try {
      await api.delete(`/repositories/${id}`);
      fetchRepos();
    } catch (err: any) {
      setError(err.message || "Failed to delete repository.");
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white">Repositories</h1>
          <p className="text-gray-400 text-sm mt-1">Connect and manage your target forks for AI contribution runs.</p>
        </div>
        
        <button
          onClick={fetchRepos}
          className="flex items-center gap-2 text-xs font-semibold text-indigo-400 bg-indigo-950/20 border border-indigo-500/20 hover:bg-indigo-950/40 py-2.5 px-4 rounded-xl transition"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh Status
        </button>
      </div>

      {/* Register Repository Form */}
      <div className="glass-panel p-6 rounded-2xl border border-indigo-500/10 shadow-lg relative overflow-hidden">
        <h2 className="text-lg font-bold text-white mb-3">Register New Fork</h2>
        <p className="text-xs text-gray-400 mb-4">Paste the HTTPS link of your GitHub repository fork to clone and index it.</p>
        
        <form onSubmit={handleRegister} className="flex flex-col sm:flex-row gap-3">
          <input
            type="text"
            placeholder="e.g., https://github.com/your-username/project-fork"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            disabled={loading}
            className="flex-1 bg-gray-950/60 border border-gray-800/80 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-gray-200 rounded-xl py-3 px-4 outline-none transition text-sm"
          />
          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold py-3 px-6 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/15 hover:scale-[1.01] active:scale-[0.99] transition duration-150"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Plus className="w-4 h-4" />
            )}
            Register Repository
          </button>
        </form>

        {error && (
          <div className="mt-4 flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/20 text-red-200 text-xs rounded-xl">
            <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {successMsg && (
          <div className="mt-4 flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 text-xs rounded-xl">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}
      </div>

      {/* Repositories List Grid */}
      {fetching ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        </div>
      ) : repos.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
          <GitFork className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No repositories registered</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto mb-6">Register a repository fork above to start analyzing source code and discovering issues.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {repos.map((repo) => (
            <div key={repo.id} className="glass-card p-6 rounded-2xl flex flex-col justify-between h-56 relative overflow-hidden group">
              <div>
                <div className="flex justify-between items-start mb-4">
                  <div className="flex items-center gap-2.5">
                    <GitFork className="w-5 h-5 text-indigo-400" />
                    <div>
                      <h3 className="font-bold text-white group-hover:text-indigo-300 transition duration-200 truncate max-w-xs">{repo.name}</h3>
                      <span className="text-[10px] text-gray-500 block truncate max-w-xs">{repo.owner}</span>
                    </div>
                  </div>
                  
                  {/* Status Indicator Badge */}
                  <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full uppercase tracking-wider ${
                    repo.status === "cloned" 
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                      : repo.status === "cloning"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse"
                      : repo.status === "failed"
                      ? "bg-red-500/10 text-red-400 border border-red-500/20"
                      : "bg-gray-800 text-gray-400"
                  }`}>
                    {repo.status}
                  </span>
                </div>

                <div className="space-y-2 mb-4">
                  <p className="text-xs text-gray-400 truncate"><span className="text-gray-500">URL:</span> {repo.url}</p>
                  
                  {repo.status === "cloned" && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {repo.language && (
                        <span className="text-[10px] bg-gray-900 border border-gray-800 text-gray-300 px-2 py-0.5 rounded-md">
                          {repo.language}
                        </span>
                      )}
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
                    </div>
                  )}
                  
                  {repo.status === "cloning" && (
                    <div className="flex items-center gap-2 text-xs text-amber-400/80 pt-1">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Cloning workspace to disk...</span>
                    </div>
                  )}
                  
                  {repo.status === "failed" && (
                    <span className="text-[10px] text-red-400 block">Workspace build failed. Check GitHub access token permissions.</span>
                  )}
                </div>
              </div>

              <div className="flex justify-between items-center pt-4 border-t border-gray-800/40">
                <span className="text-[10px] text-gray-600">Default branch: {repo.branch}</span>
                <button
                  onClick={() => handleDelete(repo.id)}
                  className="text-xs font-semibold text-red-400 hover:text-red-300 hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
