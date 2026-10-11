"use client";

import React, { useRef } from "react";
import { Mic, Send, Square, ImagePlus } from "lucide-react";

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
  setReplyingToMsg
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textInputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    if (replyingToMsg) {
      textInputRef.current?.focus();
    }
  }, [replyingToMsg]);

  return (
    <footer className="flex-none p-4 bg-gray-900 border-t border-gray-800">
      {/* Reply Preview Bar */}
      {replyingToMsg && (
        <div className="max-w-3xl mx-auto mb-2 bg-gray-900 border border-gray-700 rounded-lg p-2.5 flex justify-between items-center text-sm shadow-md animate-in slide-in-from-bottom-2">
          <div className="flex flex-col border-l-2 border-indigo-500 pl-2.5">
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

      {/* Attached Image Thumbnail Preview */}
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

      <div className="max-w-3xl mx-auto flex items-center gap-2 bg-gray-900 border border-gray-700 rounded-full p-2 shadow-2xl">
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
          className={`p-3 rounded-full transition-all shrink-0 ${
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
          className={`p-3 rounded-full transition-all duration-300 shrink-0 ${
            isRecording ? "bg-red-500 text-white animate-pulse" : "bg-gray-800 text-gray-400 hover:text-indigo-400"
          }`}
          title={isRecording ? "Stop Recording" : "Record Voice Note"}
        >
          {isRecording ? <Square className="w-5 h-5 fill-current" /> : <Mic className="w-5 h-5" />}
        </button>

        {/* Text Input & Submit */}
        <form onSubmit={handleTextSend} className="flex-1 flex items-center gap-2">
          <input
            ref={textInputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={selectedImage ? "Add a message about the image..." : "Tell me what's on your mind..."}
            className="w-full bg-transparent border-none focus:ring-0 text-white placeholder-gray-500 text-[15px] px-2 outline-none"
            disabled={isLoading || isRecording}
          />

          <button
            type="submit"
            disabled={(!input.trim() && !selectedImage) || isLoading}
            className="p-3 bg-indigo-600 text-white rounded-full hover:bg-indigo-700 disabled:opacity-50 disabled:hover:bg-indigo-600 transition-colors shrink-0 shadow-md shadow-indigo-600/20"
            title="Send Message"
          >
            <Send className="w-5 h-5 ml-0.5" />
          </button>
        </form>
      </div>
    </footer>
  );
};

