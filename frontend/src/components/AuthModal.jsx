// Popup đăng nhập/đăng ký. Chỉ hiện khi gọi requireLogin() mà chưa đăng nhập (sau bước chọn ghế).
import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import AuthPanel from "./AuthPanel";
import { useUserPreferences } from "../context/UserPreferencesContext";

export default function AuthModal() {
  const { t } = useUserPreferences();
  const { modal, closeModal } = useAuth();

  useEffect(() => {
    if (!modal.open) return;
    const onKey = (e) => e.key === "Escape" && closeModal();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modal.open, closeModal]);

  if (!modal.open) return null;
  return (
    <div className="modal-backdrop" onClick={closeModal}>
      <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={closeModal} aria-label={t("Đóng")}>×</button>
        <AuthPanel
          initialView="choice"
          onSuccess={(user) => { const cb = modal.onSuccess; closeModal(); cb?.(user); }}
        />
      </div>
    </div>
  );
}
