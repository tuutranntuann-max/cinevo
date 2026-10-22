// Quản lý đăng nhập + popup đăng nhập/đăng ký.
// requireLogin(onSuccess): nếu đã đăng nhập thì chạy ngay, chưa thì mở popup và chạy sau khi xong.
// Trạng thái đơn hàng nằm ở BookingContext nên KHÔNG bị mất khi đăng nhập/đăng ký.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authService } from "../services/authService";
import { TOKEN_KEY } from "../services/api";

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!localStorage.getItem(TOKEN_KEY));
  const [modal, setModal] = useState({ open: false, onSuccess: null });

  // Khôi phục phiên đăng nhập khi tải lại trang.
  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) return;
    authService.me()
      .then((d) => setUser(d.user))
      .catch(() => localStorage.removeItem(TOKEN_KEY))
      .finally(() => setLoading(false));
  }, []);

  const startSession = useCallback((data) => {
    localStorage.setItem(TOKEN_KEY, data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const login = useCallback(async (email, password) => {
    return startSession(await authService.login(email, password));
  }, [startSession]);
  const verifyOtp = useCallback(async (email, code) => startSession(await authService.verifyOtp(email, code)), [startSession]);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  }, []);

  const requireLogin = useCallback((onSuccess) => {
    if (user) return onSuccess?.(user);
    setModal({ open: true, onSuccess });
  }, [user]);

  const closeModal = useCallback(() => setModal({ open: false, onSuccess: null }), []);

  const value = useMemo(
    () => ({
      user, setUser, loading, startSession, login, verifyOtp, logout, requireLogin, modal, closeModal,
    }),
    [user, loading, startSession, login, verifyOtp, logout, requireLogin, modal, closeModal]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
