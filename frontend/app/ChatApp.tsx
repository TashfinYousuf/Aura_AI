"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import axios from "axios";
import { signOut, User } from "firebase/auth";
import { auth } from "./firebase";
import MoodDashboard from "./MoodDashboard";
import GoalTracker from "./GoalTracker";
import { MessageList, Message } from "./components/MessageList";
import { Composer } from "./components/Composer";
import { CompanionPanel } from "./components/CompanionPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? `http://${window.location.hostname}:8000` : "http://127.0.0.1:8000");
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || (typeof window !== "undefined" ? `ws://${window.location.hostname}:8000` : "ws://127.0.0.1:8000");

export default function ChatApp({ currentUser }: { currentUser: User }) {
  const [messages, setMessages] = useState<Message[]>([
    { id: "init-msg", role: "ai", content: "হেই... আমি আছি। দিনটা কেমন কাটলো তোমার?" },
  ]);
  const [streamingText, setStreamingText] = useState<string>("");
  const [actionStatus, setActionStatus] = useState<string | null>(null);
  const [presentationMode, setPresentationMode] = useState<"private" | "public" | "adult">("private");

  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState<File | null>(null);
  const [relationship, setRelationship] = useState({ level: 1, title: "Acquaintance", progress: 0 });
  const [isRecording, setIsRecording] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [isIncognito, setIsIncognito] = useState(false);
  const [showMediaGallery, setShowMediaGallery] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [hoveredMsgIdx, setHoveredMsgIdx] = useState<number | null>(null);
  const [replyingToMsg, setReplyingToMsg] = useState<{ id: string; preview: string; role: 'ai' | 'user' } | null>(null);
  const [editingMsgIdx, setEditingMsgIdx] = useState<number | null>(null);
  const [viewingImage, setViewingImage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const activeMediaStream = useRef<MediaStream | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  const recordingStartTime = useRef<number>(0);

  useEffect(() => {
    if ("Notification" in window && Notification.permission !== "granted") {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText]);

  // Load Previous Chat History
  const loadChatHistory = useCallback(async () => {
    if (!currentUser?.uid) return;
    try {
      const res = await axios.get(`${API_BASE}/api/chat/history/${currentUser.uid}?t=${Date.now()}`);
      if (Array.isArray(res.data) && res.data.length > 0) {
        setMessages(res.data);
      } else if (res.data?.status === "success" && res.data?.history?.length > 0) {
        setMessages(res.data.history);
      }
    } catch (err) {
      console.warn("Could not load chat history:", err);
    }
  }, [currentUser?.uid]);

  // Relationship Progression Analytics
  useEffect(() => {
    if (!currentUser?.uid || messages.length <= 1) return;
    const fetchRel = async () => {
      try {
        const res = await axios.get(`${API_BASE}/api/analytics/relationship/${currentUser.uid}`);
        if (res.data) {
          setRelationship({
            level: res.data.current_level,
            title: res.data.title,
            progress: res.data.progress_to_next_level
          });
        }
      } catch (err) {
        console.error("Relationship load error:", err);
      }
    };
    fetchRel();
  }, [messages.length, currentUser?.uid]);

  // Master WebSocket Stream Lifecycle
  useEffect(() => {
    if (!currentUser?.uid) return;

    loadChatHistory();

    const connectWS = () => {
      const socket = new WebSocket(`${WS_BASE}/api/voice/ws/live-chat/${currentUser.uid}`);
      ws.current = socket;

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "message_start") {
            setStreamingText("");
            setIsLoading(true);
          } else if (data.type === "token") {
            setStreamingText((prev) => prev + data.content);
          } else if (data.type === "action_start") {
            const desc = data.action === "generate_image"
              ? `Aura is taking a photo at ${data.scene || "desk"}... 📸`
              : `Executing ${data.action}...`;
            setActionStatus(desc);
          } else if (data.type === "action_complete") {
            setActionStatus(null);
          } else if (data.type === "reaction_updated") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === data.message_id ? { ...m, reaction: data.emoji || undefined } : m
              )
            );
          } else if (data.type === "message_unsent") {
            setMessages((prev) => prev.filter((m) => m.id !== data.message_id));
          } else if (data.type === "message_edited") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === data.message_id ? { ...m, content: data.new_content, isEdited: true } : m
              )
            );
          } else if (data.type === "reply") {
            const finalImageUrl = data.image_url?.startsWith('/') ? `${API_BASE}${data.image_url}` : data.image_url;
            const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            setMessages((prev) => [
              ...prev,
              {
                id: data.id || Date.now().toString(),
                role: "ai",
                content: data.content,
                audioBase64: data.audio_base64,
                isVoiceNote: data.is_voice_note,
                imageUrl: finalImageUrl,
                videoUrl: data.video_url,
                reaction: data.reaction,
                replyTo: data.replyTo || data.reply_to,
                replyPreview: data.replyPreview || data.reply_preview,
                timestamp: data.timestamp || nowTime
              },
            ]);
            setStreamingText("");
            setActionStatus(null);
            setIsLoading(false);

            // Trigger browser notification if user is on another tab/window
            if (typeof document !== "undefined" && document.hidden && "Notification" in window && Notification.permission === "granted") {
              try {
                new Notification("Aura 💜", {
                  body: data.content ? data.content.slice(0, 100) : "New message from Aura",
                  icon: "/favicon.ico"
                });
              } catch (e) {
                console.warn("Notification error:", e);
              }
            }
          } else if (data.type === "message_complete") {
            setStreamingText("");
            setIsLoading(false);
          }
        } catch (err) {
          console.error("WS Parse error:", err);
          setIsLoading(false);
        }
      };

      socket.onerror = () => {
        setIsLoading(false);
      };

      socket.onclose = () => {
        reconnectTimeoutRef.current = setTimeout(connectWS, 3000);
      };
    };

    connectWS();

    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (ws.current) {
        ws.current.onclose = null;
        ws.current.close();
      }
    };
  }, [currentUser?.uid, loadChatHistory]);

  const convertToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve((reader.result as string).split(",")[1]);
      reader.onerror = reject;
    });
  };

  const handleTextSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() && !selectedImage) return;

    const userText = input.trim() || "📸 Sent an image";
    let base64Image: string | null = null;
    let localPreviewUrl: string | null = null;

    if (selectedImage) {
      try {
        base64Image = await convertToBase64(selectedImage);
        localPreviewUrl = URL.createObjectURL(selectedImage);
      } catch (err) {
        console.error("Image process error:", err);
      }
    }

    const replyingSnapshot = replyingToMsg;
    const tempId = `user-${Date.now()}`;
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    setMessages((prev) => [
      ...prev,
      {
        id: tempId,
        role: "user",
        content: userText,
        imageUrl: localPreviewUrl || undefined,
        replyTo: replyingSnapshot?.id,
        replyPreview: replyingSnapshot?.preview,
        timestamp: nowTime
      }
    ]);

    setInput("");
    setSelectedImage(null);
    setReplyingToMsg(null);
    setIsLoading(true);

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: "text",
        content: userText,
        image_base64: base64Image,
        incognito: isIncognito,
        presentation_mode: presentationMode,
        reply_to: replyingSnapshot?.id,
        reply_preview: replyingSnapshot?.preview
      }));
    } else {
      console.warn("WebSocket is offline.");
      setIsLoading(false);
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      mediaRecorder.current?.stop();
      setIsRecording(false);
    } else {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        activeMediaStream.current = stream;
        mediaRecorder.current = new MediaRecorder(stream);
        audioChunks.current = [];
        recordingStartTime.current = Date.now();

        mediaRecorder.current.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.current.push(e.data);
        };

        mediaRecorder.current.onstop = () => {
          const duration = Date.now() - recordingStartTime.current;

          // Release hardware mic track immediately
          if (activeMediaStream.current) {
            activeMediaStream.current.getTracks().forEach((track) => track.stop());
            activeMediaStream.current = null;
          }

          if (duration < 1000) {
            console.warn("Recording was too short, cancelled.");
            return;
          }

          const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
          const userAudioObjectUrl = URL.createObjectURL(audioBlob);

          const reader = new FileReader();
          reader.readAsDataURL(audioBlob);
          reader.onloadend = () => {
            const base64Audio = (reader.result as string).split(',')[1];
            setMessages((prev) => [
              ...prev,
              {
                id: `voice-${Date.now()}`,
                role: 'user',
                content: "🎤 Voice Message",
                isVoiceNote: true,
                userAudioUrl: userAudioObjectUrl
              }
            ]);
            setIsLoading(true);

            if (ws.current && ws.current.readyState === WebSocket.OPEN) {
              ws.current.send(JSON.stringify({
                type: "audio",
                content: base64Audio,
                incognito: isIncognito,
                presentation_mode: presentationMode
              }));
            } else {
              setIsLoading(false);
            }
          };
        };

        mediaRecorder.current.start();
        setIsRecording(true);
      } catch (err) {
        console.error("Microphone access error:", err);
      }
    }
  };

  const handleClearHistory = async () => {
    try {
      await axios.delete(`${API_BASE}/api/chat/history/${currentUser.uid}`);
      setMessages([]);
    } catch (err) {
      console.error("Failed to delete history:", err);
    }
  };

  const handleReaction = (idx: number, emoji: string) => {
    const msgId = messages[idx].id;
    const currentReaction = messages[idx].reaction;
    const finalEmoji = currentReaction === emoji ? undefined : emoji;

    setMessages((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], reaction: finalEmoji };
      return copy;
    });
    setHoveredMsgIdx(null);

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "reaction", message_id: msgId, emoji: finalEmoji || null }));
    }
  };

  const submitEdit = (idx: number, newContent: string) => {
    const msgId = messages[idx].id;
    setMessages((prev) => {
      const copy = [...prev];
      copy[idx] = { ...copy[idx], content: newContent };
      return copy;
    });
    setEditingMsgIdx(null);
    setInput("");

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "edit", message_id: msgId, new_content: newContent }));
    }
  };

  const handleUnsend = async (msgId: string, everyone: boolean) => {
    // 1. Remove immediately from local state
    setMessages((prev) => prev.filter((m) => m.id !== msgId));

    if (everyone) {
      // 2. Broadcast via WebSocket
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: "unsend", message_id: msgId }));
      }
      // 3. Resilient fallback via REST
      try {
        await axios.delete(`${API_BASE}/api/chat/message/${currentUser.uid}/${msgId}`);
      } catch (err) {
        console.warn("Unsend REST sync notice:", err);
      }
    }
  };

  const resolveImageUrl = (url?: string | null) => {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) {
      return url;
    }
    return `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
  };

  return (
    <div className="flex flex-col h-dvh w-full bg-gray-950 overflow-hidden">
      {/* 1. Header Toolbar & Companion Panel */}
      <CompanionPanel
        relationship={relationship}
        presentationMode={presentationMode}
        setPresentationMode={setPresentationMode}
        isIncognito={isIncognito}
        setIsIncognito={setIsIncognito}
        showMediaGallery={showMediaGallery}
        setShowMediaGallery={setShowMediaGallery}
        showDashboard={showDashboard}
        setShowDashboard={setShowDashboard}
        onClearChat={() => setShowClearConfirm(true)}
        onSignOut={() => signOut(auth)}
      />

      {/* Analytics Drawers */}
      {showDashboard && (
        <div className="px-4 pt-4 border-b border-gray-800 bg-gray-900/30">
          <MoodDashboard currentUser={currentUser} />
          <GoalTracker currentUser={currentUser} />
        </div>
      )}

      {/* 2. Message History & Streaming Area */}
      <MessageList
        messages={messages}
        streamingText={streamingText}
        actionStatus={actionStatus}
        isLoading={isLoading}
        hoveredMsgIdx={hoveredMsgIdx}
        setHoveredMsgIdx={setHoveredMsgIdx}
        editingMsgIdx={editingMsgIdx}
        setEditingMsgIdx={setEditingMsgIdx}
        input={input}
        setInput={setInput}
        handleReaction={handleReaction}
        setReplyingToMsg={setReplyingToMsg}
        submitEdit={submitEdit}
        onUnsend={handleUnsend}
        setViewingImage={setViewingImage}
        resolveImageUrl={resolveImageUrl}
        messagesEndRef={messagesEndRef}
      />

      {/* 3. Composer & Input Bar */}
      <Composer
        input={input}
        setInput={setInput}
        selectedImage={selectedImage}
        setSelectedImage={setSelectedImage}
        isRecording={isRecording}
        toggleRecording={toggleRecording}
        handleTextSend={handleTextSend}
        isLoading={isLoading}
        replyingToMsg={replyingToMsg}
        setReplyingToMsg={setReplyingToMsg}
      />

      {/* Clear Chat Confirmation Modal */}
      {showClearConfirm && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-in fade-in">
          <div className="bg-gray-900 border border-gray-700 p-6 rounded-2xl max-w-sm w-full mx-4 shadow-2xl">
            <h3 className="text-xl font-bold text-white mb-2">Clear All Chats?</h3>
            <p className="text-gray-400 text-sm mb-6">Are you sure you want to delete this conversation? This will permanently wipe our chat history.</p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="px-4 py-2 bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition"
              >
                Cancel
              </button>
              <button
                onClick={() => { handleClearHistory(); setShowClearConfirm(false); }}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition shadow-lg shadow-red-900/50"
              >
                Yes, Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Media Gallery Section */}
      {showMediaGallery && (
        <div className="absolute inset-0 bg-gray-950/95 z-40 flex flex-col p-6 animate-in fade-in slide-in-from-bottom-10">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-linear-to-r from-pink-400 to-indigo-400">Media & Voice Notes</h2>
            <button onClick={() => setShowMediaGallery(false)} className="p-2 bg-gray-800 rounded-full text-white hover:bg-gray-700">✕</button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 overflow-y-auto pb-20">
            {messages.filter(m => m.imageUrl || m.isVoiceNote).reverse().map((media, i) => (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-3 flex flex-col gap-2 shadow-lg">
                {media.imageUrl && (
                  <img
                    src={resolveImageUrl(media.imageUrl)}
                    alt="Aura Asset"
                    className="w-full max-h-72 sm:max-h-80 object-cover rounded-xl mt-2 shadow-md border border-gray-700/50"
                    loading="lazy"
                  />
                )}
                {media.isVoiceNote && (
                  <audio controls className="w-full h-8" src={media.userAudioUrl || `data:audio/mp3;base64,${media.audioBase64}`} />
                )}
                <span className="text-xs text-gray-500 text-center">{media.role === 'ai' ? 'Aura' : 'You'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Click-to-Zoom Modal */}
      {viewingImage && (
        <div
          className="fixed inset-0 bg-black/95 z-50 flex items-center justify-center p-4 cursor-pointer"
          onClick={() => setViewingImage(null)}
        >
          <img
            src={resolveImageUrl(viewingImage)}
            alt="Full View"
            className="max-w-full max-h-full rounded-lg object-contain shadow-2xl"
          />
        </div>
      )}
    </div>
  );
}