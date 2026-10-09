// FILE: frontend/app/page.tsx
"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { auth, googleProvider } from "./firebase";
import { 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword, 
  onAuthStateChanged, 
  setPersistence, 
  signInWithPopup, 
  browserLocalPersistence, 
  sendPasswordResetEmail, 
  User 
} from "firebase/auth";

const ChatApp = dynamic(() => import("./ChatApp"), { ssr: false });

export default function Page() {
  const [isMounted, setIsMounted] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [loadingAuth, setLoadingAuth] = useState(true);

  const [isLoginMode, setIsLoginMode] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [resetMsg, setResetMsg] = useState("");
  const [authSubmitting, setAuthSubmitting] = useState(false);

  useEffect(() => {
    setIsMounted(true);
    setPersistence(auth, browserLocalPersistence)
      .then(() => {
        const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
          setUser(currentUser);
          setLoadingAuth(false);
        });
        return () => unsubscribe();
      })
      .catch((err) => {
        console.error("Auth persistence error:", err);
        setLoadingAuth(false);
      });
  }, []);

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setResetMsg("");
    setAuthSubmitting(true);
    try {
      if (isLoginMode) {
        await signInWithEmailAndPassword(auth, email, password);
      } else {
        await createUserWithEmailAndPassword(auth, email, password);
      }
    } catch (err: any) {
      setError(err.message.replace("Firebase: ", ""));
    } finally {
      setAuthSubmitting(false);
    }
  };

  const handleSocialLogin = async () => {
    setError("");
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err: any) {
      setError(err.message.replace("Firebase: ", ""));
    }
  };

  const handleResetPassword = async () => {
    if (!email) {
      setError("Please enter your email first.");
      return;
    }
    try {
      await sendPasswordResetEmail(auth, email);
      setResetMsg("Password reset link sent to your email!");
      setError("");
    } catch (err: any) {
      setError(err.message.replace("Firebase: ", ""));
    }
  };

  if (!isMounted || loadingAuth) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-950 text-white gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
        <div className="text-indigo-400 font-mono text-sm tracking-wide animate-pulse">Initializing Aura OS...</div>
      </div>
    );
  }

  if (user) {
    return <ChatApp currentUser={user} />;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#090a0f] p-4">
      <div className="w-full max-w-md bg-gray-900/80 border border-gray-800 rounded-3xl p-8 backdrop-blur-xl shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-extrabold text-transparent bg-clip-text bg-linear-to-r from-indigo-400 via-purple-400 to-pink-400">
            Aura OS
          </h1>
          <p className="text-gray-400 text-xs mt-2">Next-Gen Intelligent Companion</p>
        </div>

        {error && <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs">{error}</div>}
        {resetMsg && <div className="mb-4 p-3 bg-green-500/10 border border-green-500/30 rounded-xl text-green-400 text-xs">{resetMsg}</div>}

        <form onSubmit={handleAuth} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2.5 bg-gray-950 border border-gray-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
              placeholder="you@example.com"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2.5 bg-gray-950 border border-gray-800 rounded-xl text-white text-sm focus:outline-none focus:border-indigo-500"
              placeholder="••••••••"
            />
          </div>

          <div className="flex justify-end">
            <button type="button" onClick={handleResetPassword} className="text-xs text-indigo-400 hover:text-indigo-300 transition">
              Forgot Password?
            </button>
          </div>

          <button
            type="submit"
            disabled={authSubmitting}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-medium text-sm transition shadow-lg shadow-indigo-600/20"
          >
            {authSubmitting ? "Processing..." : isLoginMode ? "Sign In" : "Create Account"}
          </button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-gray-800" /></div>
          <div className="relative flex justify-center text-xs text-gray-500 uppercase"><span className="bg-gray-900 px-2">Or</span></div>
        </div>

        <button
          onClick={handleSocialLogin}
          type="button"
          className="w-full py-2.5 bg-gray-800/80 hover:bg-gray-800 border border-gray-700/60 rounded-xl text-white text-sm font-medium transition flex items-center justify-center gap-2"
        >
          Continue with Google
        </button>

        <div className="text-center mt-6">
          <button
            onClick={() => { setIsLoginMode(!isLoginMode); setError(""); }}
            className="text-xs text-gray-400 hover:text-white transition"
          >
            {isLoginMode ? "Need an account? Sign Up" : "Have an account? Sign In"}
          </button>
        </div>
      </div>
    </div>
  );
}