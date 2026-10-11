"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import axios from "axios";
import { signOut, User } from "firebase/auth";
import { auth } from "./firebase";
import MoodDashboard from "./MoodDashboard";
import GoalTracker from "./GoalTracker";
import { MessageList, Message } from "./components/MessageList";
import { Composer } from "./components/Composer";
import { CompanionPanel } from "./components/CompanionPanel";
import { 
  Pin, X, Search, Palette, ChevronUp, ChevronDown, Check, 
  Download, Bookmark, Sparkles, CheckCheck 
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" ? `http://${window.location.hostname}:8000` : "http://127.0.0.1:8000");
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || (typeof window !== "undefined" ? `ws://${window.location.hostname}:8000` : "ws://127.0.0.1:8000");

export type ChatThemeKey = "midnight" | "telegram" | "rose" | "emerald" | "cyberpunk" | "custom";

export interface ThemeConfig {
  key: ChatThemeKey;
  name: string;
  bgClass: string;
  accent: string;
  previewColor: string;
}

export const THEME_PRESETS: ThemeConfig[] = [
  { key: "midnight", name: "Midnight Velvet", bgClass: "bg-[#090a10]", accent: "#6366f1", previewColor: "#1e1b4b" },
  { key: "telegram", name: "Telegram Dark", bgClass: "bg-[#0e1621]", accent: "#5288c1", previewColor: "#17212b" },
  { key: "rose", name: "Romantic Rose", bgClass: "bg-[#130712]", accent: "#f43f5e", previewColor: "#381028" },
  { key: "emerald", name: "Emerald Slate", bgClass: "bg-[#06140f]", accent: "#10b981", previewColor: "#0f2e21" },
  { key: "cyberpunk", name: "Cyberpunk Neon", bgClass: "bg-[#070914]", accent: "#a855f7", previewColor: "#22143b" },
  { key: "custom", name: "Custom Wallpaper", bgClass: "bg-gray-950", accent: "#8b5cf6", previewColor: "#312e81" }
];

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
  const [galleryItems, setGalleryItems] = useState<any[]>([]);
  const [isLoadingGallery, setIsLoadingGallery] = useState(false);
  const [galleryFilter, setGalleryFilter] = useState<'all' | 'photos' | 'voice'>('all');
  const [showDashboard, setShowDashboard] = useState(false);
  const [hoveredMsgIdx, setHoveredMsgIdx] = useState<number | null>(null);
  const [replyingToMsg, setReplyingToMsg] = useState<{ id: string; preview: string; role: 'ai' | 'user' } | null>(null);
  const [editingMsgIdx, setEditingMsgIdx] = useState<number | null>(null);
  const [viewingImage, setViewingImage] = useState<string | null>(null);

  // New Telegram + Messenger Hybrid Features
  const [pinnedMessageId, setPinnedMessageId] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMatchIdx, setSearchMatchIdx] = useState(0);
  const [showThemeModal, setShowThemeModal] = useState(false);
  const [chatTheme, setChatTheme] = useState<ChatThemeKey>("midnight");
  const [customWallpaper, setCustomWallpaper] = useState("");
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const activeMediaStream = useRef<MediaStream | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  const recordingStartTime = useRef<number>(0);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Load Persisted Local Preferences
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedTheme = localStorage.getItem("aura_chat_theme") as ChatThemeKey;
      if (savedTheme) setChatTheme(savedTheme);
      const savedWall = localStorage.getItem("aura_custom_wallpaper");
      if (savedWall) setCustomWallpaper(savedWall);
      const savedPin = localStorage.getItem("aura_pinned_msg_id");
      if (savedPin) setPinnedMessageId(savedPin);
    }
  }, []);

  const showToast = useCallback((text: string) => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    setToastMessage(text);
    toastTimeoutRef.current = setTimeout(() => {
      setToastMessage(null);
    }, 2500);
  }, []);

  useEffect(() => {
    if ("Notification" in window && Notification.permission !== "granted") {
      Notification.requestPermission();
    }
  }, []);

  useEffect(() => {
    if (!isSearching) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingText, isSearching]);

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

  // Dedicated Complete Media Gallery Loader
  const fetchMediaGallery = useCallback(async () => {
    if (!currentUser?.uid) return;
    setIsLoadingGallery(true);
    try {
      const res = await axios.get(`${API_BASE}/api/chat/media/${currentUser.uid}?t=${Date.now()}`);
      if (res.data?.status === "success" && Array.isArray(res.data?.media)) {
        setGalleryItems(res.data.media);
      }
    } catch (err) {
      console.warn("Could not load media gallery:", err);
    } finally {
      setIsLoadingGallery(false);
    }
  }, [currentUser?.uid]);

  useEffect(() => {
    if (showMediaGallery) {
      fetchMediaGallery();
    }
  }, [showMediaGallery, fetchMediaGallery]);

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
                userAudioUrl: userAudioObjectUrl,
                timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
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
      setPinnedMessageId(null);
      localStorage.removeItem("aura_pinned_msg_id");
      showToast("Conversation cleared");
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
      copy[idx] = { ...copy[idx], content: newContent, isEdited: true };
      return copy;
    });
    setEditingMsgIdx(null);
    setInput("");
    showToast("Message updated! ✏️");

    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "edit", message_id: msgId, new_content: newContent }));
    }
  };

  const handleUnsend = async (msgId: string, everyone: boolean) => {
    setMessages((prev) => prev.filter((m) => m.id !== msgId));
    if (pinnedMessageId === msgId) {
      setPinnedMessageId(null);
      localStorage.removeItem("aura_pinned_msg_id");
    }
    showToast(everyone ? "Unsent for everyone 🗑️" : "Deleted for you");

    if (everyone) {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.send(JSON.stringify({ type: "unsend", message_id: msgId }));
      }
      try {
        await axios.delete(`${API_BASE}/api/chat/message/${currentUser.uid}/${msgId}`);
      } catch (err) {
        console.warn("Unsend REST sync notice:", err);
      }
    }
  };

  // Pin & Unpin Handler
  const handlePinMessage = (msgId: string) => {
    if (pinnedMessageId === msgId) {
      setPinnedMessageId(null);
      localStorage.removeItem("aura_pinned_msg_id");
      showToast("Message unpinned");
    } else {
      setPinnedMessageId(msgId);
      localStorage.setItem("aura_pinned_msg_id", msgId);
      showToast("Message pinned to top 📌");
    }
  };

  // Save / Bookmark Handler
  const handleSaveMessage = (msgId: string) => {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id === msgId) {
          const nextSaved = !m.isSaved;
          showToast(nextSaved ? "Message bookmarked 🔖" : "Bookmark removed");
          return { ...m, isSaved: nextSaved };
        }
        return m;
      })
    );
  };

  // Export Chat History Handler (.txt download)
  const handleExportChat = () => {
    if (messages.length === 0) {
      showToast("No messages to export");
      return;
    }
    const dateStr = new Date().toISOString().split("T")[0];
    let exportText = `==================================================\n`;
    exportText += `AURA AI — CONVERSATION EXPORT\n`;
    exportText += `Export Timestamp: ${new Date().toLocaleString()}\n`;
    exportText += `Participant: ${currentUser.email || currentUser.uid}\n`;
    exportText += `Total Messages: ${messages.length}\n`;
    exportText += `==================================================\n\n`;

    messages.forEach((m) => {
      const sender = m.role === "ai" ? "Aura 💜" : "You 👤";
      const time = m.timestamp ? `[${m.timestamp}] ` : "";
      exportText += `${time}${sender}:\n${m.content}\n`;
      if (m.imageUrl) exportText += `[Media Attachment: ${m.imageUrl}]\n`;
      if (m.reaction) exportText += `[Reaction: ${m.reaction}]\n`;
      exportText += `--------------------------------------------------\n\n`;
    });

    const blob = new Blob([exportText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Aura_Chat_Export_${dateStr}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast("Chat history exported (.txt) 📥");
  };

  // Inline Search Filter
  const searchMatches = useMemo(() => {
    if (!searchQuery.trim()) return [];
    return messages.filter((m) =>
      m.content.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }, [messages, searchQuery]);

  const activeMatch = searchMatches[searchMatchIdx] || null;

  const handleNextSearchMatch = () => {
    if (searchMatches.length === 0) return;
    const nextIdx = (searchMatchIdx + 1) % searchMatches.length;
    setSearchMatchIdx(nextIdx);
    const target = document.getElementById(`msg-${searchMatches[nextIdx].id}`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const handlePrevSearchMatch = () => {
    if (searchMatches.length === 0) return;
    const prevIdx = (searchMatchIdx - 1 + searchMatches.length) % searchMatches.length;
    setSearchMatchIdx(prevIdx);
    const target = document.getElementById(`msg-${searchMatches[prevIdx].id}`);
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const resolveImageUrl = (url?: string | null) => {
    if (!url) return "";
    if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("data:")) {
      return url;
    }
    return `${API_BASE}${url.startsWith("/") ? "" : "/"}${url}`;
  };

  const pinnedMsg = messages.find((m) => m.id === pinnedMessageId);
  const activeThemeObj = THEME_PRESETS.find((t) => t.key === chatTheme) || THEME_PRESETS[0];

  return (
    <div 
      className={`flex flex-col h-dvh w-full ${activeThemeObj.bgClass} overflow-hidden transition-colors duration-300 relative`}
      style={
        chatTheme === "custom" && customWallpaper
          ? {
              backgroundImage: customWallpaper.startsWith("http") ? `url(${customWallpaper})` : customWallpaper,
              backgroundSize: "cover",
              backgroundPosition: "center"
            }
          : undefined
      }
    >
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
        onOpenSearch={() => {
          setIsSearching(true);
          setSearchQuery("");
        }}
        onOpenThemeModal={() => setShowThemeModal(true)}
        onExportChat={handleExportChat}
      />

      {/* Telegram-style Pinned Message Banner */}
      {pinnedMsg && (
        <div 
          onClick={() => {
            const target = document.getElementById(`msg-${pinnedMsg.id}`);
            if (target) {
              target.scrollIntoView({ behavior: 'smooth', block: 'center' });
              target.classList.add('ring-2', 'ring-indigo-400', 'ring-offset-2', 'ring-offset-gray-950');
              setTimeout(() => {
                target.classList.remove('ring-2', 'ring-indigo-400', 'ring-offset-2', 'ring-offset-gray-950');
              }, 2000);
            }
          }}
          className="bg-gray-900/90 backdrop-blur-md border-b border-indigo-500/30 px-4 py-2 flex items-center justify-between text-xs cursor-pointer hover:bg-gray-850 transition z-20 shadow-sm"
        >
          <div className="flex items-center gap-2 overflow-hidden">
            <Pin className="w-3.5 h-3.5 text-indigo-400 shrink-0 fill-indigo-400/30" />
            <span className="font-semibold text-indigo-300 shrink-0">Pinned Message:</span>
            <span className="text-gray-300 truncate max-w-sm sm:max-w-md">{pinnedMsg.content || "Media"}</span>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handlePinMessage(pinnedMsg.id);
            }}
            className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-800 transition"
            title="Unpin message"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Telegram-style Inline Search Banner */}
      {isSearching && (
        <div className="bg-gray-900/95 backdrop-blur-md border-b border-gray-800 px-4 py-2 flex items-center justify-between gap-3 text-xs z-20 shadow-md animate-in slide-in-from-top duration-200">
          <div className="flex items-center gap-2 flex-1 max-w-md bg-gray-950 px-3 py-1.5 rounded-xl border border-gray-700 focus-within:border-indigo-500">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setSearchMatchIdx(0);
              }}
              placeholder="Search conversation..."
              className="bg-transparent text-white outline-none w-full text-xs placeholder-gray-500"
              autoFocus
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="text-gray-500 hover:text-gray-300">
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-gray-400 text-[11px] whitespace-nowrap">
              {searchMatches.length > 0
                ? `${searchMatchIdx + 1} of ${searchMatches.length}`
                : searchQuery
                ? "No matches"
                : ""}
            </span>
            <button
              onClick={handlePrevSearchMatch}
              disabled={searchMatches.length === 0}
              className="p-1 rounded hover:bg-gray-800 text-gray-300 disabled:opacity-30 transition"
              title="Previous match"
            >
              <ChevronUp className="w-4 h-4" />
            </button>
            <button
              onClick={handleNextSearchMatch}
              disabled={searchMatches.length === 0}
              className="p-1 rounded hover:bg-gray-800 text-gray-300 disabled:opacity-30 transition"
              title="Next match"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setIsSearching(false);
                setSearchQuery("");
              }}
              className="p-1 rounded hover:bg-gray-800 text-gray-400 hover:text-white ml-1 transition"
              title="Close search"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Transient Action Toast Feedback */}
      {toastMessage && (
        <div className="fixed top-16 left-1/2 -translate-x-1/2 z-50 bg-gray-900/95 border border-indigo-500/40 text-white px-4 py-2 rounded-full shadow-2xl text-xs flex items-center gap-2 backdrop-blur-md animate-in fade-in slide-in-from-top-4 duration-200">
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Analytics Drawers */}
      {showDashboard && (
        <div className="px-4 pt-4 border-b border-gray-800 bg-gray-900/40 backdrop-blur-md">
          <MoodDashboard currentUser={currentUser} />
          <GoalTracker currentUser={currentUser} />
        </div>
      )}

      {/* 2. Message History & Streaming Area (Telegram + Messenger Hybrid) */}
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
        onPinMessage={handlePinMessage}
        onSaveMessage={handleSaveMessage}
        pinnedMessageId={pinnedMessageId}
        setViewingImage={setViewingImage}
        resolveImageUrl={resolveImageUrl}
        messagesEndRef={messagesEndRef}
        searchQuery={searchQuery}
        activeMatchId={activeMatch?.id}
        onShowToast={showToast}
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
        editingMsg={
          editingMsgIdx !== null && messages[editingMsgIdx]
            ? { id: messages[editingMsgIdx].id, content: messages[editingMsgIdx].content, idx: editingMsgIdx }
            : null
        }
        onCancelEdit={() => {
          setEditingMsgIdx(null);
          setInput("");
        }}
        onSubmitEdit={(content) => {
          if (editingMsgIdx !== null) {
            submitEdit(editingMsgIdx, content);
          }
        }}
      />

      {/* Theme & Wallpaper Customizer Modal */}
      {showThemeModal && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-md flex items-center justify-center z-50 animate-in fade-in p-4">
          <div className="bg-gray-900 border border-gray-700/80 p-6 rounded-3xl max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Palette className="w-5 h-5 text-pink-400" />
                <h3 className="text-lg font-bold text-white">Chat Themes & Wallpaper</h3>
              </div>
              <button
                onClick={() => setShowThemeModal(false)}
                className="text-gray-400 hover:text-white p-1 rounded-full hover:bg-gray-800 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-gray-400 mb-4">
              Select a visual aesthetic inspired by Telegram and modern messenger apps:
            </p>

            {/* Presets Grid */}
            <div className="grid grid-cols-2 gap-3 mb-5">
              {THEME_PRESETS.filter(t => t.key !== "custom").map((t) => (
                <button
                  key={t.key}
                  onClick={() => {
                    setChatTheme(t.key);
                    localStorage.setItem("aura_chat_theme", t.key);
                    showToast(`Theme changed to ${t.name}`);
                  }}
                  className={`p-3 rounded-2xl border text-left flex items-center gap-3 transition-all ${
                    chatTheme === t.key
                      ? "border-indigo-500 bg-indigo-950/40 shadow-md"
                      : "border-gray-800 bg-gray-950 hover:border-gray-700"
                  }`}
                >
                  <div 
                    className="w-5 h-5 rounded-full border border-white/20 shrink-0" 
                    style={{ backgroundColor: t.accent }}
                  />
                  <span className="text-xs font-medium text-gray-200">{t.name}</span>
                </button>
              ))}
            </div>

            {/* Custom Wallpaper URL */}
            <div className="border-t border-gray-800 pt-4">
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                Custom Wallpaper URL (Unsplash or Image Link):
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={customWallpaper}
                  onChange={(e) => setCustomWallpaper(e.target.value)}
                  placeholder="https://images.unsplash.com/..."
                  className="flex-1 bg-gray-950 border border-gray-700 rounded-xl px-3 py-2 text-xs text-white placeholder-gray-500 outline-none focus:border-indigo-500"
                />
                <button
                  onClick={() => {
                    if (customWallpaper.trim()) {
                      setChatTheme("custom");
                      localStorage.setItem("aura_chat_theme", "custom");
                      localStorage.setItem("aura_custom_wallpaper", customWallpaper.trim());
                      showToast("Custom wallpaper applied! 🎨");
                      setShowThemeModal(false);
                    }
                  }}
                  className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-medium transition"
                >
                  Apply
                </button>
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => setShowThemeModal(false)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-xl text-xs transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

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
      {showMediaGallery && (() => {
        const seenUrls = new Set<string>();
        const combined: any[] = [];
        
        galleryItems.forEach(item => {
          const key = item.imageUrl || item.audioBase64 || item.id;
          if (key && !seenUrls.has(key)) {
            seenUrls.add(key);
            combined.push(item);
          }
        });

        messages.filter(m => m.imageUrl || m.isVoiceNote).reverse().forEach(m => {
          const key = m.imageUrl || m.audioBase64 || m.id;
          if (key && !seenUrls.has(key)) {
            seenUrls.add(key);
            combined.push({
              id: m.id || Math.random().toString(),
              type: m.imageUrl ? 'image' : 'audio',
              imageUrl: m.imageUrl,
              audioBase64: m.audioBase64,
              userAudioUrl: m.userAudioUrl,
              isVoiceNote: m.isVoiceNote,
              role: m.role,
              caption: m.content
            });
          }
        });

        const filtered = combined.filter(item => {
          if (galleryFilter === 'photos') return !!item.imageUrl;
          if (galleryFilter === 'voice') return !!item.isVoiceNote || !!item.audioBase64;
          return true;
        });

        return (
          <div className="absolute inset-0 bg-gray-950/95 z-40 flex flex-col p-6 animate-in fade-in slide-in-from-bottom-10">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-6">
              <div>
                <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-pink-400 to-indigo-400">
                  Media & Memory Vault
                </h2>
                <p className="text-xs text-gray-400 mt-1">
                  {filtered.length} preserved moment{filtered.length === 1 ? '' : 's'} across all conversations
                </p>
              </div>

              <div className="flex items-center gap-2">
                <div className="flex bg-gray-900 border border-gray-800 rounded-lg p-1 text-xs">
                  <button
                    onClick={() => setGalleryFilter('all')}
                    className={`px-3 py-1 rounded-md transition-all ${galleryFilter === 'all' ? 'bg-pink-600 text-white font-medium' : 'text-gray-400 hover:text-white'}`}
                  >
                    All
                  </button>
                  <button
                    onClick={() => setGalleryFilter('photos')}
                    className={`px-3 py-1 rounded-md transition-all ${galleryFilter === 'photos' ? 'bg-pink-600 text-white font-medium' : 'text-gray-400 hover:text-white'}`}
                  >
                    Photos
                  </button>
                  <button
                    onClick={() => setGalleryFilter('voice')}
                    className={`px-3 py-1 rounded-md transition-all ${galleryFilter === 'voice' ? 'bg-pink-600 text-white font-medium' : 'text-gray-400 hover:text-white'}`}
                  >
                    Voice Notes
                  </button>
                </div>
                <button
                  onClick={() => setShowMediaGallery(false)}
                  className="p-2 bg-gray-800 rounded-full text-white hover:bg-gray-700 transition-colors"
                >
                  ✕
                </button>
              </div>
            </div>

            {isLoadingGallery ? (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-400 gap-3">
                <div className="w-8 h-8 border-2 border-pink-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-sm">Fetching all historical media...</p>
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-gray-500 gap-2">
                <span className="text-4xl">📸</span>
                <p className="text-sm font-medium">No media found in vault</p>
                <p className="text-xs text-gray-600">Ask Aura for a selfie or send a voice note to start building your gallery!</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 overflow-y-auto pb-20">
                {filtered.map((media, i) => (
                  <div key={media.id || i} className="bg-gray-900/90 border border-gray-800/80 hover:border-pink-500/30 transition-all rounded-xl p-3 flex flex-col gap-2 shadow-lg group">
                    {media.imageUrl && (
                      <div className="relative overflow-hidden rounded-lg">
                        <img
                          src={resolveImageUrl(media.imageUrl)}
                          alt="Aura Deliverable"
                          className="w-full max-h-72 sm:max-h-80 object-cover rounded-lg shadow-md border border-gray-700/50 cursor-pointer transform group-hover:scale-102 transition-transform duration-300"
                          loading="lazy"
                          onClick={() => setViewingImage(media.imageUrl)}
                        />
                        <div
                          className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity cursor-pointer rounded-lg"
                          onClick={() => setViewingImage(media.imageUrl)}
                        >
                          <span className="text-xs bg-black/70 text-white px-2 py-1 rounded-md backdrop-blur-sm">🔍 Zoom</span>
                        </div>
                      </div>
                    )}
                    {media.isVoiceNote && (
                      <audio controls className="w-full h-8 mt-1" src={media.userAudioUrl || `data:audio/mp3;base64,${media.audioBase64}`} />
                    )}
                    <div className="flex items-center justify-between text-[11px] text-gray-400 px-1 mt-1">
                      <span>{media.role === 'ai' ? '💜 Aura' : '👤 You'}</span>
                      {media.timestamp && (
                        <span className="text-gray-500 text-[10px]">
                          {new Date(media.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric' })}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })()}

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