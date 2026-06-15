import React, { useState } from "react";
import { Cpu, ArrowRight } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export const Login: React.FC = () => {
  const { login } = useAuth();
  const [mockUser, setMockUser] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleGitHubLogin = () => {
    // Redirect to backend authorize endpoint
    window.location.href = "http://localhost:8000/api/v1/auth/login";
  };

  const handleMockLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!mockUser.trim()) return;
    
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/auth/callback?mock_username=${encodeURIComponent(mockUser)}`
      );
      if (!response.ok) {
        throw new Error("Mock authentication failed");
      }
      const data = await response.json();
      login(data.access_token, data.user);
    } catch (err: any) {
      setError(err.message || "Failed to log in.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen cyber-grid flex items-center justify-center px-4">
      <div className="w-full max-w-md glass-panel p-8 rounded-2xl border border-indigo-500/20 shadow-2xl relative overflow-hidden">
        {/* Glow overlay */}
        <div className="absolute -top-20 -left-20 w-40 h-40 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -right-20 w-40 h-40 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col items-center text-center mb-8">
          <div className="p-3 bg-indigo-600/10 rounded-xl border border-indigo-500/20 mb-4 animate-pulse-glow">
            <Cpu className="w-10 h-10 text-indigo-400" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight gradient-text mb-2">
            Antigravity OS Agent
          </h1>
          <p className="text-sm text-gray-400 max-w-xs">
            Automate your open-source contributions with AI orchestration
          </p>
        </div>

        {error && (
          <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-200 text-xs rounded-lg mb-6 text-center">
            {error}
          </div>
        )}

        <div className="space-y-6">
          <button
            onClick={handleGitHubLogin}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-100 text-gray-900 font-semibold py-3 px-4 rounded-xl shadow-lg transition-all duration-200 hover:scale-[1.02]"
          >
            <svg className="w-5 h-5 text-gray-900 fill-current" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
            </svg>
            Sign in with GitHub
          </button>

          <div className="relative flex items-center justify-center my-6">
            <div className="border-t border-gray-800 w-full" />
            <span className="absolute bg-[#030712] px-3 text-xs text-gray-500 font-medium uppercase tracking-wider">
              Or developer bypass
            </span>
          </div>

          <form onSubmit={handleMockLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
                Mock Username
              </label>
              <input
                type="text"
                placeholder="e.g., test-contributor"
                value={mockUser}
                onChange={(e) => setMockUser(e.target.value)}
                disabled={loading}
                className="w-full bg-gray-900/60 border border-gray-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-gray-200 rounded-xl py-3 px-4 outline-none transition-all text-sm"
              />
            </div>
            <button
              type="submit"
              disabled={loading || !mockUser.trim()}
              className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold py-3 px-4 rounded-xl shadow-indigo-600/20 shadow-md transition-all duration-200 hover:scale-[1.02]"
            >
              {loading ? "Authenticating..." : "Developer Login"}
              {!loading && <ArrowRight className="w-4 h-4" />}
            </button>
          </form>
        </div>

        <div className="mt-8 text-center">
          <span className="text-[10px] text-gray-600 uppercase tracking-widest">
            Production-Ready AI Agent Platform
          </span>
        </div>
      </div>
    </div>
  );
};
