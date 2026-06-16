import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Loader2 } from "lucide-react";

export const AuthCallback: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState("");

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    const code = queryParams.get("code");
    const mock = queryParams.get("mock");

    if (mock === "true") {
      // Direct mock login bypass
      navigate("/login");
      return;
    }

    if (!code) {
      setError("No authorization code received from GitHub.");
      setTimeout(() => navigate("/login"), 3000);
      return;
    }

    const exchangeCode = async () => {
      try {
        const response = await fetch(
          `http://localhost:8000/api/v1/auth/callback?code=${code}`
        );
        if (!response.ok) {
          throw new Error("Failed to exchange GitHub authorization code");
        }
        const data = await response.json();
        login(data.access_token, data.user);
        navigate("/");
      } catch (err: any) {
        setError(err.message || "OAuth authentication failed");
        setTimeout(() => navigate("/login"), 3000);
      }
    };

    exchangeCode();
  }, [location.search, login, navigate]);

  return (
    <div className="min-h-screen cyber-grid flex flex-col items-center justify-center text-white px-4">
      <div className="glass-panel p-8 rounded-2xl border border-indigo-500/20 shadow-2xl text-center max-w-sm">
        {error ? (
          <>
            <h2 className="text-red-400 text-xl font-bold mb-2">Authentication Error</h2>
            <p className="text-sm text-gray-400">{error}</p>
            <p className="text-[10px] text-gray-600 mt-4">Redirecting back to login...</p>
          </>
        ) : (
          <>
            <Loader2 className="w-12 h-12 text-indigo-400 animate-spin mx-auto mb-4" />
            <h2 className="text-2xl font-bold mb-2">Authenticating</h2>
            <p className="text-sm text-gray-400">Exchanging authorization credentials with GitHub...</p>
          </>
        )}
      </div>
    </div>
  );
};
