import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../services/api";

const POLL_MS = 3500;

function formatTime(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    day: "2-digit",
    month: "2-digit",
  }).format(new Date(value));
}

export default function SupportChatWidget() {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [conversation, setConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);
  const lastMessageIdRef = useRef(0);

  const loadConversation = useCallback(async () => {
    if (!user) return;
    try {
      const result = await api.get("/support/conversation");
      setConversation(result);
      const initialMessages = result?.messages || [];
      setMessages(initialMessages);
      lastMessageIdRef.current = initialMessages.at(-1)?.id || 0;
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    }
  }, [user]);

  useEffect(() => {
    if (!open || !user) return undefined;
    setLoading(true);
    loadConversation().finally(() => setLoading(false));
    const timer = window.setInterval(async () => {
      if (!conversation?.id) return;
      try {
        const current = await api.get(
          `/support/conversation/${conversation.id}/messages?after_id=${lastMessageIdRef.current}`
        );
        setConversation(current.conversation);
        if (current.messages.length) {
          setMessages((previous) => [...previous, ...current.messages]);
          lastMessageIdRef.current = current.messages.at(-1).id;
        }
      } catch (pollError) {
        console.error("Không thể cập nhật tin nhắn hỗ trợ.", pollError);
      }
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [conversation?.id, loadConversation, open, user]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, open]);

  if (user && user.role !== "USER") return null;

  async function startConversation() {
    setLoading(true);
    setError("");
    try {
      const result = await api.post("/support/conversation", {});
      setConversation(result);
      setMessages(result.messages || []);
      lastMessageIdRef.current = result.messages?.at(-1)?.id || 0;
    } catch (startError) {
      setError(startError.message);
    } finally {
      setLoading(false);
    }
  }

  async function sendMessage(event) {
    event.preventDefault();
    const text = body.trim();
    if (!text || !conversation || sending) return;
    setSending(true);
    setError("");
    try {
      const result = await api.post(`/support/conversation/${conversation.id}/messages`, { body: text });
      setMessages((previous) => [...previous, result.message]);
      lastMessageIdRef.current = result.message.id;
      setBody("");
    } catch (sendError) {
      setError(sendError.message);
    } finally {
      setSending(false);
    }
  }

  return createPortal(
    <div className="support-chat-widget">
      {open && (
        <section className="support-chat-panel" aria-label="Chat với nhân viên CINEVO">
          <header className="support-chat-header">
            <div>
              <strong>Hỗ trợ Cinevo</strong>
              <small>
                {conversation?.assigned_staff_name
                  ? `Đang trò chuyện với ${conversation.assigned_staff_name}`
                  : conversation
                    ? "Đang tìm nhân viên hỗ trợ..."
                    : "Nhân viên CINEVO luôn sẵn sàng hỗ trợ"}
              </small>
            </div>
            <button type="button" aria-label="Đóng khung chat" onClick={() => setOpen(false)}>×</button>
          </header>
          {!user ? (
            <div className="support-chat-login">
              <p>Đăng nhập để trò chuyện với nhân viên Cinevo.</p>
              <Link className="btn btn-red" to="/user/login">Đăng nhập</Link>
            </div>
          ) : (
            <>
              <div className="support-chat-messages" aria-live="polite">
                {loading && !messages.length && <p className="support-chat-state">Đang tải cuộc trò chuyện...</p>}
                {conversation?.status === "closed" && (
                  <div className="support-chat-closed">
                    <p>Cuộc trò chuyện này đã kết thúc.</p>
                    <button className="btn btn-red btn-sm" type="button" onClick={startConversation} disabled={loading}>
                      Bắt đầu cuộc trò chuyện mới
                    </button>
                  </div>
                )}
                {conversation?.status === "open" && !conversation.assigned_staff_name && (
                  <p className="support-chat-waiting" role="status" aria-live="polite">
                    <span aria-hidden="true" /> Đang tìm nhân viên hỗ trợ
                  </p>
                )}
                {!loading && !conversation && (
                  <div className="support-chat-empty">
                    <span aria-hidden="true">💬</span>
                    <strong>Chúng tôi có thể giúp gì cho bạn?</strong>
                    <p>Bắt đầu chat để kết nối với nhân viên hỗ trợ.</p>
                    <button className="btn btn-red" type="button" onClick={startConversation} disabled={loading}>
                      Bắt đầu trò chuyện
                    </button>
                  </div>
                )}
                {messages.map((message) => {
                  const system = message.sender_role === "SYSTEM";
                  const mine = !system && message.sender_id === user.id;
                  return (
                    <article className={`support-chat-message${system ? " system" : mine ? " mine" : ""}`} key={message.id}>
                      {!mine && <small>{message.sender_name}{!system && ` · ${message.sender_role === "ADMIN" ? "Quản trị viên" : "Nhân viên"}`}</small>}
                      <p>{message.body}</p>
                      <time dateTime={message.created_at}>{formatTime(message.created_at)}</time>
                    </article>
                  );
                })}
                <div ref={endRef} />
              </div>
              {conversation && (
                <form className="support-chat-compose" onSubmit={sendMessage}>
                  <textarea value={body} onChange={(event) => setBody(event.target.value)}
                    maxLength={2000} rows={2} placeholder="Nhập tin nhắn..." aria-label="Tin nhắn"
                    disabled={sending || conversation.status !== "open"} />
                  <button className="btn btn-red" type="submit"
                    disabled={sending || !body.trim() || conversation.status !== "open"}>
                    {sending ? "Đang gửi..." : "Gửi"}
                  </button>
                </form>
              )}
            </>
          )}
          {error && <p className="support-chat-error" role="alert">{error}</p>}
        </section>
      )}
      <button className={`support-chat-launcher${open ? " is-open" : ""}`} type="button"
        onClick={() => setOpen((current) => !current)} aria-expanded={open}
        aria-label={open ? "Đóng hỗ trợ" : "Mở hỗ trợ Cinevo"} title="Hỗ trợ">
        <span className="support-chat-icon" aria-hidden="true">
          {open ? (
            <svg viewBox="0 0 24 24"><path d="m6 6 12 12M18 6 6 18" /></svg>
          ) : (
            <svg viewBox="0 0 24 24">
              <path d="M20 11.5a7.5 7.5 0 0 1-7.5 7.5H5l1.5-3A7.5 7.5 0 1 1 20 11.5Z" />
              <path d="M9 12h.01M12.5 12h.01M16 12h.01" />
            </svg>
          )}
        </span>
      </button>
    </div>,
    document.body
  );
}
