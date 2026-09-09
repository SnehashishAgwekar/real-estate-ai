import React, { useState, useEffect, useRef } from "react";
import {
  Building2, Send, Bot, User, Database, FileText, Globe, Sparkles,
  RotateCcw, Loader2, SlidersHorizontal, ChevronRight, Home, ShieldCheck,
  Cpu, CheckCircle2, Plus, MessageSquare, Trash2, Upload, X, CheckCircle, AlertTriangle,
  LogOut, LogIn, UserPlus, Mail, Lock, Phone, Briefcase, MapPin, BedDouble
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_STREAM_URL = "http://localhost:8000/api/v1/chat-stream";
const API_VERIFY_URL = "http://localhost:8000/api/v1/verify-property";
const API_SIGNUP_URL = "http://localhost:8000/api/v1/auth/signup";
const API_LOGIN_URL = "http://localhost:8000/api/v1/auth/login";
const API_BROKER_LISTINGS_URL = "http://localhost:8000/api/v1/broker/my-listings";
const API_BROKER_CREATE_URL = "http://localhost:8000/api/v1/broker/listings";
const API_BROKER_LEADS_URL = "http://localhost:8000/api/v1/broker/leads";
const API_INTEREST_URL = (id) => `http://localhost:8000/api/v1/properties/${id}/interest`;
// Origin that serves uploaded media at /static/uploads/... (see backend main.py mount)
const MEDIA_BASE = "http://localhost:8000";

const EMPTY_LISTING = {
  property_name: "", city: "", location: "", price_in_inr: "", area_sqft: "",
  property_type: "Apartment", bhk: "", area_unit: "sqft", builder_name: "",
  amenities: "", availability_status: "Ready to Move",
};

// FastAPI errors: `detail` is a string for our raised HTTPExceptions, or an
// array of {msg, loc} for request-validation (422) errors.
const errDetail = (data, fallback) => {
  const d = data?.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d) && d.length) return d[0]?.msg || fallback;
  return fallback;
};

// Decode a JWT payload without verifying the signature (used only as a role fallback).
const parseJwt = (t) => {
  try {
    const base = t.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(decodeURIComponent(escape(atob(base))));
  } catch {
    return {};
  }
};

const HERO_IMAGE = "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=2000&q=80";
const SIDEBAR_IMAGE = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80";

// Chat history is stored per user id so accounts sharing a browser never mix.
const sessionsStorageKey = (uid) => `estate_chat_sessions_${uid || "anon"}`;

const WELCOME_MESSAGE = {
  role: "assistant",
  content: "Welcome to **EstateAgent AI**! How can I assist you with your property search today?",
  intent: null, filters: null, steps: [], properties: [],
};

const newSessionObject = () => ({
  id: "session_" + Math.random().toString(36).substring(2, 9),
  title: "New Conversation",
  messages: [{ ...WELCOME_MESSAGE }],
});

const loadUserSessions = (uid) => {
  try {
    const saved = localStorage.getItem(sessionsStorageKey(uid));
    const parsed = saved ? JSON.parse(saved) : null;
    if (Array.isArray(parsed) && parsed.length > 0) return parsed;
  } catch { /* ignore corrupt/blocked storage */ }
  return [newSessionObject()];
};

