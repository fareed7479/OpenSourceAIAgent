import React, { useState, useEffect } from "react";
import { Loader2, Award, Sparkles, CheckCircle2, ChevronRight, BarChart3, ShieldAlert } from "lucide-react";
import { api } from "../api/client";

interface ElusocIssue {
  id: string;
  repository_name: string;
  number: number;
  title: string;
  difficulty: string;
  score: number;
  labels: string[];
  status: string;
  assignment_status: string;
  url: string;
}

interface ElusocDashboardData {
  issues: ElusocIssue[];
  metrics: {
    total_eligible: number;
    easy_count: number;
    medium_count: number;
    hard_count: number;
    completed_prs: number;
  };
}

export const Elusoc: React.FC = () => {
  const [data, setData] = useState<ElusocDashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchDashboard = async () => {
    try {
      const resp = await api.get<ElusocDashboardData>("/intelligence/elusoc");
      setData(resp);
    } catch (err) {
      console.error("Failed to load ELUSOC details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
      </div>
    );
  }

  const metrics = data?.metrics || {
    total_eligible: 0,
    easy_count: 0,
    medium_count: 0,
    hard_count: 0,
    completed_prs: 0
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
          <Award className="w-8 h-8 text-indigo-400" />
          ELUSOC Intelligence Dashboard
        </h1>
        <p className="text-gray-400 text-sm mt-1">Track ELUSOC-eligible bounty issues, contributions metrics, and progress.</p>
      </div>

      {/* Analytics Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="glass-card p-5 rounded-2xl border border-indigo-500/10 flex items-center gap-4">
          <div className="p-3 bg-indigo-600/10 rounded-xl border border-indigo-500/20 text-indigo-400">
            <BarChart3 className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Eligible Issues</span>
            <span className="font-extrabold text-2xl text-white block">{metrics.total_eligible}</span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-emerald-500/10 flex items-center gap-4">
          <div className="p-3 bg-emerald-600/10 rounded-xl border border-emerald-500/20 text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Completed PRs</span>
            <span className="font-extrabold text-2xl text-white block">{metrics.completed_prs}</span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-amber-500/10 flex items-center gap-4">
          <div className="p-3 bg-amber-600/10 rounded-xl border border-amber-500/20 text-amber-400">
            <Sparkles className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Easy/Medium Targets</span>
            <span className="font-extrabold text-2xl text-white block">
              {metrics.easy_count + metrics.medium_count}
            </span>
          </div>
        </div>

        <div className="glass-card p-5 rounded-2xl border border-red-500/10 flex items-center gap-4">
          <div className="p-3 bg-red-600/10 rounded-xl border border-red-500/20 text-red-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <span className="text-[10px] text-gray-500 uppercase font-bold tracking-wide">Hard Obstacles</span>
            <span className="font-extrabold text-2xl text-white block">{metrics.hard_count}</span>
          </div>
        </div>
      </div>

      {/* Eligible Issues Table list */}
      <div className="glass-panel rounded-2xl border border-gray-800/80 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-800/60 bg-gray-950/40">
          <h3 className="font-bold text-white text-base">ELUSOC Bounty Targets list</h3>
          <span className="text-xs text-gray-400">Issues matching elusoc, good-first-issue, and backend labels sorted by suitability.</span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="border-b border-gray-800/60 text-gray-500 text-[10px] uppercase font-bold tracking-wider bg-gray-950/20">
                <th className="py-3 px-6">Repository</th>
                <th className="py-3 px-6">Issue Details</th>
                <th className="py-3 px-6 text-center">Difficulty</th>
                <th className="py-3 px-6 text-center">Suitability Score</th>
                <th className="py-3 px-6 text-center">Status</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800/40">
              {data?.issues.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-10 text-center text-gray-500 italic">
                    No active ELUSOC issues found. Connect repositories and trigger scans to search.
                  </td>
                </tr>
              ) : (
                data?.issues.map((issue) => (
                  <tr key={issue.id} className="hover:bg-indigo-600/[0.01] transition-all">
                    <td className="py-4 px-6 font-semibold text-white whitespace-nowrap">{issue.repository_name}</td>
                    <td className="py-4 px-6 max-w-md">
                      <div className="space-y-1">
                        <a 
                          href={issue.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="font-bold text-gray-200 hover:text-indigo-400 hover:underline transition block truncate"
                        >
                          #{issue.number} {issue.title}
                        </a>
                        <div className="flex flex-wrap gap-1">
                          {issue.labels.map(l => (
                            <span key={l} className="text-[9px] bg-gray-900 border border-gray-800 text-gray-400 px-1.5 py-0.25 rounded">
                              {l}
                            </span>
                          ))}
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-center whitespace-nowrap">
                      <span className={`text-[9px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                        issue.difficulty === "easy" 
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
                          : issue.difficulty === "medium"
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                          : "bg-red-500/10 text-red-400 border border-red-500/20"
                      }`}>
                        {issue.difficulty}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-center whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 text-[10px] font-extrabold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2 py-0.5 rounded-full">
                        <Sparkles className="w-3 h-3 animate-pulse" />
                        {issue.score}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-center whitespace-nowrap">
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        issue.assignment_status === "unassigned"
                          ? "bg-gray-800 text-gray-500"
                          : issue.assignment_status === "requested"
                          ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      }`}>
                        {issue.assignment_status}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right whitespace-nowrap">
                      <a
                        href={issue.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold transition"
                      >
                        GitHub Link
                        <ChevronRight className="w-3.5 h-3.5" />
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
