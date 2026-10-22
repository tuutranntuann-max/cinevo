import { Link } from "react-router-dom";

export default function BackHomeLink({ className = "", label = "Về trang chủ" }) {
  return (
    <Link
      to="/user"
      className={`btn btn-ghost back-home-link ${className}`.trim()}
      aria-label={label}
      title={label}
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M19 12H5m7 7-7-7 7-7" />
      </svg>
    </Link>
  );
}
