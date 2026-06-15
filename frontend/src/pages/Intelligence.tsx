import React, { useState, useEffect } from "react";
import { Loader2, Search, Brain, Code, FileCode, Sparkles } from "lucide-react";
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

export const Intelligence: React.FC = () => {
  const [repos, setRepos] = useState<Repository[]>([]);
  const [selectedRepo, setSelectedRepo] = useState("");
  
  // Intelligence states
  const [intelData, setIntelData] = useState<RepoIntelligenceData | null>(null);
  const [memories, setMemories] = useState<MemoryRecord[]>([]);
  const [loadingIntel, setLoadingIntel] = useState(false);

  // Search states
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);

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
    try {
      const symbolsResp = await api.get<RepoIntelligenceData>(`/intelligence/repo/${selectedRepo}/symbols`);
      setIntelData(symbolsResp);

      const memoryResp = await api.get<MemoryRecord[]>(`/intelligence/repo/${selectedRepo}/memory`);
      setMemories(memoryResp);
    } catch (err) {
      console.error("Failed to load intelligence maps:", err);
      setIntelData(null);
      setMemories([]);
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

  return (
    <div className="space-y-8 animate-fade-in max-w-none">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white flex items-center gap-2.5">
            <Brain className="w-8 h-8 text-indigo-400" />
            Repository Intelligence
          </h1>
          <p className="text-gray-400 text-sm mt-1">Explore AST symbols, semantic code structures, and long-term codebase memories.</p>
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
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          
          {/* Left Columns (Col Span 2): AST Symbol Mapping and Semantic Search */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Semantic Search Box */}
            <div className="glass-panel p-6 rounded-2xl border border-indigo-500/10 shadow-lg relative overflow-hidden">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-5 h-5 text-indigo-400 animate-pulse" />
                <h2 className="text-base font-bold text-white">Semantic Code Search</h2>
              </div>
              <p className="text-xs text-gray-400 mb-4">Query your codebase in natural language (e.g. "authentication validation") to scan matching symbols.</p>
              
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

              {/* Semantic Search Results list */}
              {searchResults.length > 0 && (
                <div className="mt-6 space-y-4 pt-4 border-t border-gray-850/60">
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

            {/* AST Symbol map tree browser */}
            <div className="glass-panel p-6 rounded-2xl border border-gray-800/80 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Code className="w-5 h-5 text-indigo-400" />
                AST Codebase Symbol Mapping
              </h3>
              
              {intelData?.codebase_map.length === 0 ? (
                <div className="p-6 text-center text-gray-500 italic text-sm">
                  No codebase symbols indexed yet. Wait for clone to complete.
                </div>
              ) : (
                <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                  {intelData?.codebase_map.map((fileMap) => (
                    <div key={fileMap.filepath} className="border border-gray-800/60 rounded-xl overflow-hidden">
                      <div className="bg-gray-950/40 px-4 py-2.5 border-b border-gray-800/60 flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-indigo-400" />
                        <span className="text-xs font-bold text-gray-300">{fileMap.filepath}</span>
                      </div>
                      <div className="p-3 divide-y divide-gray-850/40 bg-gray-950/10">
                        {fileMap.symbols.length === 0 ? (
                          <div className="text-[10px] text-gray-500 italic py-1 px-1">No classes or functions detected in file.</div>
                        ) : (
                          fileMap.symbols.map((sym, sIdx) => (
                            <div key={sIdx} className="flex justify-between items-center py-2 text-xs">
                              <span className="font-semibold text-gray-200 flex items-center gap-1.5">
                                <span className={`w-1.5 h-1.5 rounded-full ${sym.type === "class" ? "bg-purple-400" : "bg-blue-400"}`} />
                                {sym.name}
                              </span>
                              <div className="flex items-center gap-3 text-[10px] text-gray-500">
                                <span>Type: {sym.type}</span>
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

          </div>

          {/* Right Column: Repository Memory (Phase 20) */}
          <div className="lg:col-span-1 space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-gray-800/80 space-y-4">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Brain className="w-5 h-5 text-indigo-400" />
                Repository Memory
              </h3>
              <p className="text-xs text-gray-400">Captured architectural conventions, past fixes, and developer reviews used to steer code planning.</p>
              
              {memories.length === 0 ? (
                <div className="p-8 text-center bg-gray-950/40 border border-gray-900 rounded-xl text-gray-500 italic text-xs">
                  No memories cached yet. Successful agent runs compile memory patterns.
                </div>
              ) : (
                <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
                  {memories.map((m) => (
                    <div key={m.id} className="p-3.5 bg-gray-950/60 border border-gray-850 rounded-xl space-y-1.5">
                      <div className="flex justify-between items-center text-[9px] uppercase font-bold tracking-wider">
                        <span className="text-indigo-400">{m.memory_type}</span>
                        <span className="text-gray-500">{new Date(m.created_at).toLocaleDateString()}</span>
                      </div>
                      <h4 className="font-bold text-white text-xs">{m.key}</h4>
                      <p className="text-[10px] text-gray-400 leading-relaxed font-mono">{m.value}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

        </div>
      )}
    </div>
  );
};
