import React, { useState, useEffect, useRef } from "react";
import { 
  Building2, Send, Bot, User, Database, FileText, Globe, Sparkles, 
  RotateCcw, Loader2, SlidersHorizontal, ChevronRight, Home, ShieldCheck, 
  Cpu, CheckCircle2, Plus, MessageSquare, Trash2, Upload, X, CheckCircle, AlertTriangle
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_STREAM_URL = "http://localhost:8000/api/v1/chat-stream";
const API_VERIFY_URL = "http://localhost:8000/api/v1/verify-property";

const HERO_IMAGE = "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=2000&q=80";
const SIDEBAR_IMAGE = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=80";

export default function App() {
  const [activeView, setActiveView] = useState("chat");
  
  const [selectedBhk, setSelectedBhk] = useState(2);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);

  const [sessions, setSessions] = useState(() => {
    const saved = localStorage.getItem("estate_chat_sessions");
    if (saved) {
      try { return JSON.parse(saved); } catch (e) { }
    }
    return [];
  });
  
  const [activeSessionId, setActiveSessionId] = useState("");
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: "Welcome to **EstateAgent AI**! Discover luxury homes, browse project brochures, or check live market insights with our multi-agent assistant.",
      intent: null,
      filters: null,
      steps: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (sessions.length === 0) {
      createNewChat();
    } else {
      setActiveSessionId(sessions[0].id);
      setMessages(sessions[0].messages);
    }
  }, []);

  useEffect(() => {
    if (activeSessionId && sessions.length > 0) {
      const updated = sessions.map((s) => {
        if (s.id === activeSessionId) {
          return { ...s, messages, title: sessions.find(x => x.id === activeSessionId)?.title || "New Chat" };
        }
        return s;
      });
      setSessions(updated);
      localStorage.setItem("estate_chat_sessions", JSON.stringify(updated));
    }
  }, [messages]);

  const createNewChat = () => {
    const newId = "session_" + Math.random().toString(36).substring(2, 9);
    const initialMsg = {
      role: "assistant",
      content: "Welcome to **EstateAgent AI**! How can I assist you with your property search today?",
      intent: null, filters: null, steps: [],
    };
    const newSession = { id: newId, title: "New Conversation", messages: [initialMsg] };
    
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
    setMessages([initialMsg]);
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
    localStorage.setItem("estate_chat_sessions", JSON.stringify(filtered));

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
      { role: "assistant", content: "", intent: null, filters: null, steps: [] }
    ]);
    setLoading(true);

    let currentSteps = [];
    let finalContent = "";
    let detectedIntent = null;
    let detectedFilters = null;

    try {
      const response = await fetch(API_STREAM_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_query: userText, thread_id: activeSessionId }),
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
                if (data.node === "router" || data.node === "classify_intent_node") nodeLabel = "🧠 Classifying intent & extracting filters";
                else if (data.node === "sql_execution_node") nodeLabel = "🗄️ Querying PostgreSQL database";
                else if (data.node === "rag_execution_node") nodeLabel = "📄 Scanning Qdrant vector documents";
                else if (data.node === "web_search_node") nodeLabel = "🌐 Fetching live web insights";
                else if (data.node === "synthesizer_node") nodeLabel = "✨ Synthesizing final response";

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

        <div className="pt-3 border-t border-[#C6A15B]/15 flex-shrink-0">
          <button
            onClick={() => { setActiveView("chat"); createNewChat(); }}
            className="flex items-center justify-center gap-2 w-full py-2 px-3 rounded-sm bg-[#141F30]/90 hover:bg-[#1A2536] text-[#D9D2BF] font-medium text-xs transition border border-[#2C3A50] hover:border-[#C6A15B]/40 font-mono uppercase tracking-wider"
          >
            <RotateCcw className="w-3 h-3 text-[#C6A15B]" /> Clear Session
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
            <div className="text-[10px] font-mono bg-[#141F30] text-[#C6A15B] border border-[#C6A15B]/25 px-3 py-1 rounded-sm uppercase tracking-wider">
              {activeView === "chat" ? `Session · ${activeSessionId || "Init"}` : "Places365 Vision Model"}
            </div>
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
    </div>
  );
}