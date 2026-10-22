export default function Loading({ text = "Đang tải..." }) {
  return <div className="state-box" role="status">{text}</div>;
}
