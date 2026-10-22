import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { aiService } from "../services/aiService";

const assistantLines = [
  "Xin chào bạn! Bạn cần hỗ trợ gì?",
  "Bạn thích phim gì? Mình có thể cùng bạn khám phá nhé.",
  "Bạn thật dễ thương! Chúc bạn xem phim vui vẻ.",
];

function AssistantCharacter() {
  return (
    <svg className="assistant-character" viewBox="0 0 110 140" role="img" aria-label="Robot Cinevo đang vẫy tay">
      <defs>
        <linearGradient id="cinevo-robot-shell" x1="0" y1="0" x2="1" y2="1">
          <stop stopColor="#f7fdff" />
          <stop offset=".55" stopColor="#bcecff" />
          <stop offset="1" stopColor="#69b4e5" />
        </linearGradient>
        <linearGradient id="cinevo-robot-screen" x1="0" y1="0" x2="0" y2="1">
          <stop stopColor="#174d75" />
          <stop offset="1" stopColor="#092b50" />
        </linearGradient>
      </defs>
      <ellipse cx="55" cy="132" rx="29" ry="5" fill="#000" opacity=".2" />
      <g className="assistant-legs">
        <path d="M43 108v13m24-13v13" fill="none" stroke="#58a8dc" strokeWidth="12" strokeLinecap="round" />
        <path d="M34 125q9-5 17 1v5H34zm25 1q8-6 17-1v6H59z" fill="url(#cinevo-robot-shell)" stroke="#28628b" strokeWidth="2" />
      </g>
      <path d="M35 74q20-10 40 0l7 34q-27 16-54 0z" fill="url(#cinevo-robot-shell)" stroke="#28628b" strokeWidth="2.5" />
      <path d="M41 78q14 9 28 0" fill="none" stroke="#ffb84d" strokeWidth="5" strokeLinecap="round" />
      <path d="M46 92h18" stroke="#6fb8e4" strokeWidth="2" strokeLinecap="round" />
      <g className="assistant-arm assistant-arm-left">
        <path d="m34 82-9 19" fill="none" stroke="url(#cinevo-robot-shell)" strokeWidth="11" strokeLinecap="round" />
        <circle cx="24" cy="103" r="6" fill="#bcecff" stroke="#28628b" strokeWidth="2" />
      </g>
      <g className="assistant-arm assistant-arm-wave">
        <path d="m77 82 11-23" fill="none" stroke="url(#cinevo-robot-shell)" strokeWidth="11" strokeLinecap="round" />
        <circle cx="89" cy="57" r="7" fill="#bcecff" stroke="#28628b" strokeWidth="2" />
        <path d="M88 47v-5m7 8 4-4m-2 10h5" fill="none" stroke="#ffce59" strokeWidth="2" strokeLinecap="round" />
      </g>
      <path d="M34 27 31 12m45 15 3-15" stroke="#28628b" strokeWidth="3" strokeLinecap="round" />
      <circle cx="30" cy="10" r="4" fill="#78caff" stroke="#17466c" strokeWidth="2" />
      <circle cx="80" cy="10" r="4" fill="#78caff" stroke="#17466c" strokeWidth="2" />
      <rect x="17" y="21" width="76" height="57" rx="24" fill="url(#cinevo-robot-shell)" stroke="#17466c" strokeWidth="3" />
      <rect x="23" y="29" width="64" height="39" rx="18" fill="url(#cinevo-robot-screen)" stroke="#70c7f4" strokeWidth="2" />
      <path d="M17 42h-3v15h4m75-15h3v15h-4" fill="#ffb84d" stroke="#17466c" strokeWidth="2" />
      <text x="55" y="53" textAnchor="middle" fill="#f4fbff" fontSize="12" fontWeight="800" fontFamily="Arial, sans-serif">CINEVO</text>
      <path d="M37 60q18 8 36 0" fill="none" stroke="#55c6ed" strokeWidth="1.5" opacity=".8" />
    </svg>
  );
}

