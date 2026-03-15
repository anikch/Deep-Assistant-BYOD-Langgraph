"use client";

import { useState, useRef, useEffect } from "react";
import { Message, Citation } from "@/types";
import { chatApi } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatPanelProps {
  sessionId: string;
  messages: Message[];
  onMessageSent: (userMsg: Message, assistantMsg: Message) => void;
  loading: boolean;
}

export default function ChatPanel({ sessionId, messages, onMessageSent, loading }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    setError("");
    const message = input.trim();
    setInput("");
    setSending(true);

    // Optimistic user message
    const tempUserMsg: Message = {
      id: "temp-" + Date.now(),
      session_id: sessionId,
      user_id: "",
      role: "user",
      content: message,
      created_at: new Date().toISOString(),
    };

    try {
      const res = await chatApi.sendMessage(sessionId, message);
      const assistantMsg: Message = {
        id: res.data.message_id,
        session_id: sessionId,
        user_id: "",
        role: "assistant",
        content: res.data.content,
        structured_payload: {
          plan: res.data.plan,
          citations: res.data.citations,
          agent_run_id: res.data.agent_run_id,
          clarification_needed: res.data.clarification_needed,
        },
        created_at: res.data.created_at,
      };
      onMessageSent(tempUserMsg, assistantMsg);
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail || "Failed to send message");
      onMessageSent(tempUserMsg, {
        id: "err-" + Date.now(),
        session_id: sessionId,
        user_id: "",
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        created_at: new Date().toISOString(),
      });
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 && !loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md">
              <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Start a conversation</h3>
              <p className="text-slate-500 text-sm">
                Ask questions about your sources, request analysis, or explore research topics.
              </p>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <MessageItem key={msg.id} message={msg} />
            ))}
            {sending && (
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <div className="bg-white rounded-2xl rounded-tl-none p-4 shadow-sm border border-slate-200">
                  <div className="flex items-center gap-2 text-slate-500 text-sm">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                      <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                      <div className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                    </div>
                    <span>Researching...</span>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="px-6 pb-2">
          <p className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-slate-200 bg-white">
        <div className="flex items-end gap-3 bg-slate-50 rounded-2xl border border-slate-200 p-3 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-100 transition-all">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question... (Enter to send, Shift+Enter for new line)"
            className="flex-1 bg-transparent text-sm text-slate-900 placeholder-slate-400 resize-none focus:outline-none max-h-32 min-h-[20px]"
            rows={1}
            style={{ height: "auto" }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = "auto";
              target.style.height = Math.min(target.scrollHeight, 128) + "px";
            }}
            disabled={sending}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || sending}
            className="flex-shrink-0 w-8 h-8 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-1 text-center">
          AI can make mistakes. Verify important information.
        </p>
      </div>
    </div>
  );
}

function MessageItem({ message }: { message: Message }) {
  const [showPlan, setShowPlan] = useState(false);
  const [showCitations, setShowCitations] = useState(false);
  const isUser = message.role === "user";
  const plan = message.structured_payload?.plan;
  const citations = message.structured_payload?.citations;

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-indigo-600 text-white rounded-2xl rounded-tr-none px-4 py-3 shadow-sm">
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 max-w-[85%]">
      <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
      </div>
      <div className="flex-1">
        <div className="bg-white rounded-2xl rounded-tl-none p-4 shadow-sm border border-slate-200">
          <div className="markdown-content text-sm text-slate-800">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        </div>

        {/* Plan section */}
        {plan && plan.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowPlan(!showPlan)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors"
            >
              <svg className={`w-3.5 h-3.5 transition-transform ${showPlan ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Research Plan ({plan.length} steps)
            </button>
            {showPlan && (
              <div className="mt-2 bg-indigo-50 rounded-xl p-3 border border-indigo-100">
                <ol className="space-y-1.5">
                  {plan.map((step, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-slate-700">
                      <span className="flex-shrink-0 w-5 h-5 bg-indigo-200 text-indigo-700 rounded-full flex items-center justify-center font-medium">
                        {i + 1}
                      </span>
                      {step.replace(/^Step \d+:\s*/i, "")}
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        )}

        {/* Citations section */}
        {citations && citations.length > 0 && (
          <div className="mt-2">
            <button
              onClick={() => setShowCitations(!showCitations)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700 transition-colors"
            >
              <svg className={`w-3.5 h-3.5 transition-transform ${showCitations ? "rotate-90" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              Sources ({citations.length})
            </button>
            {showCitations && (
              <div className="mt-2 space-y-2">
                {citations.map((citation: Citation, i: number) => (
                  <div key={i} className="bg-slate-50 rounded-xl p-3 border border-slate-200">
                    <p className="text-xs font-medium text-slate-700 mb-1">
                      [{i + 1}] {citation.source_name}
                    </p>
                    <p className="text-xs text-slate-500 line-clamp-3 italic">{citation.excerpt}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
