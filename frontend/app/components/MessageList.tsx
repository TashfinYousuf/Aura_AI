"use client";

import React, { useState } from "react";
import { 
  CheckCheck, Check, Reply, Edit3, Copy, Pin, PinOff, 
  Bookmark, BookmarkCheck, Trash2, MoreHorizontal, Sparkles 
} from "lucide-react";

export interface Message {
  role: 'ai' | 'user';
  id: string;
  content: string;
  audioBase64?: string;
  isVoiceNote?: boolean;
  imageUrl?: string;
  userAudioUrl?: string;
  reaction?: string;
  replyTo?: string;
  replyPreview?: string;
  videoUrl?: string;
  timestamp?: string;
  isEdited?: boolean;
  isPinned?: boolean;
  isSaved?: boolean;
}

interface MessageListProps {
  messages: Message[];
  streamingText?: string;
  actionStatus?: string | null;
  isLoading: boolean;
  hoveredMsgIdx: number | null;
  setHoveredMsgIdx: (idx: number | null) => void;
  editingMsgIdx: number | null;
  setEditingMsgIdx: (idx: number | null) => void;
  input: string;
  setInput: (val: string) => void;
  handleReaction: (idx: number, emoji: string) => void;
  setReplyingToMsg: (item: { id: string; preview: string; role: 'ai' | 'user' } | null) => void;
  submitEdit: (idx: number, content: string) => void;
  onUnsend: (msgId: string, everyone: boolean) => void;
  onPinMessage: (msgId: string) => void;
  onSaveMessage: (msgId: string) => void;
  pinnedMessageId: string | null;
  setViewingImage: (url: string | null) => void;
  resolveImageUrl: (url?: string | null) => string;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  searchQuery?: string;
  activeMatchId?: string | null;
  onShowToast: (text: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  streamingText,
  actionStatus,
  isLoading,
  hoveredMsgIdx,
  setHoveredMsgIdx,
  editingMsgIdx,
  setEditingMsgIdx,
  input,
  setInput,
  handleReaction,
  setReplyingToMsg,
  submitEdit,
  onUnsend,
  onPinMessage,
  onSaveMessage,
  pinnedMessageId,
  setViewingImage,
  resolveImageUrl,
  messagesEndRef,
  searchQuery = "",
  activeMatchId = null,
  onShowToast
}) => {
  const [activeMenuIdx, setActiveMenuIdx] = useState<number | null>(null);

  const EMOJI_LIST = ['❤️', '🔥', '😍', '🙈', '🥺', '😂', '👍'];

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    onShowToast("Copied to clipboard! 📋");
    setActiveMenuIdx(null);
  };

  const highlightMatches = (text: string, query: string) => {
    if (!query.trim()) return text;
    const parts = text.split(new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, i) =>
      part.toLowerCase() === query.toLowerCase() ? (
        <span key={i} className="bg-amber-400/40 text-amber-200 font-semibold px-0.5 rounded">
          {part}
        </span>
      ) : (
        part
      )
    );
  };

  return (
    <main className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-4 sm:space-y-5 scroll-smooth pb-32 max-w-4xl mx-auto w-full">
      {messages.map((msg, idx) => {
        const isUser = msg.role === "user";
        const isPinned = msg.id === pinnedMessageId || !!msg.isPinned;
        const isActiveMatch = msg.id === activeMatchId;
        const isMenuOpen = activeMenuIdx === idx;
        const isHovered = hoveredMsgIdx === idx;

        return (
          <div
            key={msg.id || idx}
            className={`flex ${isUser ? "justify-end" : "justify-start"} animate-in fade-in duration-200 relative group/msg`}
            onMouseEnter={() => setHoveredMsgIdx(idx)}
            onMouseLeave={() => {
              setHoveredMsgIdx(null);
              if (!isMenuOpen) setActiveMenuIdx(null);
            }}
          >
            {/* FLOATING REACTION BAR & ACTION MENU (TELEGRAM + MESSENGER HYBRID) */}
            {(isHovered || isMenuOpen) && (
              <div 
                className={`absolute -top-9 ${isUser ? "right-2" : "left-2"} bg-gray-900/95 backdrop-blur-xl border border-gray-700/80 rounded-full px-2 py-1 flex items-center gap-1 z-20 shadow-2xl animate-in fade-in zoom-in-95 duration-150`}
              >
                {/* Expressive Floating Emojis */}
                {EMOJI_LIST.map((emoji) => (
                  <button
                    key={emoji}
                    onClick={() => {
                      handleReaction(idx, emoji);
                      setActiveMenuIdx(null);
                    }}
                    className={`hover:scale-135 transition-transform text-xs sm:text-sm p-1 rounded-full ${
                      msg.reaction === emoji ? "bg-indigo-500/30 scale-110 ring-1 ring-indigo-400" : ""
                    }`}
                    title={`React ${emoji}`}
                  >
                    {emoji}
                  </button>
                ))}

                <div className="w-px h-3.5 bg-gray-700 mx-1"></div>

                {/* Quick Reply Button */}
                <button
                  onClick={() => {
                    setReplyingToMsg({ 
                      id: msg.id, 
                      preview: msg.content.substring(0, 80), 
                      role: msg.role 
                    });
                    setActiveMenuIdx(null);
                  }}
                  className="text-gray-400 hover:text-indigo-300 p-1 rounded-full hover:bg-gray-800 transition text-xs"
                  title="Reply"
                >
                  <Reply className="w-3.5 h-3.5" />
                </button>

                {/* Quick Copy Button */}
                <button
                  onClick={() => copyToClipboard(msg.content)}
                  className="text-gray-400 hover:text-cyan-300 p-1 rounded-full hover:bg-gray-800 transition text-xs"
                  title="Copy"
                >
                  <Copy className="w-3.5 h-3.5" />
                </button>

                {/* Quick Pin Button */}
                <button
                  onClick={() => {
                    onPinMessage(msg.id);
                    setActiveMenuIdx(null);
                  }}
                  className={`p-1 rounded-full hover:bg-gray-800 transition text-xs ${
                    isPinned ? "text-amber-400" : "text-gray-400 hover:text-amber-300"
                  }`}
                  title={isPinned ? "Unpin message" : "Pin message to top"}
                >
                  {isPinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
                </button>

                {/* More Actions Popover Trigger (Telegram Style) */}
                <div className="relative">
                  <button
                    onClick={() => setActiveMenuIdx(isMenuOpen ? null : idx)}
                    className="text-gray-400 hover:text-white p-1 rounded-full hover:bg-gray-800 transition text-xs"
                    title="More actions"
                  >
                    <MoreHorizontal className="w-3.5 h-3.5" />
                  </button>

                  {/* Telegram Style Action Popover Menu */}
                  {isMenuOpen && (
                    <div className="absolute top-full right-0 mt-1.5 w-44 bg-gray-900 border border-gray-700 rounded-xl p-1 shadow-2xl z-30 text-xs backdrop-blur-xl animate-in fade-in zoom-in-95">
                      {isUser && (
                        <button
                          onClick={() => {
                            setInput(msg.content);
                            setEditingMsgIdx(idx);
                            setActiveMenuIdx(null);
                          }}
                          className="w-full flex items-center gap-2 px-2.5 py-1.5 hover:bg-gray-800 text-gray-300 hover:text-white rounded-lg transition"
                        >
                          <Edit3 className="w-3.5 h-3.5 text-indigo-400" />
                          <span>Edit Message</span>
                        </button>
                      )}

                      <button
                        onClick={() => {
                          onSaveMessage(msg.id);
                          setActiveMenuIdx(null);
                        }}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 hover:bg-gray-800 text-gray-300 hover:text-white rounded-lg transition"
                      >
                        {msg.isSaved ? (
                          <>
                            <BookmarkCheck className="w-3.5 h-3.5 text-pink-400" />
                            <span>Remove Bookmark</span>
                          </>
                        ) : (
                          <>
                            <Bookmark className="w-3.5 h-3.5 text-pink-400" />
                            <span>Save / Bookmark</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => {
                          onUnsend(msg.id, false);
                          setActiveMenuIdx(null);
                        }}
                        className="w-full flex items-center gap-2 px-2.5 py-1.5 hover:bg-gray-800 text-gray-300 hover:text-white rounded-lg transition"
                      >
                        <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                        <span>Delete for me</span>
                      </button>

                      {isUser && (
                        <button
                          onClick={() => {
                            onUnsend(msg.id, true);
                            setActiveMenuIdx(null);
                          }}
                          className="w-full flex items-center gap-2 px-2.5 py-1.5 hover:bg-rose-950/60 text-rose-400 hover:text-rose-300 rounded-lg transition font-medium"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                          <span>Unsend for everyone</span>
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* MESSAGE BUBBLE (TELEGRAM + MESSENGER HYBRID) */}
            <div
              id={`msg-${msg.id}`}
              className={`max-w-[88%] md:max-w-[72%] rounded-2xl px-4 py-3 shadow-md flex flex-col gap-1.5 relative transition-all duration-300 ${
                isUser
                  ? "bg-gradient-to-r from-indigo-600 via-indigo-600 to-purple-600 text-white rounded-br-xs shadow-indigo-950/40"
                  : "bg-gray-800/90 text-gray-100 rounded-bl-xs border border-gray-700/60 backdrop-blur-md shadow-black/20"
              } ${
                isActiveMatch ? "ring-2 ring-amber-400 ring-offset-2 ring-offset-gray-950 shadow-amber-500/20" : ""
              } ${
                editingMsgIdx === idx ? "ring-2 ring-indigo-400 ring-offset-2 ring-offset-gray-950 shadow-indigo-500/40" : ""
              } ${
                isPinned ? "border-amber-500/40" : ""
              }`}
            >
              {/* Pinned & Saved Header Indicators */}
              {(isPinned || msg.isSaved) && (
                <div className="flex items-center gap-2 text-[10px] opacity-80 border-b border-white/10 pb-1 mb-0.5">
                  {isPinned && (
                    <span className="flex items-center gap-1 text-amber-300 font-medium">
                      <Pin className="w-3 h-3 fill-amber-300/30" /> Pinned
                    </span>
                  )}
                  {msg.isSaved && (
                    <span className="flex items-center gap-1 text-pink-300 font-medium">
                      <BookmarkCheck className="w-3 h-3" /> Saved
                    </span>
                  )}
                </div>
              )}

              {/* Click-to-Jump Quoted Reply Card */}
              {msg.replyPreview && (
                <div
                  onClick={() => {
                    if (msg.replyTo) {
                      const target = document.getElementById(`msg-${msg.replyTo}`);
                      if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        target.classList.add('ring-2', 'ring-indigo-400', 'ring-offset-2', 'ring-offset-gray-950');
                        setTimeout(() => {
                          target.classList.remove('ring-2', 'ring-indigo-400', 'ring-offset-2', 'ring-offset-gray-950');
                        }, 1800);
                      }
                    }
                  }}
                  className={`cursor-pointer p-2 rounded-xl text-xs border-l-2 transition hover:opacity-95 ${
                    isUser
                      ? "bg-indigo-700/50 border-white/60 text-indigo-100"
                      : "bg-gray-900/70 border-indigo-400 text-gray-300"
                  } flex flex-col`}
                  title="Click to jump to original message"
                >
                  <span className="font-semibold text-[10px] opacity-80 flex items-center gap-1">
                    <Reply className="w-2.5 h-2.5" />
                    <span>Replied message</span>
                  </span>
                  <span className="truncate max-w-[280px] text-xs mt-0.5">{msg.replyPreview}</span>
                </div>
              )}

              {/* Image Preview with click-to-zoom */}
              {msg.imageUrl && (
                <div
                  className="relative group overflow-hidden rounded-xl w-48 md:w-56 cursor-pointer shadow-md border border-gray-700/50 hover:opacity-95 transition-opacity mt-1"
                  onClick={() => setViewingImage(msg.imageUrl!)}
                >
                  <img
                    src={resolveImageUrl(msg.imageUrl)}
                    alt="Aura Visual Asset"
                    referrerPolicy="no-referrer"
                    className="w-full h-auto object-cover max-h-72"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.src = "https://placehold.co/512x512/1e1e2f/ffffff?text=Image+Generating...";
                      target.onerror = null;
                    }}
                  />
                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                    <span className="text-white text-xs font-medium">🔍 Click to zoom</span>
                  </div>
                </div>
              )}

              {/* Video / Reel Player */}
              {msg.videoUrl && (
                <div className="relative overflow-hidden rounded-xl w-56 md:w-64 mt-1 border border-purple-500/30 shadow-lg bg-black/40">
                  <video
                    src={msg.videoUrl}
                    controls
                    playsInline
                    loop
                    autoPlay
                    muted={!msg.audioBase64}
                    className="w-full h-auto object-cover max-h-80"
                  />
                  <div className="absolute top-2 left-2 bg-black/60 backdrop-blur-md px-2 py-0.5 rounded-md text-[10px] text-purple-300 flex items-center gap-1 font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-pulse"></span>
                    Aura Reel
                  </div>
                </div>
              )}

              {/* Voice Note Player */}
              {msg.isVoiceNote ? (
                <div className={`flex items-center gap-3 p-2 rounded-xl ${
                  isUser ? "bg-indigo-500/30 border-indigo-400/30" : "bg-gray-900/50 border-gray-700"
                } border`}>
                  <button
                    onClick={() => {
                      const audio = new Audio(msg.userAudioUrl || (msg.audioBase64 ? `data:audio/mp3;base64,${msg.audioBase64}` : ""));
                      audio.play();
                    }}
                    className={`w-9 h-9 rounded-full flex items-center justify-center transition shadow-md ${
                      isUser ? "bg-white text-indigo-600 hover:bg-gray-100" : "bg-indigo-500 text-white hover:bg-indigo-400"
                    }`}
                  >
                    ▶️
                  </button>
                  <div className="flex-1 h-1.5 bg-gray-950/30 rounded-full overflow-hidden w-24">
                    <div className="w-full h-full bg-current opacity-50"></div>
                  </div>
                  <span className="text-xs font-medium opacity-70">Voice</span>
                </div>
              ) : (
                <div>
                  <span className="whitespace-pre-wrap leading-relaxed text-sm select-text">
                    {highlightMatches(msg.content, searchQuery)}
                  </span>

                  {/* Audio Synthesizer Player for Aura Voice */}
                  {msg.role !== "user" && msg.audioBase64 && (
                    <div className="mt-2">
                      <audio
                        controls
                        controlsList="nodownload noplaybackrate"
                        className="h-8 w-48 opacity-80 drop-shadow-md rounded-md"
                        src={`data:audio/mp3;base64,${msg.audioBase64}`}
                      />
                    </div>
                  )}
                </div>
              )}

              {/* Timestamp & Telegram-style Read Status Checkmarks */}
              <div className="flex items-center justify-end gap-1.5 mt-0.5 text-[10px] opacity-70 select-none">
                {msg.isEdited && <span className="italic mr-0.5 text-[9px]">(edited)</span>}
                {msg.timestamp && <span>{msg.timestamp}</span>}
                {isUser && (
                  <CheckCheck className="w-3.5 h-3.5 text-indigo-200 inline -mb-0.5" />
                )}
              </div>

              {/* Floating Reaction Badge nestled on bubble bottom */}
              {msg.reaction && (
                <div 
                  onClick={() => handleReaction(idx, msg.reaction!)}
                  className={`absolute -bottom-2.5 ${isUser ? "left-3" : "right-3"} bg-gray-900 border border-gray-700/80 rounded-full px-2 py-0.5 text-xs shadow-md hover:scale-120 transition-transform cursor-pointer flex items-center gap-1 z-10`}
                  title="Click to remove reaction"
                >
                  <span>{msg.reaction}</span>
                  <span className="text-[10px] text-gray-400 font-semibold">1</span>
                </div>
              )}
            </div>
          </div>
        );
      })}

      {/* Real-time Streaming Token Preview Bubble */}
      {streamingText && (
        <div className="flex justify-start animate-in fade-in duration-150">
          <div className="max-w-[88%] md:max-w-[72%] rounded-2xl rounded-bl-xs px-4 py-3 shadow-md bg-gray-800/90 text-gray-100 border border-indigo-500/40 backdrop-blur-md">
            <span className="whitespace-pre-wrap leading-relaxed text-sm">{streamingText}</span>
            <span className="inline-block w-1.5 h-4 ml-1 bg-indigo-400 animate-pulse align-middle"></span>
          </div>
        </div>
      )}

      {/* Action / Tool Execution Status Banner */}
      {actionStatus && (
        <div className="flex justify-start">
          <div className="px-3.5 py-1.5 rounded-full bg-indigo-950/70 border border-indigo-500/40 text-indigo-300 text-xs flex items-center gap-2 shadow-lg backdrop-blur-md">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
            {actionStatus}
          </div>
        </div>
      )}

      {/* Typing dots loader */}
      {isLoading && !streamingText && (
        <div className="flex justify-start">
          <div className="bg-gray-800/90 rounded-2xl rounded-bl-xs px-4 py-3 border border-gray-700/60 backdrop-blur-md flex items-center gap-1.5 h-10 w-18 shadow-sm">
            <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
            <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
            <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce"></div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </main>
  );
};