function AssistantAvatar() {
  return (
    <svg viewBox="0 0 40 40" role="img" aria-label="Avatar trợ lý Cinevo">
      <path d="M13 11 11 5m16 6 2-6" fill="none" stroke="#bcecff" strokeWidth="2" strokeLinecap="round" />
      <circle cx="11" cy="4" r="2" fill="#ffce59" />
      <circle cx="29" cy="4" r="2" fill="#ffce59" />
      <rect x="5" y="10" width="30" height="24" rx="9" fill="#bcecff" stroke="#17466c" strokeWidth="2" />
      <rect x="9" y="14" width="22" height="15" rx="6" fill="#092b50" stroke="#70c7f4" strokeWidth="1.5" />
      <circle cx="15" cy="21" r="2" fill="#f4fbff" />
      <circle cx="25" cy="21" r="2" fill="#f4fbff" />
      <path d="M15 25q5 3 10 0" fill="none" stroke="#55c6ed" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export default function ChatbotWidget() {
  const [position, setPosition] = useState(null);
  const [lineIndex, setLineIndex] = useState(0);
  const [greeting, setGreeting] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMinimized, setChatMinimized] = useState(false);
  const [assistantHidden, setAssistantHidden] = useState(false);
  const [assistantScale, setAssistantScale] = useState(1);
  const [chatPosition, setChatPosition] = useState(null);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState(() => [{
    id: 0,
    sender: "assistant",
    reply: navigator.language?.toLowerCase().startsWith("en")
      ? "Hello! I can recommend movies, find showtimes, explain bookings, or check Cinevo transactions in your account."
      : "Xin chào! Mình có thể gợi ý phim, tìm lịch chiếu, hướng dẫn đặt vé hoặc kiểm tra giao dịch Cinevo trong tài khoản của bạn.",
  }]);
  const characterRef = useRef(null);
  const chatRef = useRef(null);
  const messagesEndRef = useRef(null);
  const dragRef = useRef(null);
  const suppressClickRef = useRef(false);
  const greetingTimerRef = useRef(null);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setLineIndex((current) => (current + 1) % assistantLines.length);
    }, 5200);
    return () => {
      window.clearInterval(timer);
      window.clearTimeout(greetingTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!position) return undefined;
    const keepOnScreen = () => {
      const character = characterRef.current;
      if (!character) return;
      setPosition((current) => ({
        x: Math.max(0, Math.min(current.x, window.innerWidth - character.offsetWidth)),
        y: Math.max(0, Math.min(current.y, window.innerHeight - character.offsetHeight)),
      }));
    };
    window.addEventListener("resize", keepOnScreen);
    return () => window.removeEventListener("resize", keepOnScreen);
  }, [position]);

  useLayoutEffect(() => {
    if (!chatOpen) return undefined;
    const placeChat = () => {
      const character = characterRef.current;
      const chat = chatRef.current;
      if (!character || !chat) return;
      const anchor = character.getBoundingClientRect();
      const width = chat.offsetWidth;
      const height = chat.offsetHeight;
      const left = Math.max(8, Math.min(
        anchor.left + anchor.width / 2 - width / 2,
        window.innerWidth - width - 8,
      ));
      const above = anchor.top - height - 14;
      const top = above >= 8
        ? above
        : Math.max(8, Math.min(anchor.bottom + 14, window.innerHeight - height - 8));
      setChatPosition((current) => (
        current?.left === left && current?.top === top ? current : { left, top }
      ));
    };
    placeChat();
    window.addEventListener("resize", placeChat);
    return () => {
      window.removeEventListener("resize", placeChat);
    };
  }, [chatMinimized, chatOpen, position]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }, [messages, sending]);

  function startDrag(event) {
    const bounds = characterRef.current.getBoundingClientRect();
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: bounds.left,
      originY: bounds.top,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function moveCharacter(event) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < 5) return;
    drag.moved = true;

    const character = characterRef.current;
    setPosition({
      x: Math.max(0, Math.min(drag.originX + dx, window.innerWidth - character.offsetWidth)),
      y: Math.max(0, Math.min(drag.originY + dy, window.innerHeight - character.offsetHeight)),
    });
  }

  function endDrag(event) {
    if (dragRef.current?.pointerId !== event.pointerId) return;
    suppressClickRef.current = dragRef.current.moved;
    dragRef.current = null;
  }

  function activateAssistant() {
    if (suppressClickRef.current) {
      suppressClickRef.current = false;
      return;
    }
    setLineIndex((current) => (current + 1) % assistantLines.length);
    setChatOpen((current) => !current);
    setChatMinimized(false);
    setGreeting(true);
    window.clearTimeout(greetingTimerRef.current);
    greetingTimerRef.current = window.setTimeout(() => setGreeting(false), 1400);
  }

  function hideAssistant() {
    setAssistantHidden(true);
    setChatOpen(false);
  }

  async function sendMessage(event) {
    event.preventDefault();
    const message = draft.trim();
    if (!message || sending) return;
    setDraft("");
    setSending(true);
    setMessages((current) => [...current, {
      id: Date.now(),
      sender: "user",
      reply: message,
    }]);
    try {
      const response = await aiService.chat(message);
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        sender: "assistant",
        ...response,
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        id: Date.now() + 1,
        sender: "assistant",
        reply: error.message || "Không thể kết nối trợ lý Cinevo lúc này. Vui lòng thử lại.",
      }]);
    } finally {
      setSending(false);
    }
  }

  if (assistantHidden) {
    return (
      <button
        type="button"
        className="assistant-restore-button"
        onClick={() => setAssistantHidden(false)}
        aria-label="Hiện lại trợ lý Cinevo"
      >
        <AssistantCharacter />
      </button>
    );
  }

  return (
    <div
      ref={characterRef}
      className="chatbot assistant-character-dock"
      style={{
        "--assistant-character-width": `${96 * assistantScale}px`,
        "--assistant-character-height": `${142 * assistantScale}px`,
        "--assistant-dock-height": `${Math.max(170, 142 * assistantScale + 28)}px`,
        ...(position ? { left: position.x, top: position.y, right: "auto", bottom: "auto" } : {}),
      }}
    >
      <div className="assistant-thought-bubble" role="status" aria-live="polite">
        <span className="assistant-bubble-dots" aria-hidden="true"><i /><i /><i /></span>
        {assistantLines[lineIndex]}
      </div>
      <div className="assistant-mobile-actions" aria-label="Điều chỉnh trợ lý">
        <button
          type="button"
          onClick={() => setAssistantScale((current) => Math.max(0.7, Math.round((current - 0.15) * 100) / 100))}
          disabled={assistantScale <= 0.7}
          aria-label="Thu nhỏ trợ lý"
          title="Thu nhỏ trợ lý"
        >
          −
        </button>
        <button
          type="button"
          onClick={() => setAssistantScale((current) => Math.min(1.45, Math.round((current + 0.15) * 100) / 100))}
          disabled={assistantScale >= 1.45}
          aria-label="Phóng to trợ lý"
          title="Phóng to trợ lý"
        >
          +
        </button>
        <button type="button" onClick={hideAssistant} aria-label="Ẩn trợ lý Cinevo" title="Ẩn trợ lý">
          ×
        </button>
      </div>
      {chatOpen && (
        <section
          ref={chatRef}
          className={`assistant-chat-panel${chatMinimized ? " is-minimized" : ""}`}
          aria-label="Trợ lý ảo Cinevo"
          style={chatPosition ? { left: chatPosition.left, top: chatPosition.top } : undefined}
        >
          <header className="assistant-chat-header">
            <span className="assistant-chat-avatar"><AssistantAvatar /></span>
            <span>
              <strong>Trợ lý Cinevo</strong>
            </span>
            <button
              className="assistant-chat-minimize"
              type="button"
              onClick={() => setChatMinimized((current) => !current)}
              aria-label={chatMinimized ? "Mở rộng trò chuyện" : "Thu nhỏ trò chuyện"}
              title={chatMinimized ? "Mở rộng" : "Thu nhỏ"}
            >
              {chatMinimized ? "□" : "−"}
            </button>
            <button type="button" onClick={() => setChatOpen(false)} aria-label="Đóng trò chuyện">×</button>
          </header>
          {!chatMinimized && <>
            <div className="assistant-chat-messages" role="log" aria-live="polite" aria-label="Tin nhắn trò chuyện">
              {messages.map((message) => (
                <div key={message.id} className={`assistant-message is-${message.sender}`}>
                  {message.sender === "assistant" && (
                    <span className="assistant-message-avatar"><AssistantAvatar /></span>
                  )}
                  <p>{message.reply}</p>
                  {message.movies?.map((movie) => (
                    <article className="assistant-result-card" key={movie.id}>
                      <Link to={movie.url}><strong>{movie.title}</strong></Link>
                      <span>{movie.genre || "Phim"} · {movie.rating}/10 · {movie.age_rating}</span>
                      {movie.showtimes.length > 0 && (
                        <div className="assistant-result-schedule">
                          {movie.showtimes.map((showtime) => (
                            <Link to={`/user/showtimes/${movie.id}`} key={showtime.id}>
                              {showtime.cinema} · {new Date(showtime.start_time).toLocaleString(
                                message.language === "en" ? "en" : "vi",
                                { dateStyle: "short", timeStyle: "short" },
                              )}
                            </Link>
                          ))}
                        </div>
                      )}
                    </article>
                  ))}
                  {message.transactions?.map((transaction) => (
                    <article className="assistant-result-card" key={`${transaction.kind}-${transaction.reference}`}>
                      <strong>{transaction.reference}</strong>
                      <span>{transaction.description} · {transaction.amount_label || `${Number(transaction.amount).toLocaleString()}đ`}</span>
                      <span>{transaction.status_label || transaction.status}</span>
                    </article>
                  ))}
                  {message.action && <Link className="assistant-message-action" to={message.action.url}>{message.action.label}</Link>}
                </div>
              ))}
              {sending && (
                <div className="assistant-message is-assistant is-typing" role="status" aria-label="Trợ lý đang soạn tin">
                  <span className="assistant-message-avatar"><AssistantAvatar /></span>
                  <span className="assistant-typing-bubble" aria-hidden="true">
                    <i /><i /><i />
                  </span>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            {messages.length === 1 && (
              <div className="assistant-chat-suggestions">
                {(navigator.language?.toLowerCase().startsWith("en")
                  ? ["Recommend action movies", "How do I book tickets?", "Check my payment"]
                  : ["Gợi ý phim hành động", "Cách đặt vé?", "Kiểm tra giao dịch của tôi"]).map((prompt) => (
                  <button key={prompt} type="button" onClick={() => setDraft(prompt)}>{prompt}</button>
                ))}
              </div>
            )}
            <form className="assistant-chat-compose" onSubmit={sendMessage}>
              <input
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                placeholder="Nhập tin nhắn / Type a message"
                aria-label="Tin nhắn cho trợ lý Cinevo"
                maxLength={500}
                disabled={sending}
              />
              <button type="submit" disabled={sending || !draft.trim()} aria-label="Gửi tin nhắn">➤</button>
            </form>
          </>}
        </section>
      )}
      <div className="assistant-desktop-actions">
        <button
          type="button"
          onClick={hideAssistant}
          aria-label="Ẩn trợ lý Cinevo"
          title="Ẩn trợ lý"
        >
          ×
        </button>
      </div>
      <button
        type="button"
        className={`assistant-character-button${greeting ? " is-greeting" : ""}`}
        aria-expanded={chatOpen}
        aria-label="Trợ lý Cinevo vẫy tay. Bấm để nghe lời chào khác hoặc kéo để di chuyển."
        title="Bấm để trò chuyện, giữ và kéo để di chuyển"
        onPointerDown={startDrag}
        onPointerMove={moveCharacter}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onClick={activateAssistant}
      >
        <AssistantCharacter />
      </button>
    </div>
  );
}
