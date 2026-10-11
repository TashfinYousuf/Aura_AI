"use client";

import React, { useState, useRef, useEffect } from "react";
import { 
  Sparkles, Heart, Flame, Shield, Image as ImageIcon, BarChart2, 
  Trash2, LogOut, MoreVertical, Search, Palette, Download, EyeOff, Check
} from "lucide-react";

interface RelationshipState {
  level: number;
  title: string;
  progress: number;
}

interface CompanionPanelProps {
  relationship: RelationshipState;
  presentationMode: "private" | "public" | "adult";
  setPresentationMode: (mode: "private" | "public" | "adult") => void;
  isIncognito: boolean;
  setIsIncognito: (val: boolean) => void;
  showMediaGallery: boolean;
  setShowMediaGallery: (val: boolean) => void;
  showDashboard: boolean;
  setShowDashboard: (val: boolean) => void;
  onClearChat: () => void;
  onSignOut: () => void;
  onOpenSearch: () => void;
  onOpenThemeModal: () => void;
  onExportChat: () => void;
}

export const CompanionPanel: React.FC<CompanionPanelProps> = ({
  relationship,
  presentationMode,
  setPresentationMode,
  isIncognito,
  setIsIncognito,
  showMediaGallery,
  setShowMediaGallery,
  showDashboard,
  setShowDashboard,
  onClearChat,
  onSignOut,
  onOpenSearch,
  onOpenThemeModal,
  onExportChat
}) => {
  const [presence, setPresence] = useState<{ status_label: string; indicator_color: string }>({
    status_label: "Active now",
    indicator_color: "emerald"
  });
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchPresence = async () => {
      try {
        const res = await fetch("/api/presence/status");
        if (res.ok) {
          const data = await res.json();
          if (data && data.status_label) {
            setPresence({
              status_label: data.status_label,
              indicator_color: data.indicator_color || "emerald"
            });
          }
        }
      } catch {
        // Fallback to active
      }
    };
    fetchPresence();
    const interval = setInterval(fetchPresence, 60000);
    return () => clearInterval(interval);
  }, []);

  // Close 3-dots dropdown on clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const dotBg =
    presence.indicator_color === "amber"
      ? "bg-amber-500"
      : presence.indicator_color === "slate"
      ? "bg-gray-500"
      : "bg-emerald-500";

  const textColor =
    presence.indicator_color === "amber"
      ? "text-amber-400"
      : presence.indicator_color === "slate"
      ? "text-gray-400"
      : "text-emerald-400";

  return (
    <header className="flex flex-col md:flex-row justify-between items-center px-3 py-2.5 sm:px-4 sm:py-3 border-b border-gray-800 bg-gray-900/80 backdrop-blur-md sticky top-0 z-30 gap-2.5 md:gap-0 shadow-md">
      {/* Left: Brand Identity, Avatar, Presence */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="relative shrink-0">
          <img
            src="/api/static/references/aura_master_identity.png"
            alt="Aura"
            className="w-9 h-9 sm:w-10 sm:h-10 rounded-full object-cover border border-purple-500/40 shadow-sm"
            onError={(e) => {
              const target = e.target as HTMLImageElement;
              target.src = "https://kkabhwfduxijpftwdzou.supabase.co/storage/v1/object/sign/Aura%20Files/Aura_Ref_Pic.png?token=eyJraWQiOiJhY2YxYzkzYS0xNTk1LTQ5NzgtYjQxMy04OTU0YjVlYmYwOTAiLCJhbGciOiJIUzI1NiJ9.eyJ1cmwiOiJBdXJhIEZpbGVzL0F1cmFfUmVmX1BpYy5wbmciLCJzY29wZSI6ImRvd25sb2FkIiwiaWF0IjoxNzkxNTg2NjczLCJleHAiOjE3OTQxNzg2NzN9.qSonUN7MSsrbC4EwsDKO6KwIso6j5250aUG980xelYY";
            }}
          />
          {/* Steady status indicator under DP */}
          <span className={`absolute bottom-0 right-0 w-2.5 h-2.5 ${dotBg} border-2 border-gray-900 rounded-full shadow-sm`}></span>
        </div>

        <div className="flex flex-col">
          <h1 className="text-lg sm:text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 via-purple-300 to-pink-300 tracking-tight leading-none">
            Aura
          </h1>
          {/* Clean presence status label */}
          <div className="flex items-center mt-0.5">
            <span className={`text-[10px] ${textColor} font-medium`}>{presence.status_label}</span>
          </div>
        </div>
      </div>

      {/* Center: Center-Aligned Mode Switcher & Relationship Progression */}
      <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3">
        {/* Mode Switcher Pill: Normal vs Intimate vs Creator */}
        <div className="flex items-center bg-gray-800/80 p-0.5 rounded-full border border-gray-700/60 text-xs shadow-inner">
          <button
            onClick={() => setPresentationMode("private")}
            className={`px-2.5 py-1 rounded-full transition-all flex items-center gap-1 font-medium ${
              presentationMode === "private"
                ? "bg-indigo-600 text-white shadow-sm"
                : "text-gray-400 hover:text-gray-200"
            }`}
            title="1:1 Intimate & Intellectual Companion"
          >
            <Heart className="w-3 h-3 fill-current" />
            Normal
          </button>
          <button
            onClick={() => setPresentationMode("adult")}
            className={`px-2.5 py-1 rounded-full transition-all flex items-center gap-1 font-medium ${
              presentationMode === "adult"
                ? "bg-gradient-to-r from-rose-600 to-pink-600 text-white shadow-sm shadow-pink-900/50"
                : "text-gray-400 hover:text-pink-300"
            }`}
            title="Sensual & Intimate Adult Roleplay Mode"
          >
            <Flame className="w-3 h-3 fill-current" />
            Intimate
          </button>
          <button
            onClick={() => setPresentationMode("public")}
            className={`px-2.5 py-1 rounded-full transition-all flex items-center gap-1 font-medium ${
              presentationMode === "public"
                ? "bg-gradient-to-r from-pink-600 to-purple-600 text-white shadow-sm"
                : "text-gray-400 hover:text-gray-200"
            }`}
            title="Virtual Creator & Brand Ambassador"
          >
            <Sparkles className="w-3 h-3" />
            Creator
          </button>
        </div>

        {/* Level & Progress */}
        <div className="flex items-center gap-2">
          <span className="text-[11px] px-2 py-0.5 bg-indigo-500/20 text-indigo-300 rounded-md border border-indigo-500/30 whitespace-nowrap font-medium">
            Lv. {relationship.level} • {relationship.title}
          </span>
          <div className="w-16 sm:w-20 h-1.5 bg-gray-800 rounded-full overflow-hidden border border-gray-700/50">
            <div
              className="h-full bg-linear-to-r from-indigo-500 to-purple-500 transition-all duration-500"
              style={{ width: `${relationship.progress}%` }}
            />
          </div>
        </div>
      </div>

      {/* Right: Analytics & 3-Dots Profile Menu (Outer Gallery & Normal removed per user instruction) */}
      <div className="flex items-center gap-2 shrink-0">
        {/* Outer Analytics Toggle Button */}
        <button
          onClick={() => setShowDashboard(!showDashboard)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 whitespace-nowrap border ${
            showDashboard
              ? "bg-indigo-600 text-white border-indigo-500 shadow-sm"
              : "bg-gray-800/80 text-gray-300 border-gray-700 hover:text-white hover:bg-gray-750"
          }`}
          title="Mood & Goal Analytics"
        >
          <BarChart2 className="w-3.5 h-3.5 text-amber-400" />
          <span className="hidden sm:inline">Analytics</span>
        </button>

        {/* 3-DOTS TELEGRAM/MESSENGER PROFILE MENU */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className={`p-2 rounded-lg text-xs font-medium transition border ${
              menuOpen
                ? "bg-indigo-600 text-white border-indigo-500 shadow-md"
                : "bg-gray-800 text-gray-300 border-gray-700 hover:text-white hover:bg-gray-750"
            }`}
            title="Conversation Options & Profile Menu"
          >
            <MoreVertical className="w-4 h-4" />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-2 w-64 bg-gray-900/95 border border-gray-700/80 rounded-2xl p-2 shadow-2xl backdrop-blur-xl z-50 animate-in fade-in zoom-in-95 duration-150">
              <div className="px-3 py-2 border-b border-gray-800/80 mb-1">
                <span className="text-xs font-semibold text-gray-200">Chat Settings</span>
                <p className="text-[10px] text-gray-400 mt-0.5">Customize conversation & media</p>
              </div>

              {/* 1. Search Conversation */}
              <button
                onClick={() => {
                  setMenuOpen(false);
                  onOpenSearch();
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-gray-800/80 rounded-xl transition"
              >
                <Search className="w-3.5 h-3.5 text-indigo-400" />
                <span>Search Conversation</span>
              </button>

              {/* 2. Chat Wallpaper & Themes */}
              <button
                onClick={() => {
                  setMenuOpen(false);
                  onOpenThemeModal();
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-gray-800/80 rounded-xl transition"
              >
                <Palette className="w-3.5 h-3.5 text-pink-400" />
                <span>Chat Wallpaper & Themes</span>
              </button>

              {/* 3. Export Chat History */}
              <button
                onClick={() => {
                  setMenuOpen(false);
                  onExportChat();
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-gray-800/80 rounded-xl transition"
              >
                <Download className="w-3.5 h-3.5 text-cyan-400" />
                <span>Export Chat History (.txt)</span>
              </button>

              {/* 4. Disappearing Messages / Incognito Toggle */}
              <button
                onClick={() => {
                  setIsIncognito(!isIncognito);
                }}
                className="w-full flex items-center justify-between px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-gray-800/80 rounded-xl transition"
              >
                <div className="flex items-center gap-2.5">
                  <EyeOff className="w-3.5 h-3.5 text-purple-400" />
                  <span>Incognito (Disappearing)</span>
                </div>
                <div className={`w-7 h-4 rounded-full transition-colors relative ${isIncognito ? "bg-purple-600" : "bg-gray-700"}`}>
                  <div className={`w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform ${isIncognito ? "right-0.5" : "left-0.5"}`} />
                </div>
              </button>

              {/* 5. Photos & Media Vault */}
              <button
                onClick={() => {
                  setMenuOpen(false);
                  setShowMediaGallery(true);
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-300 hover:text-white hover:bg-gray-800/80 rounded-xl transition"
              >
                <ImageIcon className="w-3.5 h-3.5 text-rose-400" />
                <span>Photos & Media Vault</span>
              </button>

              <div className="border-t border-gray-800/80 my-1"></div>

              {/* 6. Clear Conversation */}
              <button
                onClick={() => {
                  setMenuOpen(false);
                  onClearChat();
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-red-400 hover:text-red-300 hover:bg-red-950/40 rounded-xl transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Conversation</span>
              </button>

              {/* 7. Log Out */}
              <button
                onClick={() => {
                  setMenuOpen(false);
                  onSignOut();
                }}
                className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-800/60 rounded-xl transition"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Log Out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
