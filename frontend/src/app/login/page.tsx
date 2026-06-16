"use client";

import { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { auth } from "@/services/api";
import { Cpu, Eye, EyeOff, Loader2 } from "lucide-react";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [guestLoading, setGuestLoading] = useState(false);

  useEffect(() => {
    // Check if guest demo was requested
    if (searchParams.get("guest") === "true") {
      handleGuestLogin();
    }
  }, [searchParams]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;

    setLoading(true);
    setError("");

    try {
      await auth.login({ username, password });
      router.push("/chat");
    } catch (err: any) {
      setError(err.message || "Invalid credentials.");
      setLoading(false);
    }
  };

  const handleGuestLogin = async () => {
    setGuestLoading(true);
    setError("");

    const randomId = Math.floor(10000 + Math.random() * 90000);
    const guestUsername = `guest_${randomId}`;
    const guestEmail = `${guestUsername}@nexusai-demo.com`;
    const guestPassword = `guestPass123!_${randomId}`;

    try {
      // 1. Register guest user
      await auth.register({
        email: guestEmail,
        username: guestUsername,
        password: guestPassword,
        display_name: `Guest #${randomId}`
      });

      // 2. Log guest user in
      await auth.login({
        username: guestUsername,
        password: guestPassword
      });

      router.push("/chat");
    } catch (err: any) {
      setError("Failed to initialize guest demo workspace.");
      setGuestLoading(false);
    }
  };

  return (
    <div className="w-full max-w-md glass-panel p-8 rounded-2xl shadow-2xl relative z-10 animate-fade-in">
      {/* Brand */}
      <div className="flex flex-col items-center mb-8">
        <div className="bg-blue-600 p-3 rounded-2xl text-white mb-3 shadow-lg shadow-blue-600/30">
          <Cpu className="w-6 h-6" />
        </div>
        <h2 className="text-2xl font-bold text-white">Welcome to NexusAI</h2>
        <p className="text-sm text-slate-400 mt-1">Sign in to enter the orchestrator</p>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-4 py-3 rounded-lg mb-6 text-center">
          {error}
        </div>
      )}

      <form onSubmit={handleLogin} className="space-y-5">
        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Username
          </label>
          <input
            type="text"
            required
            className="w-full px-4 py-3 rounded-xl glass-input text-sm"
            placeholder="e.g. shubh_admin"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={loading || guestLoading}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
            Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              required
              className="w-full px-4 py-3 rounded-xl glass-input text-sm pr-10"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading || guestLoading}
            />
            <button
              type="button"
              className="absolute right-3 top-3.5 text-slate-500 hover:text-slate-300"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading || guestLoading}
          className="w-full bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3.5 rounded-xl transition-all duration-200 shadow-md shadow-blue-600/25 flex items-center justify-center space-x-2"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <span>Authenticate</span>
          )}
        </button>
      </form>

      <div className="relative flex py-4 items-center">
        <div className="flex-grow border-t border-slate-800" />
        <span className="flex-shrink mx-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">
          Or
        </span>
        <div className="flex-grow border-t border-slate-800" />
      </div>

      <button
        type="button"
        onClick={handleGuestLogin}
        disabled={loading || guestLoading}
        className="w-full bg-slate-900 hover:bg-slate-850 border border-slate-800 text-slate-300 font-semibold py-3.5 rounded-xl transition-colors duration-200 flex items-center justify-center space-x-2"
      >
        {guestLoading ? (
          <Loader2 className="w-4 h-4 animate-spin text-slate-400" />
        ) : (
          <span>Enter as Guest (Demo)</span>
        )}
      </button>

      <p className="text-center text-xs text-slate-400 mt-6">
        Don't have an account?{" "}
        <Link href="/register" className="text-blue-400 hover:underline">
          Register here
        </Link>
      </p>
    </div>
  );
}

export default function Login() {
  return (
    <main className="flex-1 min-h-screen bg-slate-950 flex justify-center items-center px-4 relative overflow-hidden">
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a_1px,transparent_1px),linear-gradient(to_bottom,#0f172a_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-25" />
      <Suspense fallback={
        <div className="flex flex-col items-center justify-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-slate-400 text-sm">Loading login portal...</p>
        </div>
      }>
        <LoginForm />
      </Suspense>
    </main>
  );
}