export default function App() {
  // Views: "login" | "signup" | "chat" | "verify" | "broker-dashboard"
  const [activeView, setActiveView] = useState("login");

  // --- Auth state (JWT kept in memory only, never persisted) ---
  const [token, setToken] = useState(null);
  const [currentUser, setCurrentUser] = useState(null); // { name, email, role, phone_number }
  const [authForm, setAuthForm] = useState({ name: "", email: "", password: "", phone_number: "", role: "user" });
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // --- Broker dashboard state ---
  const [brokerListings, setBrokerListings] = useState(null);
  const [brokerLoading, setBrokerLoading] = useState(false);
  const [brokerError, setBrokerError] = useState("");
  const [showListingForm, setShowListingForm] = useState(false);
  const [listingForm, setListingForm] = useState(EMPTY_LISTING);
  const [listingImages, setListingImages] = useState([]);
  const [listingSubmitting, setListingSubmitting] = useState(false);
  const [listingError, setListingError] = useState("");
  const [brokerLeads, setBrokerLeads] = useState(null);

  // "Interested" state per property id: { loading, error, data }
  const [interestState, setInterestState] = useState({});

  // Full-screen image viewer (click any listing photo to enlarge)
  const [lightboxSrc, setLightboxSrc] = useState(null);

  useEffect(() => {
    if (!lightboxSrc) return;
    const onKey = (e) => { if (e.key === "Escape") setLightboxSrc(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightboxSrc]);

  const isAuthed = !!token && !!currentUser;
  const isBroker = isAuthed && currentUser.role === "broker";

  const [selectedBhk, setSelectedBhk] = useState(2);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  // Chat state stays empty until a user logs in; applyAuthSuccess loads the
  // signed-in user's own history, handleLogout wipes it.
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState("");
  const [messages, setMessages] = useState([{ ...WELCOME_MESSAGE }]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Persist the active user's chat history under their own storage key.
  useEffect(() => {
    if (!currentUser || !activeSessionId || sessions.length === 0) return;
    const updated = sessions.map((s) =>
      s.id === activeSessionId ? { ...s, messages } : s
    );
    setSessions(updated);
    try {
      localStorage.setItem(sessionsStorageKey(currentUser.id), JSON.stringify(updated));
    } catch { /* storage may be blocked */ }
  }, [messages]);

  const createNewChat = () => {
    const newSession = newSessionObject();
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newSession.id);
    setMessages(newSession.messages);
  };

  const switchSession = (id) => {
    const found = sessions.find((s) => s.id === id);
    if (found) {
      setActiveSessionId(found.id);
      setMessages(found.messages);
    }
  };

  const deleteSession = (e, id) => {
    e.stopPropagation();
    const filtered = sessions.filter((s) => s.id !== id);
    setSessions(filtered);
    try {
      localStorage.setItem(sessionsStorageKey(currentUser?.id), JSON.stringify(filtered));
    } catch { /* storage may be blocked */ }

    if (activeSessionId === id) {
      if (filtered.length > 0) {
        setActiveSessionId(filtered[0].id);
        setMessages(filtered[0].messages);
      } else {
        createNewChat();
      }
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (activeView === "chat") scrollToBottom();
  }, [messages, loading, activeView]);

  const handleSend = async (queryTextOverride) => {
    const textToSend = queryTextOverride || input;
    if (!textToSend.trim() || loading) return;

    const userText = textToSend.trim();
    if (!queryTextOverride) setInput("");

    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSessionId && s.title === "New Conversation") {
          return { ...s, title: userText.length > 25 ? userText.substring(0, 25) + "..." : userText };
        }
        return s;
      })
    );

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userText },
      { role: "assistant", content: "", intent: null, filters: null, steps: [], properties: [] }
    ]);
    setLoading(true);

    let currentSteps = [];
    let finalContent = "";
    let detectedIntent = null;
    let detectedFilters = null;
    let detectedProperties = [];

    try {
      const response = await fetch(API_STREAM_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // namespace the LangGraph thread by user so conversation memory can't bleed across accounts
        body: JSON.stringify({
          user_query: userText,
          thread_id: `${currentUser?.id || "anon"}:${activeSessionId}`,
        }),
      });

      if (!response.body) throw new Error("Streaming not supported by server");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop();

        for (const line of parts) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.replace("data: ", ""));
              if (data.node) {
                let nodeLabel = data.node;
                if (["router", "classify_intent_node", "classifier"].includes(data.node)) nodeLabel = "🧠 Classifying intent & extracting filters";
                else if (["sql_execution_node", "sql_execution"].includes(data.node)) nodeLabel = "🏠 Searching EstateAgent AI broker listings";
                else if (["rag_execution_node", "rag_execution"].includes(data.node)) nodeLabel = "📄 Scanning Qdrant vector documents";
                else if (["web_search_node", "web_search_execution"].includes(data.node)) nodeLabel = "🌐 Fetching live web insights";
                else if (["synthesizer_node", "synthesizer"].includes(data.node)) nodeLabel = "✨ Synthesizing final response";
                else if (["general_knowledge_node", "general_knowledge"].includes(data.node)) nodeLabel = "💬 Answering from general knowledge";

                currentSteps.push(nodeLabel);
                setMessages((prev) => {
                  const newPrev = [...prev];
                  const lastMsg = newPrev[newPrev.length - 1];
                  lastMsg.steps = [...currentSteps];
                  return newPrev;
                });
              }

              if (data.update) {
                if (data.update.intent) detectedIntent = data.update.intent;
                if (data.update.parsed_filters) detectedFilters = data.update.parsed_filters;
                if (Array.isArray(data.update.sql_results)) {
                  detectedProperties = data.update.sql_results;
                  setMessages((prev) => {
                    const newPrev = [...prev];
                    newPrev[newPrev.length - 1].properties = detectedProperties;
                    return newPrev;
                  });
                }
                if (data.update.final_response) finalContent = data.update.final_response;
              }

              if (data.error) finalContent = `⚠️ **Error:** ${data.error}`;
            } catch (e) {
               console.error("Incomplete JSON chunk skipped temporarily:", e);
            }
          }
        }
      }

      setMessages((prev) => {
        const newPrev = [...prev];
        const lastMsg = newPrev[newPrev.length - 1];
        lastMsg.content = finalContent || "No response generated.";
        lastMsg.intent = detectedIntent;
        lastMsg.filters = detectedFilters;
        lastMsg.properties = detectedProperties;
        return newPrev;
      });
    } catch (err) {
      setMessages((prev) => {
        const newPrev = [...prev];
        const lastMsg = newPrev[newPrev.length - 1];
        lastMsg.content = `⚠️ **Error:** Unable to connect to backend agent stream. (${err.message})`;
        lastMsg.intent = "error";
        return newPrev;
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files) {
      const filesArray = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith("image/"));
      setSelectedFiles(prev => [...prev, ...filesArray].slice(0, 8));
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files) {
      const filesArray = Array.from(e.target.files).filter(f => f.type.startsWith("image/"));
      setSelectedFiles(prev => [...prev, ...filesArray].slice(0, 8));
    }
  };

  const removeFile = (index) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleVerifySubmit = async () => {
    if (selectedFiles.length === 0 || verifyLoading) return;
    setVerifyLoading(true);
    setVerifyResult(null);

    const formData = new FormData();
    formData.append("claimed_bhk", selectedBhk);
    selectedFiles.forEach((file) => formData.append("images", file));

    try {
      const res = await fetch(API_VERIFY_URL, { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Verification failed");
      setVerifyResult(data);
    } catch (err) {
      alert(`Verification Error: ${err.message}`);
    } finally {
      setVerifyLoading(false);
    }
  };

  // --- Auth handlers ---------------------------------------------------------
  const applyAuthSuccess = (data, fallbackRole, fallbackName, fallbackEmail, fallbackPhone) => {
    const jwt = data.access_token || data.token || data.jwt;
    if (!jwt) throw new Error("No token returned by server.");
    const claims = parseJwt(jwt);
    const role = data.role || data.user?.role || claims.role || fallbackRole || "user";
    const uid = data.id ?? data.user?.id ?? claims.sub ?? null;

    setToken(jwt);
    setCurrentUser({
      id: uid,
      name: data.name || data.user?.name || fallbackName || "",
      email: data.email || data.user?.email || fallbackEmail || "",
      role,
      phone_number: data.phone_number || data.user?.phone_number || fallbackPhone || "",
    });
    setAuthForm({ name: "", email: "", password: "", phone_number: "", role: "user" });

    // Reset every piece of per-user state so nothing leaks from a prior session.
    const userSessions = loadUserSessions(uid);
    setSessions(userSessions);
    setActiveSessionId(userSessions[0].id);
    setMessages(userSessions[0].messages);
    setInput("");
    setBrokerListings(null);
    setBrokerLeads(null);
    setBrokerError("");
    setShowListingForm(false);
    setListingForm(EMPTY_LISTING);
    setListingImages([]);
    setListingError("");
    setInterestState({});
    setVerifyResult(null);
    setSelectedFiles([]);

    setActiveView(role === "broker" ? "broker-dashboard" : "chat");
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    if (authLoading) return;
    setAuthError("");
    const { name, email, password, phone_number, role } = authForm;
    if (!name.trim() || !email.trim() || !password.trim()) {
      setAuthError("Name, email and password are required.");
      return;
    }
    setAuthLoading(true);
    try {
      const res = await fetch(API_SIGNUP_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), email: email.trim(), password, phone_number: phone_number.trim(), role }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(errDetail(data, "Signup failed"));
      applyAuthSuccess(data, role, name.trim(), email.trim(), phone_number.trim());
    } catch (err) {
      setAuthError(err.message || "Unable to reach the authentication service.");
    } finally {
      setAuthLoading(false);
    }
  };
  
  async function requestNotificationPermission(userId) {
    if ('serviceWorker' in navigator && 'PushManager' in window) {
        try {
            const registration = await navigator.serviceWorker.register('/sw.js');
            const permission = await window.Notification.requestPermission();
            
            if (permission === 'granted') {
                const subscription = await registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: 'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDkJrxZJezsTu...' 
                });
                
                await fetch('http://localhost:8000/api/v1/subscribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: userId, ...subscription })
                });
            }
        } catch (err) {
            console.error("Push subscription failed:", err);
        }
    }
}

  const handleLogin = async (e) => {
    e.preventDefault();
    if (authLoading) return;
    setAuthError("");
    const { email, password } = authForm;
    if (!email.trim() || !password.trim()) {
      setAuthError("Email and password are required.");
      return;
    }
    setAuthLoading(true);
    try {
      // Backend /auth/login uses FastAPI's OAuth2PasswordRequestForm:
      // form-encoded body with `username` (our email) and `password`.
      const body = new URLSearchParams();
      body.append("username", email.trim());
      body.append("password", password);
      const res = await fetch(API_LOGIN_URL, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(errDetail(data, "Invalid credentials"));
      applyAuthSuccess(data, null, null, email.trim(), null);
    } catch (err) {
      setAuthError(err.message || "Unable to reach the authentication service.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    setToken(null);
    setCurrentUser(null);
    setAuthForm({ name: "", email: "", password: "", phone_number: "", role: "user" });
    setAuthError("");
    // Wipe chat state from memory (the user's history stays under their own
    // localStorage key and reloads when they sign back in).
    setSessions([]);
    setActiveSessionId("");
    setMessages([{ ...WELCOME_MESSAGE }]);
    setInput("");
    setBrokerListings(null);
    setBrokerError("");
    setBrokerLeads(null);
    setShowListingForm(false);
    setListingForm(EMPTY_LISTING);
    setListingImages([]);
    setListingError("");
    setInterestState({});
    setVerifyResult(null);
    setSelectedFiles([]);
    setActiveView("login");
  };

  const switchAuthMode = (mode) => {
    setActiveView(mode);
    setAuthError("");
  };

  // --- Broker dashboard data ----------------------------------------------
  const fetchBrokerListings = async () => {
    if (!token) return;
    setBrokerLoading(true);
    setBrokerError("");
    try {
      const res = await fetch(API_BROKER_LISTINGS_URL, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to load listings");
      setBrokerListings(Array.isArray(data) ? data : []);
    } catch (err) {
      setBrokerError(err.message || "Unable to load your listings.");
      setBrokerListings([]);
    } finally {
      setBrokerLoading(false);
    }
  };

  const fetchBrokerLeads = async () => {
    if (!token) return;
    try {
      const res = await fetch(API_BROKER_LEADS_URL, { headers: { Authorization: `Bearer ${token}` } });
      const data = await res.json();
      setBrokerLeads(res.ok && Array.isArray(data) ? data : []);
    } catch {
      setBrokerLeads([]);
    }
  };

  useEffect(() => {
    if (isBroker && activeView === "broker-dashboard" && brokerListings === null && !brokerLoading) {
      fetchBrokerListings();
      fetchBrokerLeads();
    }
  }, [isBroker, activeView]);

  // A user taps "Interested" on one of our broker listings shown in chat.
  const handleExpressInterest = async (propertyId) => {
    if (interestState[propertyId]?.loading || interestState[propertyId]?.data) return;
    setInterestState((s) => ({ ...s, [propertyId]: { loading: true } }));
    try {
      const res = await fetch(API_INTEREST_URL(propertyId), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({}),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(errDetail(data, "Could not register your interest"));
      setInterestState((s) => ({ ...s, [propertyId]: { loading: false, data } }));
    } catch (err) {
      setInterestState((s) => ({ ...s, [propertyId]: { loading: false, error: err.message } }));
    }
  };

  const setListingField = (k) => (e) => setListingForm((f) => ({ ...f, [k]: e.target.value }));

  const handleListingImageSelect = (e) => {
    if (!e.target.files) return;
    const picked = Array.from(e.target.files).filter((file) => file.type.startsWith("image/"));
    setListingImages((prev) => [...prev, ...picked].slice(0, 10));
    e.target.value = ""; // allow re-selecting the same file
  };

  const removeListingImage = (index) => {
    setListingImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleCreateListing = async (e) => {
    e.preventDefault();
    if (listingSubmitting) return;
    setListingError("");
    const f = listingForm;
    if (!f.property_name.trim() || !f.city.trim() || !f.location.trim() || !String(f.price_in_inr).trim() || !String(f.area_sqft).trim()) {
      setListingError("Property name, city, location, price and area are required.");
      return;
    }
    if (listingImages.length === 0) {
      setListingError("Please attach at least one property image.");
      return;
    }
    setListingSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("property_name", f.property_name.trim());
      fd.append("city", f.city.trim());
      fd.append("location", f.location.trim());
      fd.append("price_in_inr", String(Number(f.price_in_inr)));
      fd.append("area_sqft", String(Number(f.area_sqft)));
      fd.append("property_type", f.property_type);
      fd.append("area_unit", f.area_unit.trim() || "sqft");
      fd.append("availability_status", f.availability_status);
      if (String(f.bhk).trim() !== "") fd.append("bhk", String(Number(f.bhk)));
      if (f.builder_name.trim()) fd.append("builder_name", f.builder_name.trim());
      if (f.amenities.trim()) fd.append("amenities", f.amenities.trim());
      listingImages.forEach((file) => fd.append("images", file));

      // No Content-Type header — the browser sets the multipart boundary itself.
      const res = await fetch(API_BROKER_CREATE_URL, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: fd,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(errDetail(data, "Could not create listing"));
      setBrokerListings((prev) => [data, ...(prev || [])]);
      setListingForm(EMPTY_LISTING);
      setListingImages([]);
      setShowListingForm(false);
    } catch (err) {
      setListingError(err.message || "Could not create listing.");
    } finally {
      setListingSubmitting(false);
    }
  };

  const renderIntentBadge = (intent, filters) => {
    switch (intent) {
      case "sql_search":
        return (
          <div className="flex flex-wrap items-center gap-2 mb-2.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[10px] font-semibold uppercase tracking-wider bg-[#3F5142]/40 text-[#9FBF9A] border border-[#6E8B6E]/40 font-mono">
              <Database className="w-3 h-3" /> Property Registry Query
            </span>
            {filters && Object.keys(filters).length > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-sm text-[10px] font-mono bg-[#0C1420]/80 text-[#C9BFA6] border border-[#3A4457]">
                <SlidersHorizontal className="w-3 h-3 text-[#C6A15B]" />
                {Object.entries(filters).map(([k, v]) => `${k}: ${v}`).join("  ·  ")}
              </span>
            )}
          </div>
        );
      case "rag_search":
        return (
          <div className="mb-2.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[10px] font-semibold uppercase tracking-wider bg-[#463C55]/40 text-[#C6B4DA] border border-[#8A6BA1]/40 font-mono">
              <FileText className="w-3 h-3" /> Brochure Archive
            </span>
          </div>
        );
      case "web_search":
        return (
          <div className="mb-2.5">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-sm text-[10px] font-semibold uppercase tracking-wider bg-[#2A4152]/40 text-[#9CC4E0] border border-[#6FA3C7]/40 font-mono">
              <Globe className="w-3 h-3" /> Live Market Insight
            </span>
          </div>
        );
      default:
        return null;
    }
  };

  // --- Auth screen (login / signup) --------------------------------------
  const renderAuthScreen = () => {
    const isSignup = activeView === "signup";
    const inputCls =
      "w-full bg-[#0A121D]/90 border border-[#2C3A50] focus:border-[#C6A15B] rounded-md py-2.5 pl-9 pr-3 text-sm text-[#EDE7D9] placeholder-[#7D8AA1] focus:outline-none focus:ring-2 focus:ring-[#C6A15B]/30 transition disabled:opacity-50";
    const setField = (k) => (e) => setAuthForm((f) => ({ ...f, [k]: e.target.value }));

    return (
      <div className="flex-1 flex items-center justify-center z-10 p-6 font-body">
        <div className="w-full max-w-md bg-[#0E1725]/90 backdrop-blur-xl border border-[#C6A15B]/25 rounded-md shadow-2xl p-8 space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-[#0E1725]/80 border border-[#C6A15B]/50 rounded-sm">
              <Building2 className="w-5 h-5 text-[#C6A15B]" />
            </div>
            <div>
              <h1 className="font-display text-xl text-[#F3EEE1] leading-none tracking-wide">EstateAgent AI</h1>
              <p className="text-[9px] font-mono uppercase tracking-[0.15em] text-[#C6A15B] mt-1">Private Client Advisory</p>
            </div>
          </div>

          <div className="flex gap-1 p-1 bg-[#070C14]/80 border border-[#2C3A50] rounded-sm font-mono">
            {[["login", "Login"], ["signup", "Sign Up"]].map(([mode, label]) => (
              <button
                key={mode}
                type="button"
                onClick={() => switchAuthMode(mode)}
                className={`flex-1 py-2 rounded-sm text-[11px] font-semibold uppercase tracking-wider transition ${
                  activeView === mode ? "bg-[#C6A15B] text-[#0C1420]" : "text-[#D9D2BF] hover:bg-[#141F30]"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={isSignup ? handleSignup : handleLogin} className="space-y-3.5">
            {isSignup && (
              <div className="relative">
                <User className="w-4 h-4 text-[#7D8AA1] absolute left-3 top-1/2 -translate-y-1/2" />
                <input className={inputCls} type="text" placeholder="Full name" value={authForm.name}
                  onChange={setField("name")} autoComplete="name" disabled={authLoading} />
              </div>
            )}

            <div className="relative">
              <Mail className="w-4 h-4 text-[#7D8AA1] absolute left-3 top-1/2 -translate-y-1/2" />
              <input className={inputCls} type="email" placeholder="Email address" value={authForm.email}
                onChange={setField("email")} autoComplete="email" disabled={authLoading} />
            </div>

            <div className="relative">
              <Lock className="w-4 h-4 text-[#7D8AA1] absolute left-3 top-1/2 -translate-y-1/2" />
              <input className={inputCls} type="password" placeholder="Password" value={authForm.password}
                onChange={setField("password")} autoComplete={isSignup ? "new-password" : "current-password"} disabled={authLoading} />
            </div>

            {isSignup && (
              <div className="relative">
                <Phone className="w-4 h-4 text-[#7D8AA1] absolute left-3 top-1/2 -translate-y-1/2" />
                <input className={inputCls} type="tel" placeholder="Phone number" value={authForm.phone_number}
                  onChange={setField("phone_number")} autoComplete="tel" disabled={authLoading} />
              </div>
            )}

            {isSignup && (
              <div className="space-y-1.5 pt-0.5">
                <label className="text-[10px] font-mono uppercase tracking-wider text-[#C6A15B] font-semibold">Account Type</label>
                <div className="grid grid-cols-2 gap-2">
                  {[["user", "Sign up as User", User], ["broker", "Sign up as Broker", Briefcase]].map(([val, label, Icon]) => (
                    <button
                      key={val}
                      type="button"
                      onClick={() => setAuthForm((f) => ({ ...f, role: val }))}
                      className={`flex items-center justify-center gap-1.5 px-2 py-2 rounded-sm text-[11px] font-mono font-semibold border transition ${
                        authForm.role === val
                          ? "bg-[#C6A15B] text-[#0C1420] border-[#C6A15B]"
                          : "bg-[#141F30] text-[#D9D2BF] border-[#2C3A50] hover:border-[#C6A15B]/40"
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" /> {label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {authError && (
              <div className="flex items-start gap-2 p-2.5 bg-[#553C3C]/25 border border-[#DA6B6B]/40 rounded-sm text-xs text-[#DA6B6B] font-body">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span>{authError}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={authLoading}
              className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-sm bg-[#C6A15B] hover:bg-[#D9B876] disabled:opacity-40 text-[#0C1420] font-semibold text-xs transition shadow-lg font-mono uppercase tracking-wider"
            >
              {authLoading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> Please wait...</>
              ) : isSignup ? (
                <><UserPlus className="w-4 h-4" /> Create Account</>
              ) : (
                <><LogIn className="w-4 h-4" /> Sign In</>
              )}
            </button>
          </form>

          <p className="text-center text-[11px] text-[#7D8AA1] font-body">
            {isSignup ? "Already registered? " : "New to EstateAgent AI? "}
            <button
              type="button"
              onClick={() => switchAuthMode(isSignup ? "login" : "signup")}
              className="text-[#C6A15B] hover:underline font-medium"
            >
              {isSignup ? "Log in" : "Create an account"}
            </button>
          </p>
        </div>
      </div>
    );
  };

  // --- Broker dashboard --------------------------------------------------
  const renderBrokerDashboard = () => (
    <main className="flex-1 flex flex-col h-full relative z-10">
      <header className="h-16 border-b border-[#C6A15B]/15 flex items-center justify-between px-6 bg-[#0E1725]/60 backdrop-blur-xl font-body">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-[#0E1725]/80 border border-[#C6A15B]/50 rounded-sm">
            <Briefcase className="w-4 h-4 text-[#C6A15B]" />
          </div>
          <h2 className="text-sm font-semibold tracking-wide text-[#D9D2BF] font-display">Broker Dashboard</h2>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-[10px] font-mono bg-[#141F30] text-[#C6A15B] border border-[#C6A15B]/25 px-3 py-1 rounded-sm uppercase tracking-wider hidden sm:block">
            {currentUser?.email}
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#141F30] hover:bg-[#1A2536] text-[#D9D2BF] border border-[#2C3A50] rounded-sm text-xs font-mono transition"
          >
            <LogOut className="w-3.5 h-3.5" /> Logout
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-8 font-body space-y-6 max-w-5xl mx-auto w-full">
        <div className="flex items-end justify-between gap-4">
          <div>
            <h3 className="text-lg font-display text-[#F3EEE1]">Welcome back, {currentUser?.name || "Broker"}</h3>
            <p className="text-xs text-[#8892A3] mt-1">Property listings linked to your broker account.</p>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => { setListingError(""); setShowListingForm((v) => !v); }}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-sm text-xs font-mono transition border ${
                showListingForm
                  ? "bg-[#141F30] text-[#D9D2BF] border-[#2C3A50] hover:bg-[#1A2536]"
                  : "bg-[#C6A15B] text-[#0C1420] border-[#C6A15B] hover:bg-[#D9B876] font-semibold uppercase tracking-wider"
              }`}
            >
              {showListingForm ? <><X className="w-3.5 h-3.5" /> Cancel</> : <><Plus className="w-3.5 h-3.5" /> Add Listing</>}
            </button>
            <button
              onClick={fetchBrokerListings}
              disabled={brokerLoading}
              className="flex items-center gap-2 px-3 py-1.5 bg-[#141F30] hover:bg-[#1A2536] text-[#D9D2BF] border border-[#2C3A50] rounded-sm text-xs font-mono transition disabled:opacity-50"
            >
              <RotateCcw className={`w-3 h-3 text-[#C6A15B] ${brokerLoading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>
        </div>

        {showListingForm && (
          <form
            onSubmit={handleCreateListing}
            className="bg-[#0E1725]/80 border border-[#C6A15B]/30 rounded-md p-5 space-y-4 shadow-2xl"
          >
            <h4 className="text-xs font-mono uppercase tracking-wider text-[#C6A15B] font-semibold">New Property Listing</h4>

            {(() => {
              const fieldCls =
                "w-full bg-[#0A121D]/90 border border-[#2C3A50] focus:border-[#C6A15B] rounded-md py-2 px-3 text-sm text-[#EDE7D9] placeholder-[#7D8AA1] focus:outline-none focus:ring-2 focus:ring-[#C6A15B]/30 transition disabled:opacity-50";
              const labelCls = "text-[10px] font-mono uppercase tracking-wider text-[#7D8AA1]";
              return (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <label className="space-y-1 sm:col-span-2">
                    <span className={labelCls}>Property Name *</span>
                    <input className={fieldCls} value={listingForm.property_name} onChange={setListingField("property_name")} placeholder="Skyline Residences" disabled={listingSubmitting} />
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>City *</span>
                    <input className={fieldCls} value={listingForm.city} onChange={setListingField("city")} placeholder="Indore" disabled={listingSubmitting} />
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>Location / Area *</span>
                    <input className={fieldCls} value={listingForm.location} onChange={setListingField("location")} placeholder="Vijay Nagar" disabled={listingSubmitting} />
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>Price (INR) *</span>
                    <input className={fieldCls} type="number" min="0" value={listingForm.price_in_inr} onChange={setListingField("price_in_inr")} placeholder="9500000" disabled={listingSubmitting} />
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>BHK</span>
                    <input className={fieldCls} type="number" min="0" value={listingForm.bhk} onChange={setListingField("bhk")} placeholder="3 (leave blank for plots)" disabled={listingSubmitting} />
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>Area *</span>
                    <input className={fieldCls} type="number" min="0" value={listingForm.area_sqft} onChange={setListingField("area_sqft")} placeholder="1450" disabled={listingSubmitting} />
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>Area Unit</span>
                    <select className={fieldCls} value={listingForm.area_unit} onChange={setListingField("area_unit")} disabled={listingSubmitting}>
                      {["sqft", "sq_yard", "acre", "hectare"].map((u) => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>Property Type</span>
                    <select className={fieldCls} value={listingForm.property_type} onChange={setListingField("property_type")} disabled={listingSubmitting}>
                      {["Apartment", "Villa", "Plot", "Commercial", "Independent House"].map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>Availability</span>
                    <select className={fieldCls} value={listingForm.availability_status} onChange={setListingField("availability_status")} disabled={listingSubmitting}>
                      {["Ready to Move", "Under Construction", "New Launch"].map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </label>
                  <label className="space-y-1">
                    <span className={labelCls}>Builder Name</span>
                    <input className={fieldCls} value={listingForm.builder_name} onChange={setListingField("builder_name")} placeholder="ABC Group" disabled={listingSubmitting} />
                  </label>
                  <label className="space-y-1 sm:col-span-2">
                    <span className={labelCls}>Amenities</span>
                    <input className={fieldCls} value={listingForm.amenities} onChange={setListingField("amenities")} placeholder="Pool, Gym, Clubhouse" disabled={listingSubmitting} />
                  </label>
                </div>
              );
            })()}

            <div className="space-y-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-[#7D8AA1]">
                Property Images * ({listingImages.length}/10)
              </span>
              <label className="flex flex-col items-center justify-center gap-1 border-2 border-dashed border-[#2C3A50] hover:border-[#C6A15B]/50 rounded-md p-5 text-center bg-[#070C14]/60 transition cursor-pointer">
                <input type="file" multiple accept="image/*" className="hidden" onChange={handleListingImageSelect} disabled={listingSubmitting} />
                <Upload className="w-6 h-6 text-[#C6A15B]" />
                <span className="text-xs text-[#D9D2BF] font-medium">Click to add photos (JPG, PNG, WebP, GIF)</span>
              </label>
              {listingImages.length > 0 && (
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                  {listingImages.map((file, idx) => (
                    <div key={idx} className="relative group rounded-md overflow-hidden border border-[#2C3A50] bg-[#070C14] h-20">
                      <img src={URL.createObjectURL(file)} alt={file.name} className="w-full h-full object-cover" />
                      <button
                        type="button"
                        onClick={() => removeListingImage(idx)}
                        disabled={listingSubmitting}
                        className="absolute top-1 right-1 p-1 bg-red-600/90 hover:bg-red-700 text-white rounded-full transition opacity-0 group-hover:opacity-100"
                        title="Remove image"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {listingError && (
              <div className="flex items-start gap-2 p-2.5 bg-[#553C3C]/25 border border-[#DA6B6B]/40 rounded-sm text-xs text-[#DA6B6B] font-body">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                <span>{listingError}</span>
              </div>
            )}

            <div className="flex items-center gap-2">
              <button
                type="submit"
                disabled={listingSubmitting}
                className="flex items-center justify-center gap-2 px-4 py-2 rounded-sm bg-[#C6A15B] hover:bg-[#D9B876] disabled:opacity-40 text-[#0C1420] font-semibold text-xs transition font-mono uppercase tracking-wider"
              >
                {listingSubmitting ? <><Loader2 className="w-4 h-4 animate-spin" /> Saving...</> : <><Plus className="w-4 h-4" /> Create Listing</>}
              </button>
              <button
                type="button"
                onClick={() => { setShowListingForm(false); setListingError(""); }}
                disabled={listingSubmitting}
                className="px-4 py-2 rounded-sm bg-[#141F30] hover:bg-[#1A2536] text-[#D9D2BF] border border-[#2C3A50] text-xs font-mono transition disabled:opacity-40"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {brokerLoading && (
          <div className="flex items-center gap-2 text-xs text-[#7D8AA1] font-mono">
            <Loader2 className="w-4 h-4 animate-spin text-[#C6A15B]" /> Loading your listings...
          </div>
        )}

        {brokerError && (
          <div className="flex items-start gap-2 p-3 bg-[#553C3C]/25 border border-[#DA6B6B]/40 text-[#DA6B6B] text-xs rounded-sm font-mono">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" /> {brokerError}
          </div>
        )}

        {!brokerLoading && brokerListings && brokerListings.length === 0 && (
          <div className="p-8 bg-[#0E1725]/80 border border-[#2C3A50] rounded-md text-center text-xs text-[#8892A3] font-body">
            No property listings are linked to your account yet.
          </div>
        )}

        {brokerListings && brokerListings.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {brokerListings.map((p) => (
              <div key={p.id} className="bg-[#0E1725]/80 border border-[#2C3A50] rounded-md p-4 space-y-2 shadow-xl">
                {Array.isArray(p.image_urls) && p.image_urls.length > 0 && (
                  <div className="flex gap-1.5 overflow-x-auto no-scrollbar -mx-1 px-1 pb-1">
                    {p.image_urls.map((url, i) => (
                      <img
                        key={i}
                        src={`${MEDIA_BASE}${url}`}
                        alt={`${p.property_name} photo ${i + 1}`}
                        loading="lazy"
                        onClick={() => setLightboxSrc(`${MEDIA_BASE}${url}`)}
                        className="h-24 w-32 flex-shrink-0 object-cover rounded-sm border border-[#2C3A50] bg-[#070C14] cursor-zoom-in hover:brightness-110 transition"
                      />
                    ))}
                  </div>
                )}
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-sm font-display text-[#F3EEE1]">{p.property_name}</h4>
                  {p.availability_status && (
                    <span className="text-[9px] font-mono uppercase tracking-wider bg-[#3F5142]/40 text-[#9FBF9A] border border-[#6E8B6E]/40 px-2 py-0.5 rounded-sm flex-shrink-0">
                      {p.availability_status}
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-[#8892A3] font-mono flex items-center gap-1.5">
                  <MapPin className="w-3 h-3 text-[#C6A15B]" /> {p.location}{p.city ? `, ${p.city}` : ""}
                </p>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono text-[#C9BFA6] pt-2 border-t border-[#2C3A50]/60">
                  <span className="text-[#F3EEE1] font-semibold">₹ {Number(p.price_in_inr || 0).toLocaleString("en-IN")}</span>
                  {p.bhk != null && (
                    <span className="flex items-center gap-1"><BedDouble className="w-3 h-3 text-[#7D9471]" /> {p.bhk} BHK</span>
                  )}
                  {p.area_sqft != null && <span>{p.area_sqft} {p.area_unit || "sqft"}</span>}
                  {p.property_type && <span className="text-[#7D8AA1]">{p.property_type}</span>}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Enquiries: users who tapped "Interested" on this broker's listings */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-display text-[#F3EEE1] flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-[#C6A15B]" /> Enquiries
            </h3>
            {brokerLeads && brokerLeads.length > 0 && (
              <span className="text-[10px] font-mono bg-[#C6A15B] text-[#0C1420] px-2 py-0.5 rounded-sm font-semibold">
                {brokerLeads.length}
              </span>
            )}
            <button
              onClick={fetchBrokerLeads}
              className="ml-auto flex items-center gap-1.5 px-2.5 py-1 bg-[#141F30] hover:bg-[#1A2536] text-[#D9D2BF] border border-[#2C3A50] rounded-sm text-[10px] font-mono transition"
            >
              <RotateCcw className="w-3 h-3 text-[#C6A15B]" /> Refresh
            </button>
          </div>

          {brokerLeads === null ? (
            <p className="text-xs text-[#7D8AA1] font-mono">Loading enquiries...</p>
          ) : brokerLeads.length === 0 ? (
            <div className="p-6 bg-[#0E1725]/80 border border-[#2C3A50] rounded-md text-center text-xs text-[#8892A3] font-body">
              No one has expressed interest in your listings yet.
            </div>
          ) : (
            <div className="space-y-2">
              {brokerLeads.map((lead) => (
                <div key={lead.interest_id} className="bg-[#0E1725]/80 border border-[#2C3A50] rounded-md p-3.5 space-y-1.5 shadow-lg">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm text-[#F3EEE1] font-medium">
                      {lead.user?.name || "A user"} <span className="text-[#7D8AA1] font-normal">is interested in</span> {lead.property_name}
                    </p>
                    <span className="text-[9px] font-mono text-[#7D8AA1] flex-shrink-0">
                      {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : ""}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-mono text-[#C9BFA6]">
                    {lead.user?.phone && <span>📞 {lead.user.phone}</span>}
                    {lead.user?.email && <span>✉️ {lead.user.email}</span>}
                    <span className="text-[#7D8AA1]">{lead.location}{lead.city ? `, ${lead.city}` : ""}</span>
                  </div>
                  {lead.message && <p className="text-[11px] text-[#C9BFA6] italic border-l-2 border-[#C6A15B]/40 pl-2">{`“${lead.message}”`}</p>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </main>
  );

  return (
    <div className="flex h-screen w-full text-[#EDE7D9] antialiased overflow-hidden font-sans relative">
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');
        .font-display { font-family: 'Fraunces', serif; font-optical-sizing: auto; }
        .font-body { font-family: 'Inter', sans-serif; }
        .font-mono { font-family: 'IBM Plex Mono', monospace; }
        .blueprint-grid {
          background-image:
            linear-gradient(rgba(198,161,91,0.06) 1px, transparent 1px),
            linear-gradient(90deg, rgba(198,161,91,0.06) 1px, transparent 1px);
          background-size: 28px 28px;
        }
        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
      `}</style>

      {/* BACKDROP */}
      <div className="absolute inset-0 z-0">
        <img src={HERO_IMAGE} alt="" className="w-full h-full object-cover brightness-[0.28] scale-105" />
        <div className="absolute inset-0 bg-[#0C1420]/88" />
        <div className="absolute inset-0 blueprint-grid" />
      </div>

      {/* AUTH GATE: nothing below is reachable until logged in */}
      {!isAuthed && renderAuthScreen()}

      {isBroker && renderBrokerDashboard()}

      {isAuthed && !isBroker && (
      <>
      {/* SIDEBAR WITH CHAT HISTORY & NEW CHAT */}
      <aside className="w-80 bg-[#0E1725]/90 backdrop-blur-xl border-r border-[#C6A15B]/15 flex flex-col justify-between p-5 hidden md:flex z-10 shadow-2xl font-body">
        <div className="space-y-5 flex-1 flex flex-col min-h-0">
          <div className="relative overflow-hidden rounded-md border border-[#C6A15B]/25 flex-shrink-0">
            <img src={SIDEBAR_IMAGE} alt="" className="w-full h-20 object-cover brightness-[0.5]" />
            <div className="absolute inset-0 bg-gradient-to-t from-[#0E1725] via-[#0E1725]/30 to-transparent" />
            <div className="absolute bottom-0 left-0 right-0 flex items-center gap-2.5 p-2.5">
              <div className="p-1.5 bg-[#0E1725]/80 border border-[#C6A15B]/50 rounded-sm">
                <Building2 className="w-4 h-4 text-[#C6A15B]" />
              </div>
              <div>
                <h1 className="font-display text-base leading-none tracking-wide text-[#F3EEE1]">EstateAgent AI</h1>
                <p className="text-[9px] font-mono uppercase tracking-[0.15em] text-[#C6A15B] mt-1">Private Client Advisory</p>
              </div>
            </div>
          </div>

          <button
            onClick={() => { setActiveView("chat"); createNewChat(); }}
            className="flex items-center justify-center gap-2 w-full py-2.5 px-4 rounded-sm bg-[#C6A15B] hover:bg-[#D9B876] text-[#0C1420] font-semibold text-xs transition shadow-lg font-mono uppercase tracking-wider flex-shrink-0"
          >
            <Plus className="w-4 h-4" /> New Chat
          </button>

          {/* Chat History List */}
          <div className="flex-1 overflow-y-auto space-y-1.5 no-scrollbar pr-1">
            <p className="text-[10px] font-mono font-semibold uppercase tracking-[0.15em] text-[#7D8AA1] px-1 pt-1 pb-1">Chat History</p>
            {sessions.map((sess) => (
              <div
                key={sess.id}
                onClick={() => { setActiveView("chat"); switchSession(sess.id); }}
                className={`w-full text-left p-2.5 rounded-sm border transition text-xs flex items-center justify-between group cursor-pointer ${
                  activeView === "chat" && activeSessionId === sess.id
                    ? "bg-[#1A2536] border-[#C6A15B]/50 text-[#F3EEE1]"
                    : "bg-[#141F30]/50 hover:bg-[#1A2536]/80 border-[#2C3A50] text-[#D9D2BF]"
                }`}
              >
                <div className="flex items-center gap-2 overflow-hidden">
                  <MessageSquare className="w-3.5 h-3.5 text-[#C6A15B] flex-shrink-0" />
                  <span className="truncate">{sess.title}</span>
                </div>
                {sessions.length > 1 && (
                  <button onClick={(e) => deleteSession(e, sess.id)} className="opacity-0 group-hover:opacity-100 hover:text-red-400 text-[#7D8AA1] transition p-1" title="Delete Chat">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>

          <div className="p-3 bg-[#0A121D]/80 rounded-sm border border-[#2C3A50] text-xs space-y-1.5 flex-shrink-0">
            <div className="flex items-center gap-1.5 text-[#7D9471] font-semibold font-mono text-[11px] uppercase tracking-wider">
              <ShieldCheck className="w-3.5 h-3.5" /> Multi-Agent Engine
            </div>
            <p className="text-[10px] text-[#8892A3] leading-relaxed">
              LangGraph + Gemini 3.6-Flash orchestrating Postgres &amp; Places365 Vision Verification.
            </p>
          </div>
        </div>

        <div className="pt-3 border-t border-[#C6A15B]/15 flex-shrink-0 space-y-2">
          <div className="flex items-center gap-2 px-1 text-[10px] font-mono text-[#7D8AA1] truncate">
            <User className="w-3 h-3 text-[#C6A15B] flex-shrink-0" />
            <span className="truncate">Signed in as {currentUser?.email || currentUser?.name}</span>
          </div>
          <button
            onClick={() => { setActiveView("chat"); createNewChat(); }}
            className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-sm bg-[#141F30]/90 hover:bg-[#1A2536] text-[#D9D2BF] font-medium text-xs transition border border-[#2C3A50] hover:border-[#C6A15B]/40 font-mono uppercase tracking-wider"
          >
            <RotateCcw className="w-3 h-3 text-[#C6A15B]" /> Clear Session
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-sm bg-[#553C3C]/30 hover:bg-[#553C3C]/50 text-[#DA9A9A] font-medium text-xs transition border border-[#A16B6B]/30 hover:border-[#DA6B6B]/50 font-mono uppercase tracking-wider"
          >
            <LogOut className="w-3 h-3" /> Logout
          </button>
        </div>
      </aside>

      {/* MAIN WORKSPACE VIEW CONTAINER */}
      <main className="flex-1 flex flex-col h-full relative z-10">
        <header className="h-16 border-b border-[#C6A15B]/15 flex items-center justify-between px-6 bg-[#0E1725]/60 backdrop-blur-xl font-body">
          <div className="flex items-center gap-3">
            <span className="w-2 h-2 rounded-full bg-[#7D9471] animate-pulse"></span>
            <h2 className="text-sm font-semibold tracking-wide text-[#D9D2BF] font-display">
              {activeView === "chat" ? "AI Real Estate Workspace" : "Property Room Verification Engine"}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            {activeView === "chat" ? (
              <button
                onClick={() => setActiveView("verify")}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#C6A15B]/20 hover:bg-[#C6A15B]/30 text-[#C6A15B] border border-[#C6A15B]/50 rounded-sm text-xs font-mono transition"
              >
                <Sparkles className="w-3.5 h-3.5" /> 🏠 Verify Property
              </button>
            ) : (
              <button
                onClick={() => setActiveView("chat")}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-[#141F30] hover:bg-[#1A2536] text-[#D9D2BF] border border-[#2C3A50] rounded-sm text-xs font-mono transition"
              >
                <ChevronRight className="w-3.5 h-3.5 rotate-180" /> Back to Chat
              </button>
            )}
            <div className="text-[10px] font-mono bg-[#141F30] text-[#C6A15B] border border-[#C6A15B]/25 px-3 py-1 rounded-sm uppercase tracking-wider hidden lg:block">
              {activeView === "chat" ? `Session · ${activeSessionId || "Init"}` : "Places365 Vision Model"}
            </div>
            <button
              onClick={handleLogout}
              title="Logout"
              className="flex items-center gap-1.5 px-3 py-1.5 bg-[#553C3C]/30 hover:bg-[#553C3C]/50 text-[#DA9A9A] border border-[#A16B6B]/30 hover:border-[#DA6B6B]/50 rounded-sm text-xs font-mono transition"
            >
              <LogOut className="w-3.5 h-3.5" /> Logout
            </button>
          </div>
        </header>

        {activeView === "chat" ? (
          <>
            <div className="flex-1 overflow-y-auto p-6 space-y-6 font-body">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex items-start gap-3.5 max-w-3xl ${msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"}`}>
                  <div className={`p-2 rounded-full flex-shrink-0 shadow-lg border ${msg.role === "user" ? "bg-[#C6A15B] text-[#0C1420] border-[#C6A15B]" : "bg-[#0E1725] text-[#C6A15B] border-[#C6A15B]/40"}`}>
                    {msg.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                  </div>

                  <div className={`relative rounded-md px-5 py-3.5 shadow-xl text-sm leading-relaxed space-y-2.5 ${msg.role === "user" ? "bg-[#C6A15B] text-[#0C1420] rounded-tr-none shadow-black/30" : "bg-[#0E1725]/90 border border-[#2C3A50] text-[#D9D2BF] rounded-tl-none shadow-black/40 pl-6"}`}>
                    {msg.role === "assistant" && <span className="absolute left-0 top-0 bottom-0 w-1.5 bg-gradient-to-b from-[#C6A15B] to-[#7D9471] rounded-l-md" />}

                    {msg.steps && msg.steps.length > 0 && (
                      <div className="mb-3 p-2.5 rounded-sm bg-[#070C14] border border-[#2C3A50] text-xs font-mono text-[#9CC4E0] space-y-1.5 shadow-inner">
                        <div className="flex items-center gap-1.5 text-[10px] text-[#C6A15B] uppercase tracking-wider font-semibold border-b border-[#2C3A50]/60 pb-1 mb-1">
                          <Cpu className="w-3 h-3 animate-spin" /> LangGraph Telemetry Trace
                        </div>
                        {msg.steps.map((step, sIdx) => (
                          <div key={sIdx} className="flex items-center gap-2 text-[11px]">
                            <CheckCircle2 className="w-3 h-3 text-[#7D9471] flex-shrink-0" />
                            <span className="text-[#C9BFA6]">{step}</span>
                          </div>
                        ))}
                        {loading && idx === messages.length - 1 && (
                          <div className="flex items-center gap-2 text-[11px] text-[#7D8AA1] italic pt-0.5">
                            <Loader2 className="w-3 h-3 animate-spin text-[#C6A15B]" />
                            <span>Processing next graph node...</span>
                          </div>
                        )}
                      </div>
                    )}

                    {msg.intent && msg.role === "assistant" && renderIntentBadge(msg.intent, msg.filters)}

                    {msg.role === "assistant" && Array.isArray(msg.properties) && msg.properties.length > 0 && (
                      <div className="mb-3 space-y-2">
                        <div className="flex items-center gap-1.5 text-[11px] text-[#9FBF9A] uppercase tracking-wider font-mono font-semibold pb-1 border-b border-[#3F5142]/40">
                          <ShieldCheck className="w-3.5 h-3.5" /> EstateAgent AI Listings ({msg.properties.length})
                        </div>
                        {msg.properties.map((p) => {
                          const st = interestState[p.id] || {};
                          return (
                            <div key={p.id} className="rounded-sm border border-[#3F5142]/50 bg-[#0B1510]/70 p-3 space-y-2">
                              {Array.isArray(p.image_urls) && p.image_urls.length > 0 && (
                                <div className="flex gap-1.5 overflow-x-auto no-scrollbar">
                                  {p.image_urls.map((url, i) => (
                                    <img key={i} src={`${MEDIA_BASE}${url}`} alt={`${p.property_name} ${i + 1}`} loading="lazy"
                                      onClick={() => setLightboxSrc(`${MEDIA_BASE}${url}`)}
                                      className="h-20 w-28 flex-shrink-0 object-cover rounded-sm border border-[#2C3A50] bg-[#070C14] cursor-zoom-in hover:brightness-110 transition" />
                                  ))}
                                </div>
                              )}
                              <div className="flex items-start justify-between gap-2">
                                <div>
                                  <p className="text-sm font-display text-[#F3EEE1]">{p.property_name}</p>
                                  <p className="text-[11px] text-[#8892A3] font-mono flex items-center gap-1"><MapPin className="w-3 h-3 text-[#C6A15B]" /> {p.location}{p.city ? `, ${p.city}` : ""}</p>
                                </div>
                                {p.availability_status && (
                                  <span className="text-[9px] font-mono uppercase tracking-wider bg-[#3F5142]/40 text-[#9FBF9A] border border-[#6E8B6E]/40 px-2 py-0.5 rounded-sm flex-shrink-0">{p.availability_status}</span>
                                )}
                              </div>
                              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-mono text-[#C9BFA6]">
                                <span className="text-[#F3EEE1] font-semibold">₹ {Number(p.price_in_inr || 0).toLocaleString("en-IN")}</span>
                                {p.bhk != null && <span className="flex items-center gap-1"><BedDouble className="w-3 h-3 text-[#7D9471]" /> {p.bhk} BHK</span>}
                                {p.area_sqft != null && <span>{p.area_sqft} {p.area_unit || "sqft"}</span>}
                                {p.property_type && <span className="text-[#7D8AA1]">{p.property_type}</span>}
                              </div>

                              {st.data ? (
                                <div className="mt-1 p-2.5 rounded-sm bg-[#0E1725] border border-[#6E8B6E]/40 text-[11px] space-y-1">
                                  <div className="flex items-center gap-1.5 text-[#9FBF9A] font-mono uppercase tracking-wider text-[10px] font-semibold">
                                    <CheckCircle className="w-3 h-3" /> Interest sent — broker contact
                                  </div>
                                  <p className="text-[#EDE7D9]">{st.data.broker?.name || "Broker"}</p>
                                  {st.data.broker?.phone && <p className="text-[#C9BFA6] font-mono">📞 {st.data.broker.phone}</p>}
                                  {st.data.broker?.email && <p className="text-[#C9BFA6] font-mono">✉️ {st.data.broker.email}</p>}
                                  <p className="text-[10px] text-[#7D8AA1] pt-1">{st.data.notice}</p>
                                </div>
                              ) : (
                                <button
                                  onClick={() => handleExpressInterest(p.id)}
                                  disabled={st.loading}
                                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm bg-[#C6A15B] hover:bg-[#D9B876] disabled:opacity-50 text-[#0C1420] text-[11px] font-mono font-semibold uppercase tracking-wider transition"
                                >
                                  {st.loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                                  {st.loading ? "Sending..." : "Interested"}
                                </button>
                              )}
                              {st.error && <p className="text-[10px] text-[#DA6B6B] font-mono">{st.error}</p>}
                            </div>
                          );
                        })}
                      </div>
                    )}

                    <div className={`prose prose-sm max-w-none ${msg.role === "user" ? "prose-p:text-[#0C1420] prose-strong:text-[#0C1420]" : "prose-invert prose-p:text-[#D9D2BF] prose-strong:text-[#F3EEE1] prose-a:text-[#C6A15B]"}`}>
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={{ a: ({ node, ...props }) => (<a {...props} target="_blank" rel="noopener noreferrer" className="text-[#C6A15B] underline hover:text-[#D9B876] font-medium inline-flex items-center gap-1" />) }}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="px-6 py-2.5 bg-[#0E1725]/70 backdrop-blur-md border-t border-[#C6A15B]/15 flex items-center gap-2 overflow-x-auto no-scrollbar font-mono">
              <span className="text-[10px] font-semibold text-[#7D8AA1] uppercase tracking-[0.15em] flex-shrink-0">Quick Queries:</span>
              <button onClick={() => handleSend("Find 3 BHK flats in Indore under 3 Cr")} disabled={loading} className="text-xs bg-[#141F30]/80 hover:bg-[#1A2536] text-[#D9D2BF] px-3 py-1.5 rounded-sm border border-[#2C3A50] hover:border-[#C6A15B]/40 transition flex items-center gap-1.5 flex-shrink-0 disabled:opacity-50 shadow-sm">
                <Home className="w-3 h-3 text-[#7D9471]" />
                <span>3 BHK in Indore &lt; 3 Cr</span>
                <ChevronRight className="w-3 h-3 text-[#7D8AA1]" />
              </button>
              <button onClick={() => setActiveView("verify")} className="text-xs bg-[#C6A15B]/15 hover:bg-[#C6A15B]/25 text-[#C6A15B] px-3 py-1.5 rounded-sm border border-[#C6A15B]/40 transition flex items-center gap-1.5 flex-shrink-0 shadow-sm">
                <Sparkles className="w-3 h-3 text-[#C6A15B]" />
                <span>🏠 Verify Property Photos</span>
                <ChevronRight className="w-3 h-3 text-[#C6A15B]" />
              </button>
            </div>

            <div className="p-4 bg-[#0E1725]/80 backdrop-blur-xl border-t border-[#C6A15B]/15 shadow-2xl font-body">
              <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="max-w-4xl mx-auto relative flex items-center">
                <input type="text" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Search properties, BHK sizes, live listings, or locations..." disabled={loading} className="w-full bg-[#0A121D]/90 border border-[#2C3A50] focus:border-[#C6A15B] rounded-md py-4 pl-5 pr-14 text-sm text-[#EDE7D9] placeholder-[#7D8AA1] focus:outline-none focus:ring-2 focus:ring-[#C6A15B]/30 transition shadow-inner disabled:opacity-50" />
                <button type="submit" disabled={loading || !input.trim()} aria-label="Send message" className="absolute right-2.5 p-2.5 bg-[#C6A15B] hover:bg-[#D9B876] disabled:opacity-40 disabled:hover:bg-[#C6A15B] text-[#0C1420] rounded-sm transition shadow-lg">
                  <Send className="w-4 h-4" />
                </button>
              </form>
              <p className="text-center text-[10px] font-mono uppercase tracking-wider text-[#7D8AA1] mt-2.5">Powered by LangGraph Agent Orchestrator &amp; Gemini 3.6-Flash Engine</p>
            </div>
          </>
        ) : (
          <div className="flex-1 overflow-y-auto p-8 font-body space-y-8 max-w-5xl mx-auto w-full">
            <div className="bg-[#0E1725]/80 border border-[#C6A15B]/30 p-6 rounded-md shadow-2xl space-y-6">
              <div>
                <h3 className="text-lg font-display text-[#F3EEE1] flex items-center gap-2"><Sparkles className="w-5 h-5 text-[#C6A15B]" /> Property Room &amp; BHK Verification</h3>
                <p className="text-xs text-[#8892A3] mt-1">Upload listing photographs to independently verify declared BHK configurations using Places365 pretrained scene classification AI.</p>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-[#C6A15B] font-semibold">Select Claimed Configuration:</label>
                <div className="flex gap-3">
                  {[1, 2, 3, 4, 5].map((bhk) => (
                    <button key={bhk} onClick={() => setSelectedBhk(bhk)} className={`px-4 py-2 rounded-sm text-xs font-mono font-semibold transition border ${selectedBhk === bhk ? "bg-[#C6A15B] text-[#0C1420] border-[#C6A15B]" : "bg-[#141F30] text-[#D9D2BF] border-[#2C3A50] hover:border-[#C6A15B]/40"}`}>
                      {bhk} BHK
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-xs font-mono uppercase tracking-wider text-[#C6A15B] font-semibold">Upload Room Photos (Max 8):</label>
                <div onDragOver={(e) => e.preventDefault()} onDrop={handleFileDrop} className="border-2 border-dashed border-[#2C3A50] hover:border-[#C6A15B]/50 rounded-md p-8 text-center bg-[#070C14]/60 transition flex flex-col items-center justify-center cursor-pointer relative" onClick={() => document.getElementById("hiddenFileInput").click()}>
                  <input id="hiddenFileInput" type="file" multiple accept="image/*" className="hidden" onChange={handleFileSelect} />
                  <Upload className="w-8 h-8 text-[#C6A15B] mb-2" />
                  <p className="text-sm text-[#D9D2BF] font-medium">Drag and drop apartment photos here, or click to browse</p>
                  <p className="text-[11px] text-[#7D8AA1] mt-1">Supports PNG, JPG, JPEG (Analyzes distinct bedrooms)</p>
                </div>
              </div>

              {selectedFiles.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-mono text-[#7D8AA1]">Selected Photos ({selectedFiles.length}/8):</p>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {selectedFiles.map((file, idx) => (
                      <div key={idx} className="relative group rounded-md overflow-hidden border border-[#2C3A50] bg-[#070C14] h-28">
                        <img src={URL.createObjectURL(file)} alt={file.name} className="w-full h-full object-cover" />
                        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center">
                          <button onClick={(e) => { e.stopPropagation(); removeFile(idx); }} className="p-1.5 bg-red-600 hover:bg-red-700 text-white rounded-full transition" title="Remove Image"><X className="w-3.5 h-3.5" /></button>
                        </div>
                        <span className="absolute bottom-1 left-1 bg-black/70 text-[9px] font-mono px-1.5 py-0.5 rounded text-[#EDE7D9]">#{idx + 1}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button onClick={handleVerifySubmit} disabled={selectedFiles.length === 0 || verifyLoading} className="w-full py-3 bg-[#C6A15B] hover:bg-[#D9B876] disabled:opacity-40 text-[#0C1420] font-semibold text-xs rounded-sm transition font-mono uppercase tracking-wider flex items-center justify-center gap-2 shadow-lg">
                {verifyLoading ? (<><Loader2 className="w-4 h-4 animate-spin" /> Analyzing via Places365 CNN...</>) : (<><Sparkles className="w-4 h-4" /> Verify BHK Configuration Now</>)}
              </button>
            </div>

            {verifyResult && (
              <div className="bg-[#0E1725]/90 border border-[#2C3A50] p-6 rounded-md shadow-2xl space-y-6">
                <div className="flex items-center justify-between border-b border-[#2C3A50] pb-4">
                  <div>
                    <h4 className="text-sm font-mono uppercase tracking-wider text-[#C6A15B]">Verification Audit Report</h4>
                    <p className="text-xs text-[#8892A3] mt-0.5">Analyzed {verifyResult.images_analyzed} uploaded photographs</p>
                  </div>
                  <div className={`px-3 py-1 rounded-sm text-xs font-mono uppercase tracking-wider flex items-center gap-1.5 border ${verifyResult.verdict.matches ? "bg-[#3F5142]/40 text-[#9FBF9A] border-[#6E8B6E]/40" : "bg-[#553C3C]/40 text-[#DA6B6B] border-[#A16B6B]/40"}`}>
                    {verifyResult.verdict.matches ? <CheckCircle className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
                    {verifyResult.verdict.matches ? "Config Verified Match" : "Mismatch Warning"}
                  </div>
                </div>

               {/* Aggregate Verdict Summary Card */}
                <div className="p-4 bg-[#070C14] rounded-sm border border-[#2C3A50] space-y-2">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-[#8892A3]">Claimed BHK:</span>
                    <span className="text-[#F3EEE1] font-semibold">{verifyResult.verdict.claimed_bhk} BHK</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-[#8892A3]">Unique Bedrooms Detected:</span>
                    <span className="text-[#F3EEE1] font-semibold">{verifyResult.verdict.unique_bedrooms_detected} Found (from {verifyResult.verdict.raw_bedroom_photos} photos)</span>
                  </div>
                  
                  {verifyResult.verdict.duplicate_groups?.length > 0 && (
                    <div className="mt-3 p-2.5 bg-[#553C3C]/20 border border-[#DA6B6B]/30 rounded-sm space-y-1.5">
                      <div className="flex items-center gap-1.5 text-[10px] text-[#DA6B6B] font-mono uppercase tracking-wider font-semibold">
                        <AlertTriangle className="w-3 h-3" /> Duplicate Photos Detected
                      </div>
                      {verifyResult.verdict.duplicate_groups.map((group, gIdx) => (
                         <p key={gIdx} className="text-xs text-[#C9BFA6] font-body">
                           ⚠️ Photos #{group.photo_indices.join(" and #")} look like the same room ({(group.similarity * 100).toFixed(1)}% match).
                         </p>
                      ))}
                    </div>
                  )}
                  {verifyResult.verdict.low_confidence_warning && (
    <div className="mt-3 p-2.5 bg-[#5C4A2E]/20 border border-[#C6A15B]/30 rounded-sm space-y-1.5">
      <div className="flex items-center gap-1.5 text-[10px] text-[#C6A15B] font-mono uppercase tracking-wider font-semibold">
        <AlertTriangle className="w-3 h-3" /> Low Confidence — Manual Check Suggested
      </div>
      <p className="text-xs text-[#C9BFA6] font-body">
        {verifyResult.verdict.low_confidence_warning}
      </p>
    </div>
  )}

                  <p className="text-xs text-[#C9BFA6] pt-2 border-t border-[#2C3A50]/60 leading-relaxed font-body">
                    {verifyResult.verdict.confidence_note}
                  </p>
                </div>

                {/* Per-image breakdown */}
                <div className="space-y-3">
                  <p className="text-xs font-mono uppercase tracking-wider text-[#7D8AA1]">Per-Image Scene Classification Details:</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {verifyResult.verdict.all_detected_rooms.map((room, rIdx) => {
                      const isDuplicate = verifyResult.verdict.duplicate_groups?.some(g => g.photo_indices.includes(room.image_index));
                      return (
                        <div key={rIdx} className={`p-3 bg-[#070C14]/80 border ${isDuplicate ? "border-[#DA6B6B]/40 bg-[#553C3C]/10" : "border-[#2C3A50]"} rounded-sm flex items-center justify-between text-xs transition-colors`}>
                          <div className="space-y-1">
                            <span className="font-mono text-[#C6A15B] font-semibold">
                              Photo #{room.image_index}
                              {isDuplicate && <span className="ml-2 bg-[#553C3C]/60 text-[#DA6B6B] px-1.5 py-0.5 rounded text-[9px] uppercase tracking-wider border border-[#A16B6B]/40">Duplicate</span>}
                            </span>
                            <p className="text-[#EDE7D9] capitalize font-medium">Mapped: {room.room_type.replace("_", " ")}</p>
                            <p className="text-[10px] text-[#7D8AA1] font-mono">Raw Scene: {room.raw_category}</p>
                          </div>
                          <div className="text-right font-mono">
                            <span className={`px-2 py-0.5 rounded text-[10px] ${room.room_type === "bedroom" ? "bg-[#3F5142]/40 text-[#9FBF9A]" : "bg-[#141F30] text-[#8892A3]"}`}>
                              {(room.confidence * 100).toFixed(1)}% conf
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                <div className="pt-2 flex justify-end">
                  <button onClick={() => setActiveView("chat")} className="px-4 py-2 bg-[#141F30] hover:bg-[#1A2536] text-[#D9D2BF] border border-[#2C3A50] rounded-sm text-xs font-mono transition">
                    Return to Active Chat
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
      </>
      )}

      {lightboxSrc && (
        <div
          onClick={() => setLightboxSrc(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-6 cursor-zoom-out"
        >
          <button
            onClick={() => setLightboxSrc(null)}
            aria-label="Close image"
            className="absolute top-4 right-4 p-2 bg-[#0E1725]/80 border border-[#C6A15B]/40 text-[#EDE7D9] rounded-sm hover:bg-[#1A2536] transition"
          >
            <X className="w-5 h-5" />
          </button>
          <img
            src={lightboxSrc}
            alt="Property photo enlarged"
            onClick={(e) => e.stopPropagation()}
            className="max-w-full max-h-full object-contain rounded-md shadow-2xl border border-[#2C3A50] cursor-default"
          />
        </div>
      )}
    </div>
  );
}