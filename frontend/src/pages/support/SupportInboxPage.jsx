import { useCallback, useEffect, useRef, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { useAuth } from "../../context/AuthContext";
import { api } from "../../services/api";

const POLL_MS = 3500;

function formatDate(value) {
  if (!value) return "";
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function SupportInboxPage() {
  const { user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [newConversations, setNewConversations] = useState(0);
  const [selectedId, setSelectedId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [body, setBody] = useState("");
  const [status, setStatus] = useState("open");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);
  const lastMessageIdRef = useRef(0);

  const loadInbox = useCallback(async () => {
    try {
      const result = await api.get(`/support/staff/conversations?status=${status}`);
      setConversations(result.conversations);
      setNewConversations(result.new_conversations);
      setError("");
      return result.conversations;
    } catch (loadError) {
      setError(loadError.message);
      return null;
    } finally {
      setLoading(false);
    }
  }, [status]);

  const loadSelectedMessages = useCallback(async (conversationId, initial = false) => {
    const afterId = initial ? "" : `?after_id=${lastMessageIdRef.current}`;
    const result = await api.get(`/support/staff/conversations/${conversationId}/messages${afterId}`);
    setMessages((current) => initial ? result.messages : [...current, ...result.messages]);
    if (result.messages.length) {
      lastMessageIdRef.current = result.messages.at(-1).id;
    } else if (initial) {
      lastMessageIdRef.current = 0;
    }
    setError("");
  }, []);

  useEffect(() => {
    loadInbox();
    const timer = window.setInterval(() => {
      loadInbox().catch((pollError) => console.error("Không thể cập nhật hộp thư hỗ trợ.", pollError));
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [loadInbox]);

  useEffect(() => {
    if (!selectedId) {
      setMessages([]);
      return undefined;
    }
    let active = true;
    setMessages([]);
    lastMessageIdRef.current = 0;
    loadSelectedMessages(selectedId, true).catch((loadError) => setError(loadError.message));
    const timer = window.setInterval(async () => {
      try {
        const result = await api.get(
          `/support/staff/conversations/${selectedId}/messages?after_id=${lastMessageIdRef.current}`
        );
        if (!active) return;
        if (result.messages.length) {
          setMessages((current) => [...current, ...result.messages]);
          lastMessageIdRef.current = result.messages.at(-1).id;
        }
      } catch (pollError) {
        console.error("Không thể cập nhật tin nhắn hỗ trợ.", pollError);
      }
    }, POLL_MS);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [loadSelectedMessages, selectedId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [messages]);

  async function selectConversation(conversation) {
    setSelectedId(conversation.id);
    setBody("");
    await loadInbox();
  }

  async function sendReply(event) {
    event.preventDefault();
    const text = body.trim();
    if (!text || !selectedId || sending) return;
    setSending(true);
    setError("");
    try {
      const result = await api.post(`/support/staff/conversations/${selectedId}/messages`, { body: text });
      setMessages((current) => [...current, result.message]);
      lastMessageIdRef.current = result.message.id;
      setBody("");
      await loadInbox();
    } catch (sendError) {
      setError(sendError.message);
    } finally {
      setSending(false);
    }
  }

  async function acceptConversation() {
    if (!selectedId) return;
    setError("");
    try {
      await api.post(`/support/staff/conversations/${selectedId}/accept`, {});
      await Promise.all([loadInbox(), loadSelectedMessages(selectedId, true)]);
    } catch (acceptError) {
      setError(acceptError.message);
      await loadInbox();
    }
  }

  async function closeConversation() {
    if (!selectedId) return;
    setError("");
    try {
      await api.post(`/support/staff/conversations/${selectedId}/close`, {});
      setSelectedId(null);
      setMessages([]);
      await loadInbox();
    } catch (closeError) {
      setError(closeError.message);
    }
  }

  const selected = conversations.find((conversation) => conversation.id === selectedId);

  if (loading && !conversations.length) return <Loading />;

  return (
    <section className="support-inbox-page">
      <div className="support-inbox-title">
        <div>
          <h1 className="page-title">Chat hỗ trợ khách hàng</h1>
          <p className="muted">Tin nhắn của khách được cập nhật tự động.</p>
        </div>
        <div className="support-inbox-tabs" role="group" aria-label="Lọc cuộc trò chuyện">
          {[
            ["open", "Đang mở"],
            ["closed", "Đã đóng"],
            ["all", "Tất cả"],
          ].map(([value, label]) => (
            <button key={value} type="button" className={`btn btn-sm ${status === value ? "btn-red" : "btn-ghost"}`}
              onClick={() => { setStatus(value); setSelectedId(null); }}>
              {label}
            </button>
          ))}
        </div>
      </div>
      {status === "open" && newConversations > 0 && (
        <p className="support-inbox-notice" role="status" aria-live="polite">
          <strong>{newConversations} khách hàng đang muốn chat.</strong> Mở cuộc trò chuyện để xem và phản hồi.
        </p>
      )}
      {error && <ErrorBox message={error} />}
      <div className="support-inbox-layout">
        <aside className="support-inbox-list" aria-label="Cuộc trò chuyện">
          {!conversations.length
            ? <p className="support-inbox-empty">Chưa có khách hàng nhắn tin.</p>
            : conversations.map((conversation) => (
              <button type="button" key={conversation.id}
                className={`support-inbox-conversation${selectedId === conversation.id ? " selected" : ""}`}
                onClick={() => selectConversation(conversation)}>
                <span className="support-inbox-avatar" aria-hidden="true">
                  {conversation.customer_name.trim().charAt(0).toLocaleUpperCase("vi-VN")}
                </span>
                <span className="support-inbox-conversation-copy">
                  <strong>{conversation.customer_name}</strong>
                  <small>{conversation.latest_message?.body || "Chưa có tin nhắn"}</small>
                  <small>{formatDate(conversation.updated_at)}</small>
                </span>
                {conversation.unread_count > 0 && (
                  <span className="support-inbox-unread" aria-label={`${conversation.unread_count} tin nhắn chưa đọc`}>
                    {conversation.unread_count}
                  </span>
                )}
              </button>
            ))}
        </aside>
        <section className="support-inbox-thread" aria-label="Nội dung chat">
          {!selected ? (
            <div className="support-inbox-empty support-inbox-prompt">
              <span aria-hidden="true">💬</span>
              <p>Chọn cuộc trò chuyện để xem và trả lời khách hàng.</p>
            </div>
          ) : (
            <>
              <header className="support-inbox-thread-header">
                <div>
                  <strong>{selected.customer_name}</strong>
                  <small>{selected.customer_email}</small>
                </div>
                {selected.status === "open" && (
                  <div className="support-inbox-thread-actions">
                    {!selected.assigned_staff_id && (
                      <button className="btn btn-red btn-sm" type="button" onClick={acceptConversation}>
                        Nhận trò chuyện
                      </button>
                    )}
                    <button className="btn btn-ghost btn-sm" type="button" onClick={closeConversation}>
                      Đóng cuộc trò chuyện
                    </button>
                  </div>
                )}
              </header>
              <p className="support-inbox-assigned" role="status">
                {!selected.assigned_staff_id
                  ? "Chưa có nhân viên nhận cuộc trò chuyện."
                  : selected.assigned_staff_id === user?.id
                    ? "Bạn đang phụ trách cuộc trò chuyện này."
                    : `Đang được ${selected.assigned_staff_name} hỗ trợ.`}
              </p>
              <div className="support-inbox-messages" aria-live="polite">
                {messages.map((message) => {
                  const isSystem = message.sender_role === "SYSTEM";
                  const isStaff = message.sender_role !== "USER" && !isSystem;
                  return (
                    <article className={`support-inbox-message${isSystem ? " system" : isStaff ? " staff" : ""}`} key={message.id}>
                      <small>{message.sender_name} · {isSystem ? "Thông báo" : isStaff ? "Nhân viên" : "Khách hàng"}</small>
                      <p>{message.body}</p>
                      <time dateTime={message.created_at}>{formatDate(message.created_at)}</time>
                    </article>
                  );
                })}
                <div ref={endRef} />
              </div>
              {selected.status === "open" && (
                selected.assigned_staff_id === user?.id || user?.role === "ADMIN"
              )
                ? <form className="support-inbox-compose" onSubmit={sendReply}>
                    <textarea value={body} onChange={(event) => setBody(event.target.value)} maxLength={2000}
                      rows={2} placeholder="Trả lời khách hàng..." aria-label="Tin nhắn trả lời" />
                    <button className="btn btn-red" type="submit" disabled={sending || !body.trim()}>
                      {sending ? "Đang gửi..." : "Gửi trả lời"}
                    </button>
                  </form>
                : selected.status !== "open"
                  ? <p className="support-inbox-closed">Cuộc trò chuyện này đã đóng.</p>
                  : !selected.assigned_staff_id
                    ? <p className="support-inbox-closed">Nhận cuộc trò chuyện để bắt đầu trả lời khách hàng.</p>
                    : <p className="support-inbox-closed">Nhân viên phụ trách mới có thể trả lời cuộc trò chuyện này.</p>}
            </>
          )}
        </section>
      </div>
    </section>
  );
}
