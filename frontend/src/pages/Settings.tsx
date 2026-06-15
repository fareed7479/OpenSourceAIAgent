import React, { useState, useEffect } from "react";
import { Settings as SettingsIcon, Loader2, Save, Key, Sparkles, CheckCircle2 } from "lucide-react";
import { api } from "../api/client";

interface Setting {
  id: string;
  key: string;
  value: string;
}

interface ProviderConfig {
  id: string;
  provider_name: string;
  config_data: {
    api_key?: string;
    model_name?: string;
    custom_url?: string;
  };
}

export const Settings: React.FC = () => {
  const [prefLangs, setPrefLangs] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [geminiModel, setGeminiModel] = useState("gemini-2.5-flash");
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState("");

  const loadSettings = async () => {
    try {
      // 1. Fetch settings
      const settingsData = await api.get<Setting[]>("/settings");
      const langSetting = settingsData.find((s) => s.key === "preferred_languages");
      if (langSetting) {
        setPrefLangs(langSetting.value);
      }

      // 2. Fetch provider configs
      const configs = await api.get<ProviderConfig[]>("/settings/providers");
      const gemini = configs.find((c) => c.provider_name === "gemini");
      if (gemini) {
        setGeminiKey(gemini.config_data.api_key || "");
        setGeminiModel(gemini.config_data.model_name || "gemini-2.5-flash");
      }
    } catch (err) {
      console.error("Failed to load settings:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setSuccess("");
    try {
      // Save preferred languages
      await api.post("/settings", {
        key: "preferred_languages",
        value: prefLangs
      });

      // Save Gemini credentials config
      await api.post("/settings/providers", {
        provider_name: "gemini",
        config_data: {
          api_key: geminiKey,
          model_name: geminiModel
        }
      });

      setSuccess("Settings and API keys saved successfully.");
      loadSettings();
    } catch (err: any) {
      alert(err.message || "Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-white">Settings</h1>
        <p className="text-gray-400 text-sm mt-1">Configure your coding preferences, repository monitoring guidelines, and LLM providers.</p>
      </div>

      {success && (
        <div className="flex items-center gap-2 p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 text-xs rounded-xl">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-indigo-500 animate-spin" />
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-6 max-w-2xl">
          
          {/* General Developer Preferences */}
          <div className="glass-panel p-6 rounded-2xl border border-indigo-500/10 shadow-lg space-y-4">
            <h3 className="text-white font-bold text-base flex items-center gap-2">
              <SettingsIcon className="w-4.5 h-4.5 text-indigo-400" />
              Contributor Preferences
            </h3>
            
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Preferred Technologies & Languages
              </label>
              <input
                type="text"
                placeholder="e.g. Python, TypeScript, JavaScript, Go"
                value={prefLangs}
                onChange={(e) => setPrefLangs(e.target.value)}
                className="w-full bg-gray-950/60 border border-gray-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-gray-200 rounded-xl py-3 px-4 outline-none transition text-sm"
              />
              <span className="text-[10px] text-gray-500 block">Comma-separated list. Used by the issue ranking engine to boost suitability scores.</span>
            </div>
          </div>

          {/* AI Providers Keys and models setup */}
          <div className="glass-panel p-6 rounded-2xl border border-indigo-500/10 shadow-lg space-y-4">
            <h3 className="text-white font-bold text-base flex items-center gap-2">
              <Key className="w-4.5 h-4.5 text-indigo-400" />
              LLM Provider Configuration
            </h3>
            <p className="text-xs text-gray-400">Configure keys for AI coding agents. Sensitive credentials are encrypted before storage.</p>
            
            <div className="border-t border-gray-800/60 pt-4 space-y-4">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-semibold text-white">Google Gemini</span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Model Selection
                  </label>
                  <select
                    value={geminiModel}
                    onChange={(e) => setGeminiModel(e.target.value)}
                    className="w-full bg-gray-950 border border-gray-800 text-gray-300 rounded-xl py-3 px-3 outline-none text-sm"
                  >
                    <option value="gemini-2.5-flash">gemini-2.5-flash (Fast & recommended)</option>
                    <option value="gemini-2.5-pro">gemini-2.5-pro (Higher quality reasoning)</option>
                  </select>
                </div>
                
                <div className="space-y-1.5">
                  <label className="block text-xs font-semibold text-gray-400 uppercase tracking-wider">
                    Gemini API Key
                  </label>
                  <input
                    type="password"
                    placeholder={geminiKey ? "••••••••••••••••" : "Paste your Gemini API key here..."}
                    value={geminiKey === "••••••••••••••••" ? "••••••••••••••••" : geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    className="w-full bg-gray-950 border border-gray-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-gray-200 rounded-xl py-3 px-4 outline-none transition text-sm"
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={saving}
              className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white font-semibold py-3 px-8 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/15 transition duration-150 hover:scale-[1.01]"
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              Save Configurations
            </button>
          </div>

        </form>
      )}
    </div>
  );
};
