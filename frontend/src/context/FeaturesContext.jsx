// Lấy danh sách tính năng đang bật từ backend (GET /api/config). Mặc định mọi tính năng TẮT
// cho tới khi backend xác nhận, nên giao diện AI không bị nháy lên rồi biến mất.
import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../services/api";

const FeaturesContext = createContext({ features: { ai: false }, loaded: false });
export const useFeatures = () => useContext(FeaturesContext);

export function FeaturesProvider({ children }) {
  const [state, setState] = useState({ features: { ai: false }, loaded: false });

  useEffect(() => {
    api.get("/config")
      .then((d) => setState({ features: { ai: !!d.features?.ai }, loaded: true }))
      .catch(() => setState((s) => ({ ...s, loaded: true })));
  }, []);

  return <FeaturesContext.Provider value={state}>{children}</FeaturesContext.Provider>;
}
