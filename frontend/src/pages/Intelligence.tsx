import React, { useState, useEffect } from "react";
import { 
  Loader2, 
  Search, 
  Brain, 
  Code, 
  FileCode, 
  Sparkles, 
  Cpu, 
  Binary, 
  Network, 
  History, 
  Workflow, 
  Folder, 
  Layers, 
  Plus, 
  Save 
} from "lucide-react";
import { api } from "../api/client";

interface Repository {
  id: string;
  owner: string;
  name: string;
}

interface SymbolMapping {
  name: string;
  type: string;
  lines: string;
}

interface FileCodebaseMap {
  filepath: string;
  symbols: SymbolMapping[];
}

interface RepoIntelligenceData {
  repository_id: string;
  files_count: number;
  symbols_count: number;
  codebase_map: FileCodebaseMap[];
}

interface SearchResult {
  filepath: string;
  symbol?: string;
  content: string;
  similarity: number;
}

interface MemoryRecord {
  id: string;
  key: string;
  value: string;
  memory_type: string;
  created_at: string;
}

interface DependencyRelation {
  id: string;
  source_file: string;
  target_file: string;
  relation_type: string;
}

// Recursive Directory Tree Component
const DirectoryTree: React.FC<{ node: any; depth?: number }> = ({ node, depth = 0 }) => {
  const [isOpen, setIsOpen] = useState(depth < 2);
  
  if (!node) return null;
  const isDir = node.type === "directory";
  
  return (
    <div className="select-none font-mono text-xs">
      <div 
        onClick={() => isDir && setIsOpen(!isOpen)}
        className={`flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-900/60 cursor-pointer ${isDir ? 'text-indigo-400 font-semibold' : 'text-gray-400'}`}
        style={{ paddingLeft: `${depth * 14 + 8}px` }}
      >
        {isDir ? (
          <>
            <span className="text-[8px] text-gray-500 w-2.5 text-center">{isOpen ? "▼" : "▶"}</span>
            <Folder className="w-3.5 h-3.5 text-indigo-400/80 fill-indigo-400/10" />
            <span className="truncate text-gray-305">{node.name}</span>
          </>
        ) : (
          <>
            <span className="w-2.5" />
            <FileCode className="w-3.5 h-3.5 text-indigo-400/60" />
            <span className="truncate text-gray-400">{node.name}</span>
          </>
        )}
      </div>
      
      {isDir && isOpen && node.children && (
        <div className="space-y-0.5 mt-0.5 border-l border-gray-900/40 ml-2">
          {node.children.map((child: any, idx: number) => (
            <DirectoryTree key={idx} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export const Intelligence: React.FC = () => {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  
  // Tab control state
  const [activeTab, setActiveTab] = useState<"overview" | "architecture" | "symbols" | "dependencies" | "search" | "memory">("overview");

  // Intelligence states
  const [intelData, setIntelData] = useState<RepoIntelligenceData | null>(null);
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [dependencies, setDependencies] = useState<DependencyRelation[]>([]);
  const [repoStats, setRepoStats] = useState<any | null>(null);
  const [loadingIntel, setLoadingIntel] = useState(false);

  // Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

  // Manual Memory Creation form states
  const [newMemoryKey, setNewMemoryKey] = useState("");
  const [newMemoryValue, setNewMemoryValue] = useState("");
  const [newMemoryType, setNewMemoryType] = useState("convention");
  const [savingMemory, setSavingMemory] = useState(false);

  // AST Map Search filter
  const [astFilter, setAstFilter] = useState("");

  // Load repositories on mount
  useEffect(() => {
    const loadRepos = async () => {
      try {
        const data = await api.get<Repository[]>("/repositories");
        setRepos(data);
        if (data.length > 0) {
          setSelectedRepo(data[0].id);
        }
      } catch (err) {
        console.error("Failed to load repositories:", err);
      }
    };
    loadRepos();
  }, []);

  // Fetch intelligence data when selected repository changes
  const fetchIntel = async () => {
    if (!selectedRepo) return;
    setLoadingIntel(true);
    setSearchResults([]);
    setSearchQuery("");
    setAstFilter("");
    try {
      const symbolsResp = await api.get<RepoIntelligenceData>(`/intelligence/repo/${selectedRepo}/symbols`);
      setIntelData(symbolsResp);

      const memoryResp = await api.get<MemoryRecord[]>(`/intelligence/repo/${selectedRepo}/memory`);
      setMemories(memoryResp);

      const statsResp = await api.get<any>(`/repositories/${selectedRepo}/intelligence`);
      setRepoStats(statsResp);

      const depsResp = await api.get<DependencyRelation[]>(`/intelligence/repo/${selectedRepo}/dependencies`);
      setDependencies(depsResp);
    } catch (err) {
      console.error("Failed to load intelligence maps:", err);
      setIntelData(null);
      setMemories([]);
      setRepoStats(null);
      setDependencies([]);
    } finally {
      setLoadingIntel(false);
    }
  };

  useEffect(() => {
    fetchIntel();
  }, [selectedRepo]);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRepo || !searchQuery.trim()) return;

    setSearching(true);
    try {
      const resp = await api.get<SearchResult[]>(
        `/intelligence/repo/${selectedRepo}/search?query=${encodeURIComponent(searchQuery)}`
      );
      setSearchResults(resp);
    } catch (err) {
      console.error("Semantic search failed:", err);
      alert("Semantic search execution failed.");
    } finally {
      setSearching(false);
    }
  };

  const handleAddMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMemoryKey.trim() || !newMemoryValue.trim()) return;

    setSavingMemory(true);
    try {
      await api.post(`/intelligence/repo/${selectedRepo}/memory`, {
        key: newMemoryKey,
        value: newMemoryValue,
        memory_type: newMemoryType
      });
      // reload memories
      const memoryResp = await api.get<MemoryRecord[]>(`/intelligence/repo/${selectedRepo}/memory`);
      setMemories(memoryResp);
      setNewMemoryKey("");
      setNewMemoryValue("");
      alert("Repository memory saved successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to save memory.");
    } finally {
      setSavingMemory(false);
    }
  };

  // Filter AST Codebase mapping list
  const filteredAstMap = intelData?.codebase_map.filter(fileMap => 
    fileMap.filepath.toLowerCase().includes(astFilter.toLowerCase()) ||
    fileMap.symbols.some(s => s.name.toLowerCase().includes(astFilter.toLowerCase()))
  ) || [];

  return (
    <div className="space-y-8 animate-fade-in max-w-none">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-gray-900 pb-5">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
            <Brain className="w-8 h-8 text-indigo-400" />
            Repository Intelligence Cockpit
          </h1>
          <p className="text-gray-400 text-sm mt-1">Explore AST symbols, semantic structures, dependency networks, and architectural conventions.</p>
        </div>
        
        {/* Repo selector dropdown */}
        <div className="w-64 space-y-1">
          <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Active Workspace</label>
          <select
            value={selectedRepo}
            onChange={(e) => setSelectedRepo(e.target.value)}
            className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-2.5 px-3 outline-none text-sm font-semibold"
          >
            <option value="" disabled>Select Repository</option>
            {repos.map((r) => (
              <option key={r.id} value={r.id}>{r.owner}/{r.name}</option>
            ))}
          </select>
        </div>
      </div>

      {!selectedRepo ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-gray-800/60">
          <Brain className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-white font-bold text-lg mb-1">No repository selected</h3>
          <p className="text-gray-400 text-sm max-w-sm mx-auto">Register and select a repository fork to index symbols and view knowledge base files.</p>
        </div>
      ) : loadingIntel ? (
        <div className="flex justify-center py-24">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
            <span className="text-sm text-gray-400">Scanning repository modules & relations...</span>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Repository Health Overview Stats Panel */}
          {repoStats && (
            <div className="bg-[#0b0f19]/80 border border-gray-850/80 p-5 rounded-2xl shadow-2xl relative overflow-hidden space-y-5">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-gray-900/60 pb-3">
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <Workflow className="w-4 h-4 text-indigo-400 animate-pulse" />
                    Repository Health Profile
                  </h2>
                </div>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 bg-emerald-950/20 text-emerald-400 border border-emerald-500/20 px-3 py-0.5 rounded-full text-xs font-bold">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    {repoStats.index_status || "synced"}
                  </div>
                  {repoStats.last_sync && (
                    <span className="text-[10px] text-gray-500 font-mono">Indexed: {new Date(repoStats.last_sync).toLocaleString()}</span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                {[
                  { label: "Framework", val: repoStats.framework || "unknown", desc: repoStats.language || "unknown", icon: Cpu, color: "text-indigo-400 bg-indigo-950/30 border-indigo-500/10" },
                  { label: "Indexed Files", val: repoStats.indexed_files, desc: "Source files analyzed", icon: FileCode, color: "text-blue-400 bg-blue-950/30 border-blue-500/10" },
                  { label: "Extracted Symbols", val: repoStats.indexed_symbols, desc: "Classes, methods, routes", icon: Code, color: "text-purple-400 bg-purple-950/30 border-purple-500/10" },
                  { label: "Vector Chunks", val: repoStats.vector_chunks, desc: "Semantic embeds", icon: Binary, color: "text-pink-400 bg-pink-950/30 border-pink-500/10" },
                  { label: "KG Network", val: `${repoStats.kg_nodes} Nodes`, desc: `${repoStats.kg_edges} Relations`, icon: Network, color: "text-cyan-400 bg-cyan-950/30 border-cyan-500/10" },
                  { label: "Tests & Fixes", val: `${repoStats.tests_discovered} Tests`, desc: `${repoStats.historical_fixes} Past Fixes`, icon: History, color: "text-emerald-400 bg-emerald-950/30 border-emerald-500/10" },
                ].map((stat, idx) => {
                  const Icon = stat.icon;
                  return (
                    <div key={idx} className={`p-4 rounded-xl border flex flex-col justify-between ${stat.color} transition duration-200 hover:scale-[1.02]`}>
                      <div className="flex justify-between items-start mb-2">
                        <span className="text-[9px] uppercase font-bold tracking-wider opacity-85">{stat.label}</span>
                        <Icon className="w-3.5 h-3.5 opacity-80" />
                      </div>
                      <div>
                        <h4 className="text-lg font-black tracking-tight text-white mb-0.5">{stat.val}</h4>
                        <span className="text-[10px] opacity-60 block truncate">{stat.desc}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Navigation Tabs */}
          <div className="flex border-b border-gray-900 gap-1 overflow-x-auto pb-px">
            {[
              { id: "overview", label: "Overview & Health", icon: Cpu },
              { id: "architecture", label: "Architecture Mappings", icon: Layers },
              { id: "symbols", label: "AST Symbol Map", icon: Code },
              { id: "dependencies", label: "Dependency Network", icon: Network },
              { id: "search", label: "Semantic Search", icon: Search },
              { id: "memory", label: "Repository Memory", icon: Brain }
            ].map(tab => {
              const TabIcon = tab.icon;
              const isTabActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold border-b-2 whitespace-nowrap transition-all duration-200 ${
                    isTabActive 
                      ? "border-indigo-500 text-indigo-400 bg-indigo-950/10" 
                      : "border-transparent text-gray-500 hover:text-gray-300 hover:bg-gray-900/10"
                  }`}
                >
                  <TabIcon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Tab Contents */}
          <div className="space-y-6">

            {/* TAB 1: OVERVIEW & HEALTH */}
            {activeTab === "overview" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                
                {/* Left Columns (Col Span 2): Core Files, Env configs and Directory Tree */}
                <div className="lg:col-span-2 space-y-6">
                  {/* File & Environment Overview */}
                  <div className="glass-panel p-5 rounded-2xl border border-gray-800 space-y-4">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-900 pb-2">
                      <FileCode className="w-4 h-4 text-indigo-400" />
                      Configuration & Entry points
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                      <div className="space-y-1.5 p-3.5 bg-gray-950/40 border border-gray-850 rounded-xl">
                        <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Entry Points Detected</span>
                        {repoStats?.entry_points && repoStats.entry_points.length > 0 ? (
                          <div className="space-y-1">
                            {repoStats.entry_points.map((ep: string, index: number) => (
                              <div key={index} className="font-mono text-indigo-300 truncate">⚡ {ep}</div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-gray-500 italic">No entry point files detected.</div>
                        )}
                      </div>

                      <div className="space-y-1.5 p-3.5 bg-gray-950/40 border border-gray-850 rounded-xl">
                        <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Package Lock files</span>
                        {repoStats?.lock_files && repoStats.lock_files.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5">
                            {repoStats.lock_files.map((lf: string, index: number) => (
                              <span key={index} className="bg-blue-950/20 border border-blue-500/20 text-blue-400 px-2 py-0.5 rounded text-[10px] font-semibold">{lf}</span>
                            ))}
                          </div>
                        ) : (
                          <div className="text-gray-500 italic">No package manager lock files found.</div>
                        )}
                      </div>

                      <div className="space-y-1.5 p-3.5 bg-gray-950/40 border border-gray-850 rounded-xl">
                        <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">Environment config templates</span>
                        {repoStats?.env_files && repoStats.env_files.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5">
                            {repoStats.env_files.map((ef: string, index: number) => (
                              <span key={index} className="bg-purple-950/20 border border-purple-500/20 text-purple-400 px-2 py-0.5 rounded text-[10px] font-semibold">{ef}</span>
                            ))}
                          </div>
                        ) : (
                          <div className="text-gray-500 italic">No environment .env templates found.</div>
                        )}
                      </div>

                      <div className="space-y-1.5 p-3.5 bg-gray-950/40 border border-gray-850 rounded-xl">
                        <span className="text-[10px] uppercase font-bold text-gray-500 tracking-wider">CI/CD workflows</span>
                        {repoStats?.cicd_configs && repoStats.cicd_configs.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5">
                            {repoStats.cicd_configs.map((cc: string, index: number) => (
                              <span key={index} className="bg-pink-950/20 border border-pink-500/20 text-pink-400 px-2 py-0.5 rounded text-[10px] font-semibold">{cc}</span>
                            ))}
                          </div>
                        ) : (
                          <div className="text-gray-500 italic">No CI/CD configuration files found.</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Codebase Indented Tree structure */}
                  <div className="glass-panel p-5 rounded-2xl border border-gray-800 space-y-4">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-900 pb-2">
                      <Folder className="w-4 h-4 text-indigo-400" />
                      Interactive Directory Hierarchy Structure
                    </h3>
                    
                    {repoStats?.directory_structure ? (
                      <div className="p-4 bg-gray-950/40 border border-gray-850 rounded-xl max-h-[360px] overflow-y-auto pr-2">
                        <DirectoryTree node={repoStats.directory_structure} />
                      </div>
                    ) : (
                      <div className="p-8 text-center text-gray-500 italic text-xs">Directory map structure unavailable.</div>
                    )}
                  </div>
                </div>

                {/* Right Column: High-level overview info */}
                <div className="lg:col-span-1 space-y-6">
                  <div className="glass-panel p-5 rounded-2xl border border-gray-800 space-y-4">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-900 pb-2">
                      <Cpu className="w-4 h-4 text-indigo-400" />
                      Workspace Pattern
                    </h3>
                    <div className="space-y-4 text-xs">
                      <div>
                        <span className="text-[10px] text-gray-500 uppercase font-semibold">Active Architecture</span>
                        <div className="text-base font-extrabold text-white mt-0.5">{repoStats?.architecture || "Monolithic Layout"}</div>
                      </div>
                      
                      <div className="p-3.5 bg-indigo-950/15 border border-indigo-500/10 rounded-xl">
                        <span className="font-bold text-indigo-400 block mb-1">🔍 Automatic Classification</span>
                        <p className="text-gray-400 leading-relaxed">
                          Antigravity parses your files and folders to infer your project layer layout. This determines the orchestration flow of code modifications.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

              </div>
            )}

            {/* TAB 2: ARCHITECTURE COMPONENTS */}
            {activeTab === "architecture" && (
              <div className="space-y-6">
                <div className="glass-panel p-5 rounded-2xl border border-gray-850 space-y-1">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Layers className="w-4 h-4 text-indigo-400" />
                    Layered Architecture Components Mappings
                  </h3>
                  <p className="text-xs text-gray-400">Extracted modules matching MVC, Clean Architecture, or standard layered component filters.</p>
                </div>

                {repoStats?.components ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[
                      { key: "controllers", label: "Controllers & Routers", desc: "API handlers, HTTP routes, controllers" },
                      { key: "services", label: "Services & Handlers", desc: "Core business logic layers" },
                      { key: "repositories", label: "Repositories & DAOs", desc: "Database queries, data operations" },
                      { key: "models", label: "Models & Schemas", desc: "Entity models, serialize schemas" },
                      { key: "utilities", label: "Utilities & Helpers", desc: "Helper functions, static common utilities" },
                      { key: "middlewares", label: "Middlewares & Guards", desc: "Authorization, guards, interception layers" }
                    ].map(comp => {
                      const filesList = repoStats.components[comp.key] || [];
                      return (
                        <div key={comp.key} className="glass-panel p-4.5 rounded-2xl border border-gray-850 flex flex-col justify-between h-[280px]">
                          <div>
                            <div className="flex justify-between items-center mb-1">
                              <h4 className="font-bold text-white text-sm">{comp.label}</h4>
                              <span className="text-[10px] font-bold bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full border border-indigo-500/10">
                                {filesList.length} files
                              </span>
                            </div>
                            <p className="text-[10px] text-gray-500 mb-3">{comp.desc}</p>
                            
                            <div className="space-y-1.5 overflow-y-auto max-h-[160px] pr-1">
                              {filesList.length > 0 ? (
                                filesList.map((f: string, idx: number) => (
                                  <div key={idx} className="font-mono text-[10px] text-gray-400 p-1.5 bg-gray-950/40 border border-gray-900 rounded truncate" title={f}>
                                    📄 {f}
                                  </div>
                                ))
                              ) : (
                                <div className="text-[10px] text-gray-600 italic p-2 text-center bg-gray-950/20 border border-dashed border-gray-900 rounded">No components detected.</div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="p-12 text-center bg-[#0b0f19]/40 border border-gray-850 rounded-2xl text-gray-500 italic text-sm">
                    No components mappings extracted for this codebase.
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: AST SYMBOL MAP */}
            {activeTab === "symbols" && (
              <div className="glass-panel p-6 rounded-2xl border border-gray-850 space-y-4">
                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-gray-900/60 pb-3">
                  <div>
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Code className="w-4 h-4 text-indigo-400" />
                      AST Codebase Symbol Mapping
                    </h3>
                  </div>
                  
                  {/* Local filter input */}
                  <div className="w-72">
                    <input
                      type="text"
                      placeholder="Filter files or symbol names..."
                      value={astFilter}
                      onChange={(e) => setAstFilter(e.target.value)}
                      className="w-full bg-gray-950/60 border border-gray-850 text-gray-300 rounded-xl py-1.5 px-3 outline-none text-xs"
                    />
                  </div>
                </div>

                {filteredAstMap.length === 0 ? (
                  <div className="p-8 text-center text-gray-500 italic text-sm">
                    No symbols matching filter found.
                  </div>
                ) : (
                  <div className="space-y-3 max-h-[460px] overflow-y-auto pr-2">
                    {filteredAstMap.map((fileMap) => (
                      <div key={fileMap.filepath} className="border border-gray-850/80 rounded-xl overflow-hidden bg-gray-950/25">
                        <div className="bg-gray-950/60 px-4 py-2.5 border-b border-gray-850/60 flex items-center justify-between">
                          <span className="text-xs font-bold text-gray-300 flex items-center gap-2">
                            <FileCode className="w-4 h-4 text-indigo-400" />
                            {fileMap.filepath}
                          </span>
                          <span className="text-[9px] text-gray-500 font-mono">
                            {fileMap.symbols.length} symbols
                          </span>
                        </div>
                        
                        <div className="p-2.5 divide-y divide-gray-900/40">
                          {fileMap.symbols.length === 0 ? (
                            <div className="text-[10px] text-gray-500 italic py-1 px-1">No classes or functions detected in file.</div>
                          ) : (
                            fileMap.symbols.map((sym, sIdx) => (
                              <div key={sIdx} className="flex justify-between items-center py-2 px-1 text-xs hover:bg-gray-900/20 rounded transition">
                                <span className="font-semibold text-gray-200 flex items-center gap-2">
                                  <span className={`w-2 h-2 rounded-full ${
                                    sym.type === "class" ? "bg-purple-400" :
                                    sym.type === "interface" ? "bg-pink-400" :
                                    sym.type === "route" ? "bg-orange-400" :
                                    sym.type === "api_handler" ? "bg-emerald-400" : "bg-blue-400"
                                  }`} />
                                  {sym.name}
                                </span>
                                <div className="flex items-center gap-3 text-[10px] text-gray-500">
                                  <span className="bg-gray-900 px-2 py-0.5 rounded text-gray-400 capitalize">{sym.type}</span>
                                  <span>Lines: {sym.lines}</span>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: DEPENDENCY GRAPH */}
            {activeTab === "dependencies" && (
              <div className="glass-panel p-6 rounded-2xl border border-gray-850 space-y-4">
                <div>
                  <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-900 pb-2">
                    <Network className="w-4 h-4 text-indigo-400" />
                    Codebase Dependency Network Mappings
                  </h3>
                  <p className="text-xs text-gray-400 mt-1">Direct relationships extracted from module imports and function/method call graph tracings.</p>
                </div>

                {dependencies.length === 0 ? (
                  <div className="p-12 text-center bg-gray-950/20 border border-gray-900 rounded-xl text-gray-500 italic text-xs">
                    No dependency relations indexed. Register symbols and trigger a file scan.
                  </div>
                ) : (
                  <div className="border border-gray-850 rounded-xl overflow-hidden max-h-[440px] overflow-y-auto pr-2">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-gray-950 border-b border-gray-850 text-gray-400 font-bold uppercase tracking-wider text-[9px]">
                          <th className="p-3">Source Node</th>
                          <th className="p-3">Relationship</th>
                          <th className="p-3">Target Node</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-900">
                        {dependencies.map((dep) => (
                          <tr key={dep.id} className="hover:bg-gray-900/10 font-mono text-[11px]">
                            <td className="p-3 text-indigo-300 truncate max-w-xs" title={dep.source_file}>
                              {dep.source_file}
                            </td>
                            <td className="p-3">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                dep.relation_type === "imports" 
                                  ? "bg-blue-950/20 text-blue-400 border border-blue-500/10" 
                                  : "bg-purple-950/20 text-purple-400 border border-purple-500/10"
                              }`}>
                                {dep.relation_type.toUpperCase()}
                              </span>
                            </td>
                            <td className="p-3 text-gray-300 truncate max-w-xs" title={dep.target_file}>
                              {dep.target_file}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {/* TAB 5: SEMANTIC SEARCH */}
            {activeTab === "search" && (
              <div className="glass-panel p-6 rounded-2xl border border-indigo-500/10 shadow-lg relative overflow-hidden space-y-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-indigo-400 animate-pulse" />
                  <h2 className="text-base font-bold text-white">Semantic Code Search</h2>
                </div>
                <p className="text-xs text-gray-400">Query your codebase in natural language (e.g. "token verification auth") to find semantic symbol contexts.</p>
                
                <form onSubmit={handleSearch} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Ask something about the codebase..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="flex-1 bg-gray-950/60 border border-gray-800 focus:border-indigo-500 text-gray-200 rounded-xl py-3 px-4 outline-none text-sm"
                  />
                  <button
                    type="submit"
                    disabled={searching || !searchQuery.trim()}
                    className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold py-3 px-6 rounded-xl flex items-center justify-center gap-2 transition"
                  >
                    {searching ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Search className="w-4 h-4" />
                    )}
                    Search
                  </button>
                </form>

                {searchResults.length > 0 && (
                  <div className="space-y-4 pt-4 border-t border-gray-900/60">
                    <h3 className="text-xs font-bold text-gray-400 uppercase tracking-widest">Similarity Search Matches</h3>
                    <div className="space-y-3 max-h-[300px] overflow-y-auto pr-2">
                      {searchResults.map((res, index) => (
                        <div key={index} className="p-4 bg-gray-950/60 border border-gray-850 rounded-xl space-y-2">
                          <div className="flex justify-between items-center text-[10px] text-gray-400">
                            <span className="font-semibold text-gray-300 flex items-center gap-1.5">
                              <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                              {res.filepath} {res.symbol && `• Symbol: ${res.symbol}`}
                            </span>
                            <span className="bg-indigo-500/10 text-indigo-400 px-2 py-0.5 rounded-full border border-indigo-500/10 font-bold">
                              Match: {Math.round(res.similarity * 100)}%
                            </span>
                          </div>
                          <pre className="p-3 bg-black/40 border border-gray-900/60 rounded-lg text-[10px] text-gray-400 overflow-x-auto max-h-24 font-mono whitespace-pre-wrap">
                            {res.content}
                          </pre>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 6: REPOSITORY MEMORY */}
            {activeTab === "memory" && (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
                
                {/* Left Columns (Col Span 2): Memories list */}
                <div className="lg:col-span-2 space-y-6">
                  <div className="glass-panel p-6 rounded-2xl border border-gray-850 space-y-4">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-900 pb-2">
                      <Brain className="w-4 h-4 text-indigo-400" />
                      Repository Knowledge Memory
                    </h3>
                    
                    {memories.length === 0 ? (
                      <div className="p-8 text-center bg-gray-950/40 border border-gray-900 rounded-xl text-gray-500 italic text-xs">
                        No memories cached yet. Successful agent runs compile memory patterns.
                      </div>
                    ) : (
                      <div className="space-y-3 max-h-[460px] overflow-y-auto pr-1">
                        {memories.map((m) => (
                          <div key={m.id} className="p-3.5 bg-gray-950/60 border border-gray-850 rounded-xl space-y-1.5 relative group">
                            <div className="flex justify-between items-center text-[9px] uppercase font-bold tracking-wider">
                              <span className={`px-2 py-0.5 rounded ${
                                m.memory_type === "past_fix" ? "bg-emerald-950/40 text-emerald-400 border border-emerald-500/10" :
                                m.memory_type === "convention" ? "bg-indigo-950/40 text-indigo-400 border border-indigo-500/10" :
                                "bg-purple-950/40 text-purple-400 border border-purple-500/10"
                              }`}>
                                {m.memory_type}
                              </span>
                              <span className="text-gray-500">{new Date(m.created_at).toLocaleDateString()}</span>
                            </div>
                            <h4 className="font-bold text-white text-xs">{m.key}</h4>
                            <p className="text-[10px] text-gray-400 leading-relaxed font-mono whitespace-pre-wrap">{m.value}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Column: Register New Memory Form */}
                <div className="lg:col-span-1">
                  <div className="glass-panel p-5 rounded-2xl border border-gray-850 space-y-4">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2 border-b border-gray-900 pb-2">
                      <Plus className="w-4 h-4 text-indigo-400" />
                      Register Memory
                    </h3>
                    
                    <form onSubmit={handleAddMemory} className="space-y-4 text-xs">
                      <div className="space-y-1">
                        <label className="text-[10px] text-gray-400 uppercase font-semibold">Memory Type</label>
                        <select
                          value={newMemoryType}
                          onChange={(e) => setNewMemoryType(e.target.value)}
                          className="w-full bg-gray-950 border border-gray-850 text-gray-300 rounded-xl py-2 px-3 outline-none"
                        >
                          <option value="convention">Convention (Naming, Folders)</option>
                          <option value="style">Style (Coding syntax guidelines)</option>
                          <option value="preference">Preference (Build, Lint tools)</option>
                          <option value="past_fix">Past Fix (Fix references)</option>
                        </select>
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] text-gray-400 uppercase font-semibold">Key/Identifier</label>
                        <input
                          type="text"
                          placeholder="e.g. naming_camel_case"
                          value={newMemoryKey}
                          onChange={(e) => setNewMemoryKey(e.target.value)}
                          required
                          className="w-full bg-gray-950 border border-gray-850 text-gray-200 rounded-xl py-2 px-3 outline-none"
                        />
                      </div>

                      <div className="space-y-1">
                        <label className="text-[10px] text-gray-400 uppercase font-semibold">Description / Value</label>
                        <textarea
                          placeholder="Provide details about the convention or preference..."
                          value={newMemoryValue}
                          onChange={(e) => setNewMemoryValue(e.target.value)}
                          required
                          rows={4}
                          className="w-full bg-gray-950 border border-gray-850 text-gray-200 rounded-xl py-2 px-3 outline-none resize-none font-mono"
                        />
                      </div>

                      <button
                        type="submit"
                        disabled={savingMemory}
                        className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-bold py-2.5 rounded-xl flex items-center justify-center gap-2 transition"
                      >
                        {savingMemory ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Save className="w-3.5 h-3.5" />
                        )}
                        Save Convention Memory
                      </button>
                    </form>
                  </div>
                </div>

              </div>
            )}

          </div>
        </div>
      )}
    </div>
  );
};
