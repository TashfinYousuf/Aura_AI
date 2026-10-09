"use client";

import React from "react";

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
  setViewingImage: (url: string | null) => void;
  resolveImageUrl: (url?: string | null) => string;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
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
  setViewingImage,
  resolveImageUrl,
  messagesEndRef
}) => {
  return (
    <main className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth pb-32 max-w-4xl mx-auto w-full">
      {messages.map((msg, idx) => (
        <div
          key={msg.id || idx}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in duration-300 relative`}
          onMouseEnter={() => setHoveredMsgIdx(idx)}
          onMouseLeave={() => setHoveredMsgIdx(null)}
        >
          {/* Reaction & Action Bar (Messenger Style) */}
          {hoveredMsgIdx === idx && (
            <div className={`absolute -top-7 ${msg.role === "user" ? "right-4" : "left-4"} bg-gray-900/95 backdrop-blur-md border border-gray-700/80 rounded-full px-2.5 py-1 flex items-center gap-1.5 z-20 shadow-xl animate-in fade-in zoom-in-95 duration-150`}>
              {['❤️', '😢', '🔥', '😆', '👍'].map(emoji => (
                <button
                  key={emoji}
                  onClick={() => handleReaction(idx, emoji)}
                  className={`hover:scale-125 transition-transform text-xs p-1 rounded-full ${msg.reaction === emoji ? "bg-indigo-500/30 scale-110" : ""}`}
                  title={`React ${emoji}`}
                >
                  {emoji}
                </button>
              ))}
              <div className="w-px h-3.5 bg-gray-700 mx-0.5"></div>
              <button
                onClick={() => setReplyingToMsg({ id: msg.id, preview: msg.content.substring(0, 80), role: msg.role })}
                className="text-gray-400 hover:text-indigo-300 p-1 rounded hover:bg-gray-800 transition text-xs"
                title="Reply"
              >
                ↩️
              </button>
              {msg.role === "user" && (
                <button
                  onClick={() => { setInput(msg.content); setEditingMsgIdx(idx); }}
                  className="text-gray-400 hover:text-indigo-300 p-1 rounded hover:bg-gray-800 transition text-xs"
                  title="Edit"
                >
                  ✏️
                </button>
              )}
              {/* Unsend Action Dropdown */}
              <div className="relative group/unsend">
                <button
                  className="text-gray-400 hover:text-rose-400 p-1 rounded hover:bg-gray-800 transition text-xs"
                  title="Unsend"
                >
                  🗑️
                </button>
                <div className="absolute top-full mt-1.5 right-0 hidden group-hover/unsend:flex flex-col bg-gray-900 border border-gray-700 rounded-lg p-1 shadow-2xl z-30 min-w-[140px] text-xs">
                  <button
                    onClick={() => onUnsend(msg.id, false)}
                    className="text-left px-2.5 py-1.5 hover:bg-gray-800 text-gray-300 hover:text-white rounded transition"
                  >
                    Unsend for you
                  </button>
                  {msg.role === "user" && (
                    <button
                      onClick={() => onUnsend(msg.id, true)}
                      className="text-left px-2.5 py-1.5 hover:bg-rose-950/60 text-rose-400 hover:text-rose-300 rounded transition font-medium"
                    >
                      Unsend for everyone
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          <div
            id={`msg-${msg.id}`}
            className={`max-w-[85%] md:max-w-[70%] rounded-2xl px-5 py-3.5 shadow-sm flex flex-col gap-2 relative transition-all duration-300 ${
              msg.role === "user"
                ? "bg-indigo-600 text-white rounded-br-none"
                : "bg-gray-800 text-gray-200 rounded-bl-none border border-gray-700/50"
            }`}
          >
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
                className={`cursor-pointer mb-1 p-2 rounded-lg text-xs border-l-2 transition hover:opacity-90 ${
                  msg.role === "user"
                    ? "bg-indigo-700/60 border-indigo-200 text-indigo-100"
                    : "bg-gray-900/70 border-purple-400 text-gray-300"
                } flex flex-col`}
                title="Click to jump to original message"
              >
                <span className="font-semibold text-[10px] opacity-75">↩️ Replied message</span>
                <span className="truncate max-w-[260px] text-xs">{msg.replyPreview}</span>
              </div>
            )}
            {/* Image Preview with click-to-zoom */}
            {msg.imageUrl && (
              <div
                className="relative group overflow-hidden rounded-xl w-48 md:w-56 cursor-pointer shadow-md border border-gray-700/50 hover:opacity-90 transition-opacity mt-2"
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
              <div className="relative overflow-hidden rounded-2xl w-56 md:w-64 mt-2 border border-purple-500/30 shadow-lg bg-black/40">
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
              <div className={`flex items-center gap-3 p-2 rounded-xl ${msg.role === "user" ? "bg-indigo-500/30 border-indigo-400/30" : "bg-gray-900/50 border-gray-700"} border`}>
                <button
                  onClick={() => {
                    const audio = new Audio(msg.userAudioUrl || (msg.audioBase64 ? `data:audio/mp3;base64,${msg.audioBase64}` : ""));
                    audio.play();
                  }}
                  className={`w-10 h-10 rounded-full flex items-center justify-center transition shadow-md ${msg.role === "user" ? "bg-white text-indigo-600 hover:bg-gray-100" : "bg-indigo-500 text-white hover:bg-indigo-400"}`}
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
                {editingMsgIdx === idx ? (
                  <div className="flex flex-col gap-2 w-full mt-1">
                    <textarea
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      className="bg-gray-900 text-white p-3 rounded-lg w-full text-sm border border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none min-h-15"
                    />
                    <div className="flex gap-2 justify-end">
                      <button
                        onClick={() => { setEditingMsgIdx(null); setInput(""); }}
                        className="text-xs bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded-md transition"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => submitEdit(idx, input)}
                        className="text-xs bg-indigo-600 hover:bg-indigo-500 px-3 py-1.5 rounded-md transition shadow-md"
                      >
                        Save
                      </button>
                    </div>
                  </div>
                ) : (
                  <span className="whitespace-pre-wrap leading-relaxed">{msg.content}</span>
                )}

                {/* Timestamp & Edited status */}
                {(msg.timestamp || msg.isEdited) && (
                  <div className="flex items-center justify-end gap-1 mt-1 opacity-60 text-[10px]">
                    {msg.isEdited && <span className="italic mr-0.5">(edited)</span>}
                    {msg.timestamp && <span>{msg.timestamp}</span>}
                  </div>
                )}

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

            {/* Reaction Badge */}
            {msg.reaction && (
              <div className={`absolute -bottom-3 ${msg.role === "user" ? "left-3" : "right-3"} bg-gray-900 border border-gray-700 rounded-full px-1.5 py-0.5 text-xs shadow-md hover:scale-125 transition-transform cursor-pointer`}>
                {msg.reaction}
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Real-time Streaming Token Preview Bubble */}
      {streamingText && (
        <div className="flex justify-start animate-in fade-in duration-150">
          <div className="max-w-[85%] md:max-w-[70%] rounded-2xl px-5 py-3.5 shadow-sm bg-gray-800 text-gray-200 rounded-bl-none border border-indigo-500/30">
            <span className="whitespace-pre-wrap leading-relaxed">{streamingText}</span>
            <span className="inline-block w-1.5 h-4 ml-1 bg-indigo-400 animate-pulse align-middle"></span>
          </div>
        </div>
      )}

      {/* Action / Tool Execution Status Banner */}
      {actionStatus && (
        <div className="flex justify-start">
          <div className="px-3 py-1.5 rounded-full bg-indigo-950/60 border border-indigo-500/40 text-indigo-300 text-xs flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
            {actionStatus}
          </div>
        </div>
      )}

      {/* Typing dots loader */}
      {isLoading && !streamingText && (
        <div className="flex justify-start">
          <div className="bg-gray-800 rounded-2xl rounded-bl-none px-5 py-4 border border-gray-700/50 flex items-center gap-2 h-12 w-20">
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

