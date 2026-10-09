"use client";

import React from "react";
import { Sparkles, Heart, Shield, Image as ImageIcon, BarChart2, Trash2, LogOut } from "lucide-react";

interface RelationshipState {
  level: number;
  title: string;
  progress: number;
}

interface CompanionPanelProps {
  relationship: RelationshipState;
  presentationMode: "private" | "public";
  setPresentationMode: (mode: "private" | "public") => void;
  isIncognito: boolean;
  setIsIncognito: (val: boolean) => void;
  showMediaGallery: boolean;
  setShowMediaGallery: (val: boolean) => void;
  showDashboard: boolean;
  setShowDashboard: (val: boolean) => void;
  onClearChat: () => void;
  onSignOut: () => void;
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
  onSignOut
}) => {
  return (
    <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center p-3 sm:p-4 border-b border-gray-800 bg-gray-900/60 backdrop-blur-md sticky top-0 z-20 gap-3 sm:gap-0 shadow-sm">
      {/* Brand Identity, Avatar, Presence & Mode Switcher */}
      <div className="flex flex-wrap items-center justify-between w-full sm:w-auto gap-3">
        <div className="flex items-center gap-3">
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
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 border-2 border-gray-900 rounded-full"></span>
          </div>

          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h1 className="text-lg sm:text-xl font-black text-transparent bg-clip-text bg-gradient-to-r from-indigo-300 via-purple-300 to-pink-300 tracking-tight leading-none">
                Aura
              </h1>

              {/* Mode Switcher Pill: Private vs Creator */}
              <div className="flex items-center bg-gray-800/80 p-0.5 rounded-full border border-gray-700/60 text-xs">
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
                  Private
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
            </div>

            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span className="text-[10px] text-emerald-400 font-medium">Active now</span>
            </div>
          </div>
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

      {/* Control Buttons Toolbar */}
      <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0 no-scrollbar">
        {/* Media Gallery */}
        <button
          onClick={() => setShowMediaGallery(!showMediaGallery)}
          className="px-3 py-1.5 bg-pink-600/15 text-pink-300 rounded-lg text-xs font-medium hover:bg-pink-600/25 transition border border-pink-500/20 flex items-center gap-1.5 whitespace-nowrap"
        >
          <ImageIcon className="w-3.5 h-3.5" />
          Gallery
        </button>

        {/* Incognito Mode */}
        <button
          onClick={() => setIsIncognito(!isIncognito)}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition flex items-center gap-1.5 whitespace-nowrap border ${
            isIncognito
              ? "bg-purple-600/30 text-purple-200 border-purple-500 shadow-[0_0_12px_rgba(168,85,247,0.4)]"
              : "bg-gray-800/60 text-gray-400 border-gray-700 hover:text-purple-300"
          }`}
          title="When active, conversations are not permanently stored in episodic memory"
        >
          <Shield className="w-3.5 h-3.5" />
          {isIncognito ? "Incognito" : "Normal"}
        </button>

        {/* Analytics Dashboard */}
        <button
          onClick={() => setShowDashboard(!showDashboard)}
          className="px-3 py-1.5 bg-indigo-600/15 text-indigo-300 rounded-lg hover:bg-indigo-600/25 transition border border-indigo-500/20 text-xs font-medium flex items-center gap-1.5 whitespace-nowrap"
        >
          <BarChart2 className="w-3.5 h-3.5" />
          {showDashboard ? "Hide" : "Analytics"}
        </button>

        {/* Clear Chat */}
        <button
          onClick={onClearChat}
          className="px-2.5 py-1.5 bg-red-600/15 text-red-400 rounded-lg text-xs font-medium hover:bg-red-600/25 transition border border-red-500/20 flex items-center gap-1 whitespace-nowrap"
          title="Clear Conversation"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>

        {/* Logout */}
        <button
          onClick={onSignOut}
          className="px-2.5 py-1.5 bg-gray-800 text-gray-400 rounded-lg text-xs font-medium hover:text-red-400 hover:bg-gray-700 transition border border-gray-700 flex items-center gap-1 whitespace-nowrap"
          title="Log Out"
        >
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};

