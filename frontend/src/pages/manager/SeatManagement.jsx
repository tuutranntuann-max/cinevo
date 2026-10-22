import { useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";

const SEAT_TYPES = [
  ["STANDARD", "Ghế thường"],
  ["VIP", "Ghế VIP"],
  ["DOUBLE", "Ghế đôi"],
];

export default function SeatManagement() {
  const [rooms, setRooms] = useState([]);
  const [roomId, setRoomId] = useState("");
  const [seats, setSeats] = useState([]);
  const [selected, setSelected] = useState([]);
  const [loading, setLoading] = useState(true);
  const [seatsLoading, setSeatsLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.get("/manager/rooms")
      .then((items) => {
        setRooms(items);
        setRoomId(String(items[0]?.id || ""));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!roomId) {
      setSeats([]);
      return;
    }
    let active = true;
    setSelected([]);
    setSeats([]);
    setError("");
    setSeatsLoading(true);
    api.get(`/manager/seats?room_id=${encodeURIComponent(roomId)}`)
      .then((items) => { if (active) setSeats(items); })
      .catch((e) => { if (active) setError(e.message); })
      .finally(() => { if (active) setSeatsLoading(false); });
    return () => { active = false; };
  }, [roomId]);

  const toggleSeat = (id) => {
    const seat = seats.find((item) => item.id === id);
    const partnerNumber = seat?.number % 2 ? seat.number + 1 : seat?.number - 1;
    const partner = seat?.type === "DOUBLE"
      ? seats.find((item) => item.row === seat.row && item.number === partnerNumber && item.type === "DOUBLE")
      : null;
    const seatIds = partner ? [seat.id, partner.id] : [id];
    setSelected((current) => {
      const isSelected = seatIds.every((seatId) => current.includes(seatId));
      return isSelected
        ? current.filter((seatId) => !seatIds.includes(seatId))
        : [...new Set([...current.filter((seatId) => !seatIds.includes(seatId)), ...seatIds])];
    });
    setError("");
    setMessage("");
  };

  async function updateType(type) {
    if (!selected.length) {
      setError("Hãy chọn ghế cần cập nhật trước.");
      return;
    }
    let seatIds = selected;
    if (type === "DOUBLE" && selected.length === 1) {
      const seat = seats.find((item) => item.id === selected[0]);
      const partnerNumber = seat.number % 2 ? seat.number + 1 : seat.number - 1;
      const partner = seats.find((item) => item.row === seat.row && item.number === partnerNumber);
      if (!partner) {
        setError("Không tìm thấy ghế liền kề để ghép cặp.");
        return;
      }
      seatIds = [seat.id, partner.id];
      setSelected(seatIds);
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const result = await api.patch("/manager/seats/type", { seat_ids: seatIds, type });
      const updated = new Map(result.seats.map((seat) => [seat.id, seat]));
      setSeats((current) => current.map((seat) => updated.get(seat.id) || seat));
      setSelected(type === "DOUBLE" ? seatIds : []);
      setMessage(`Đã cập nhật ${result.seats.length} ghế.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading />;

  const selectedSeats = new Set(selected);
  const rows = seats.reduce((groups, seat) => {
    (groups[seat.row] ||= []).push(seat);
    return groups;
  }, {});

  return (
    <section className="seat-management">
      <h1 className="page-title">Quản lý ghế</h1>
      <p className="muted">Chọn ghế để đổi loại. Khi tạo ghế đôi, chỉ cần chọn một ghế trong cặp; hệ thống tự ghép với ghế liền kề theo cặp 1–2, 3–4...</p>
      <ErrorBox message={error} />
      {message && <div className="success" role="status">{message}</div>}
      <label className="seat-room-select">Phòng chiếu
        <select value={roomId} onChange={(event) => setRoomId(event.target.value)}>
          {rooms.map((room) => (
            <option value={room.id} key={room.id}>{room.cinema} · {room.name}</option>
          ))}
        </select>
      </label>
      {!rooms.length ? <div className="state-box">Chưa có phòng chiếu.</div> : (
        <>
          <div className="seat-type-actions">
            <span>{seatsLoading ? "Đang tải ghế..." : `${selected.length} ghế đã chọn`}</span>
            {SEAT_TYPES.map(([type, label]) => (
              <button key={type} className="btn btn-ghost btn-sm" type="button"
                disabled={busy || !selected.length} onClick={() => updateType(type)}>
                {busy ? "Đang lưu..." : label}
              </button>
            ))}
          </div>
          <div className="seat-config-grid">
            {Object.keys(rows).sort().map((row) => (
              <div className="seat-config-row" key={row}>
                <strong>{row}</strong>
                {[...rows[row]].sort((a, b) => a.number - b.number).map((seat) => (
                  <button
                    key={seat.id}
                    type="button"
                    className={[
                      "seat-config-cell",
                      seat.type.toLowerCase(),
                      selectedSeats.has(seat.id) && "selected",
                    ].filter(Boolean).join(" ")}
                    aria-pressed={selectedSeats.has(seat.id)}
                    onClick={() => toggleSeat(seat.id)}
                    disabled={busy}
                    title={`${seat.label} · ${SEAT_TYPES.find(([type]) => type === seat.type)?.[1] || seat.type}`}
                  >
                    {seat.number}
                  </button>
                ))}
                <strong>{row}</strong>
              </div>
            ))}
          </div>
          <div className="legend">
            {SEAT_TYPES.map(([type, label]) => (
              <span key={type}><i className={`seat-config-cell ${type.toLowerCase()}`} />{label}</span>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
