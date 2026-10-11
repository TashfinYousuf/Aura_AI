"use client";

import React, { useRef, useEffect } from "react";
import { Mic, Send, Square, ImagePlus, Check, Edit3 } from "lucide-react";

interface ComposerProps {
  input: string;
  setInput: (val: string) => void;
  selectedImage: File | null;
  setSelectedImage: (file: File | null) => void;
  isRecording: boolean;
  toggleRecording: () => void;
  handleTextSend: (e?: React.FormEvent) => void;
  isLoading: boolean;
  replyingToMsg: { id: string; preview: string; role: 'ai' | 'user' } | null;
  setReplyingToMsg: (item: { id: string; preview: string; role: 'ai' | 'user' } | null) => void;
  editingMsg?: { id: string; content: string; idx: number } | null;
  onCancelEdit?: () => void;
  onSubmitEdit?: (content: string) => void;
}

export const Composer: React.FC<ComposerProps> = ({
  input,
  setInput,
  selectedImage,
  setSelectedImage,
  isRecording,
  toggleRecording,
  handleTextSend,
  isLoading,
  replyingToMsg,
  setReplyingToMsg,
  editingMsg = null,
  onCancelEdit,
  onSubmitEdit
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height like Messenger / Telegram
  const adjustTextareaHeight = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [input]);

  useEffect(() => {
    if (replyingToMsg || editingMsg) {
      textareaRef.current?.focus();
      if (editingMsg && textareaRef.current) {
        const len = textareaRef.current.value.length;
        textareaRef.current.setSelectionRange(len, len);
      }
    }
  }, [replyingToMsg, editingMsg]);

  return (
    <footer className="flex-none p-3 sm:p-4 bg-gray-900 border-t border-gray-800">
      {/* 1. Telegram / Messenger Quoted Reply Preview Bar */}
      {replyingToMsg && (
        <div className="max-w-3xl mx-auto mb-2 bg-gray-900 border border-gray-700 rounded-xl p-2.5 flex justify-between items-center text-sm shadow-md animate-in slide-in-from-bottom-2">
          <div className="flex flex-col border-l-2 border-indigo-500 pl-2.5 overflow-hidden">
            <span className="text-indigo-400 font-medium text-xs">
              Replying to {replyingToMsg.role === 'ai' ? 'Aura' : 'yourself'}
            </span>
            <span className="text-gray-300 text-xs truncate max-w-sm mt-0.5">{replyingToMsg.preview}</span>
          </div>
          <button
            onClick={() => setReplyingToMsg(null)}
            className="text-gray-400 hover:text-white p-1 text-xs rounded hover:bg-gray-800 transition"
          >
            ✕
          </button>
        </div>
      )}

      {/* 2. Telegram / Messenger Editing Message Banner */}
      {editingMsg && (
        <div className="max-w-3xl mx-auto mb-2 bg-gray-900 border border-indigo-500/60 rounded-xl p-2.5 flex justify-between items-center text-sm shadow-xl animate-in slide-in-from-bottom-2">
          <div className="flex items-center gap-2.5 border-l-2 border-indigo-400 pl-2.5 overflow-hidden">
            <Edit3 className="w-4 h-4 text-indigo-400 shrink-0" />
            <div className="flex flex-col overflow-hidden">
              <span className="text-indigo-300 font-semibold text-xs flex items-center gap-1">
                Editing message
              </span>
              <span className="text-gray-400 text-xs truncate max-w-sm sm:max-w-md mt-0.5">{editingMsg.content}</span>
            </div>
          </div>
          <button
            type="button"
            onClick={onCancelEdit}
            className="text-gray-400 hover:text-white p-1 text-xs rounded hover:bg-gray-800 transition ml-2 shrink-0"
            title="Cancel editing"
          >
            ✕
          </button>
        </div>
      )}

      {/* 3. Attached Image Thumbnail Preview */}
      {selectedImage && (
        <div className="max-w-3xl mx-auto flex items-center gap-2 p-2 mb-2 bg-gray-800/80 rounded-lg w-fit border border-purple-500/30">
          <img
            src={URL.createObjectURL(selectedImage)}
            alt="Selected attachment"
            className="w-12 h-12 object-cover rounded-md"
          />
          <span className="text-xs text-gray-300 max-w-[140px] truncate">{selectedImage.name}</span>
          <button
            type="button"
            onClick={() => setSelectedImage(null)}
            className="text-red-400 hover:text-red-300 text-sm font-bold ml-1"
          >
            ✕
          </button>
        </div>
      )}

      {/* 4. Expandable Messenger/Telegram Style Input Box */}
      <div className="max-w-3xl mx-auto flex items-end gap-2 bg-gray-900 border border-gray-700/80 focus-within:border-indigo-500/70 rounded-3xl p-2 shadow-2xl transition-all">
        {/* Hidden File Input */}
        <input
          type="file"
          accept="image/*"
          className="hidden"
          ref={fileInputRef}
          onChange={(e) => setSelectedImage(e.target.files?.[0] || null)}
        />

        {/* Image Attachment Trigger */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          className={`p-2.5 rounded-full transition-all shrink-0 mb-0.5 ${
            selectedImage
              ? "text-indigo-400 bg-indigo-500/20"
              : "text-gray-400 hover:text-indigo-400 hover:bg-gray-800"
          }`}
          title="Attach Photo"
        >
          <ImagePlus className="w-5 h-5" />
        </button>

        {/* Voice Note Recording Trigger */}
        <button
          type="button"
          onClick={toggleRecording}
          className={`p-2.5 rounded-full transition-all duration-300 shrink-0 mb-0.5 ${
            isRecording ? "bg-red-500 text-white animate-pulse" : "bg-gray-800 text-gray-400 hover:text-indigo-400"
          }`}
          title={isRecording ? "Stop Recording" : "Record Voice Note"}
        >
          {isRecording ? <Square className="w-5 h-5 fill-current" /> : <Mic className="w-5 h-5" />}
        </button>

        {/* Expandable Textarea & Action Button */}
        <div className="flex-1 flex items-end gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                if (editingMsg && onSubmitEdit) {
                  if (input.trim()) onSubmitEdit(input);
                } else {
                  handleTextSend(e);
                }
              } else if (e.key === "Escape" && editingMsg && onCancelEdit) {
                e.preventDefault();
                onCancelEdit();
              }
            }}
            placeholder={
              editingMsg
                ? "Edit your message..."
                : selectedImage
                ? "Add a message about the image..."
                : "Tell me what's on your mind..."
            }
            className="w-full bg-transparent border-none focus:ring-0 text-white placeholder-gray-500 text-[15px] px-2 py-2 outline-none resize-none max-h-36 overflow-y-auto leading-relaxed"
            disabled={isLoading || isRecording}
          />

          <button
            type="button"
            onClick={(e) => {
              if (editingMsg && onSubmitEdit) {
                if (input.trim()) onSubmitEdit(input);
              } else {
                handleTextSend(e);
              }
            }}
            disabled={(!input.trim() && !selectedImage) || isLoading}
            className={`p-2.5 rounded-full transition-all shrink-0 mb-0.5 shadow-md ${
              editingMsg
                ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30"
                : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-indigo-600/20"
            } disabled:opacity-50 disabled:hover:bg-indigo-600`}
            title={editingMsg ? "Save Changes" : "Send Message"}
          >
            {editingMsg ? (
              <Check className="w-5 h-5" />
            ) : (
              <Send className="w-5 h-5 ml-0.5" />
            )}
          </button>
        </div>
      </div>
    </footer>
  );
};
