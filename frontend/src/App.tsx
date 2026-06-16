import React from "react";
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Login } from "./pages/Login";
import { AuthCallback } from "./pages/AuthCallback";
import { Dashboard } from "./pages/Dashboard";
import { Issues } from "./pages/Issues";
import { Assignments } from "./pages/Assignments";
import { Runs } from "./pages/Runs";
import { Settings } from "./pages/Settings";
import { Elusoc } from "./pages/Elusoc";
import { Intelligence } from "./pages/Intelligence";
import { AgentMonitor } from "./pages/AgentMonitor";
import { PRWorkspace } from "./pages/PRWorkspace";
import { 
  GitFork, 
  ListTodo, 
  Terminal, 
  GitPullRequest, 
  Settings as SettingsIcon, 
  LogOut, 
  Cpu, 
  User as UserIcon,
  BookOpen,
  Award,
  Brain
} from "lucide-react";

// Protected Route wrapper
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { token, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen bg-[#030712] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 border-t-2 border-indigo-500 rounded-full animate-spin" />
          <span className="text-sm text-gray-400">Loading your space...</span>
        </div>
      </div>
    );
  }
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// Main layout template wrapper
const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const navItems = [
    { name: "Repositories", path: "/", icon: GitFork },
    { name: "ELUSOC Dashboard", path: "/elusoc", icon: Award },
    { name: "Issues Discovery", path: "/issues", icon: BookOpen },
    { name: "Assignments", path: "/assignments", icon: ListTodo },
    { name: "Repository Intelligence", path: "/intelligence", icon: Brain },
    { name: "Agent Monitor", path: "/agent-monitor", icon: Cpu },
    { name: "Agent Runs", path: "/runs", icon: Terminal },
    { name: "Pull Requests", path: "/prs", icon: GitPullRequest },
    { name: "Settings", path: "/settings", icon: SettingsIcon },
  ];

  return (
    <div className="min-h-screen bg-[#030712] text-gray-200 flex flex-col md:flex-row">
      {/* Sidebar Navigation */}
      <aside className="w-full md:w-64 bg-[#0a0f1e]/80 backdrop-blur-xl border-b md:border-b-0 md:border-r border-indigo-500/10 flex flex-col justify-between p-4 md:p-6 z-10">
        <div className="space-y-8">
          {/* Logo */}
          <div className="flex items-center gap-3 px-2">
            <div className="p-2 bg-indigo-600/10 rounded-lg border border-indigo-500/20">
              <Cpu className="w-6 h-6 text-indigo-400" />
            </div>
            <div>
              <span className="font-bold text-lg text-white block">Antigravity</span>
              <span className="text-[10px] text-gray-500 tracking-wider uppercase block -mt-1 font-semibold">AI OS Contributor</span>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-200 ${
                    isActive 
                      ? "bg-indigo-600/10 text-indigo-400 border border-indigo-500/20" 
                      : "text-gray-400 hover:text-gray-200 hover:bg-gray-900/40 border border-transparent"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-indigo-400" : "text-gray-400"}`} />
                  {item.name}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* User profile details at bottom */}
        <div className="mt-8 pt-4 border-t border-gray-800/60 flex flex-col gap-3">
          {user && (
            <div className="flex items-center gap-3 px-2">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="Avatar" className="w-10 h-10 rounded-xl border border-gray-800 shadow" />
              ) : (
                <div className="w-10 h-10 rounded-xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center">
                  <UserIcon className="w-5 h-5 text-indigo-400" />
                </div>
              )}
              <div className="overflow-hidden">
                <span className="font-semibold text-sm text-white block truncate">{user.username}</span>
                <span className="text-[10px] text-indigo-400 font-semibold uppercase tracking-wide block">
                  {user.developer_mode ? "Developer Bypass" : "GitHub OAuth"}
                </span>
              </div>
            </div>
          )}
          <button
            onClick={logout}
            className="w-full flex items-center justify-center gap-2 text-xs font-semibold text-red-400 hover:text-red-300 bg-red-950/10 hover:bg-red-950/20 border border-red-500/10 hover:border-red-500/20 py-2.5 px-4 rounded-xl transition-all"
          >
            <LogOut className="w-3.5 h-3.5" />
            Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 p-6 md:p-10 overflow-y-auto max-w-7xl mx-auto w-full">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/elusoc" element={<Elusoc />} />
          <Route path="/issues" element={<Issues />} />
          <Route path="/assignments" element={<Assignments />} />
          <Route path="/intelligence" element={<Intelligence />} />
          <Route path="/agent-monitor" element={<AgentMonitor />} />
          <Route path="/runs" element={<Runs />} />
          <Route path="/prs" element={<PRWorkspace />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<LoginRedirectWrapper />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route
            path="*"
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

// Check if already authenticated and redirect away from login
const LoginRedirectWrapper: React.FC = () => {
  const { token } = useAuth();
  const location = useLocation();
  
  // Handle redirect callback token extraction from URL if any
  const queryParams = new URLSearchParams(location.search);
  const callbackToken = queryParams.get("token") || queryParams.get("access_token");
  
  if (callbackToken) {
    const username = queryParams.get("username") || "github-contributor";
    const avatar = queryParams.get("avatar_url") || "";
    const dev = queryParams.get("developer_mode") === "true";
    
    localStorage.setItem("token", callbackToken);
    localStorage.setItem(
      "user",
      JSON.stringify({ id: "gh-user", username, email: "", avatar_url: avatar, developer_mode: dev })
    );
    return <Navigate to="/" replace />;
  }

  if (token) {
    return <Navigate to="/" replace />;
  }
  
  return <Login />;
};

export default App;
