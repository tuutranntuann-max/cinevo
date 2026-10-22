import { createContext, useContext, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { api } from "../services/api";

const DEFAULT_APPEARANCE = {
  footer_tax_code: import.meta.env.VITE_PUBLIC_PREVIEW === "true" ? "" : "0335823036",
  footer_email: import.meta.env.VITE_PUBLIC_PREVIEW === "true" ? "" : "tuutranntuann@gmail.com",
  accent_color: "#e11d2e",
  page_color: "#080808",
  surface_color: "#141414",
  overlay_opacity: 0.45,
  welcome_enabled: true,
  welcome_title: "Chào mừng đến với CINEVO",
  welcome_description: "Khám phá phim đang chiếu, chọn chỗ ngồi yêu thích và đặt vé nhanh chóng.",
  welcome_button_text: "Vào xem phim",
  title_size: 78,
  title_font: "bebas",
  title_frame: "none",
  title_preset: "cinema",
  title_motion: "bob",
  footer_company_name: "CINEVO",
  footer_license: "",
  footer_registered: "",
  footer_address: "",
  footer_version: "v8.1",
  footer_links: [
    { label: "Về chúng tôi", url: "" },
    { label: "Chính sách bảo mật", url: "" },
    { label: "Hỗ trợ", url: "" },
    { label: "Liên hệ", url: "" },
  ],
  footer_partners: [
    "beta cinemas", "Mega GS", "CINESTAR", "DCINE", "CINEMAX", "STARLIGHT", "RIO",
    "DDC", "TOUCH CINEMA", "GALAXY", "AEON BETA", "AZ", "Payoo", "momo", "ZaloPay",
  ].map((name) => ({ name, logo_url: "", url: "" })),
  footer_partners_enabled: true,
  footer_commerce_notice: "",
  footer_show_upcoming: true,
};

const TITLE_FONTS = {
  bebas: '"Bebas Neue", sans-serif',
  sans: '"Montserrat", "Be Vietnam Pro", sans-serif',
  serif: '"Playfair Display", Georgia, serif',
  script: '"Great Vibes", "Brush Script MT", cursive',
};
const TITLE_FRAMES = new Set(["none", "underline", "rounded", "geometric", "speech"]);
const TITLE_PRESETS = new Set(["cinema", "glow", "shadow", "stroke", "three-d"]);
const TITLE_MOTIONS = new Set([
  "none", "bob", "sway", "float", "breathe", "tilt", "drift-left", "drift-right",
  "nod", "wave", "swing", "lift", "orbit", "sway-wide", "bounce-soft",
  "rise-fall", "shimmer", "rotate-soft", "dance", "hover",
]);

const AppearanceContext = createContext({
  appearance: DEFAULT_APPEARANCE,
  appearanceLoaded: false,
  refreshAppearance: async () => {},
});

export const useAppearance = () => useContext(AppearanceContext);

export function AppearanceProvider({ children }) {
  const [appearance, setAppearance] = useState(DEFAULT_APPEARANCE);
  const [appearanceLoaded, setAppearanceLoaded] = useState(false);

  async function refreshAppearance() {
    try {
      const next = await api.get("/movies/appearance");
      setAppearance({ ...DEFAULT_APPEARANCE, ...next });
      return next;
    } finally {
      setAppearanceLoaded(true);
    }
  }

  useEffect(() => {
    refreshAppearance().catch((error) => {
      console.error("Không thể tải cấu hình giao diện CINEVO.", error);
    });
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--red", appearance.accent_color);
    root.style.setProperty("--bg", appearance.page_color);
    root.style.setProperty("--panel", appearance.surface_color);
    root.style.setProperty("--panel-2", `color-mix(in srgb, ${appearance.surface_color} 78%, white)`);
    root.style.setProperty("--movie-title-font", TITLE_FONTS[appearance.title_font] || TITLE_FONTS.bebas);
    const titleSize = Math.min(100, Math.max(60, Number(appearance.title_size) || DEFAULT_APPEARANCE.title_size));
    root.style.setProperty("--movie-title-size", `${(titleSize * 4.4 / 100).toFixed(2)}rem`);
    root.style.setProperty("--movie-title-preview-size", `${(1.4 + ((titleSize - 60) / 40) * 0.8).toFixed(2)}rem`);
    root.dataset.titleFrame = TITLE_FRAMES.has(appearance.title_frame) ? appearance.title_frame : "none";
    root.dataset.titlePreset = TITLE_PRESETS.has(appearance.title_preset) ? appearance.title_preset : "cinema";
    root.dataset.titleMotion = TITLE_MOTIONS.has(appearance.title_motion) ? appearance.title_motion : "bob";
  }, [appearance]);

  return (
    <AppearanceContext.Provider value={{ appearance, appearanceLoaded, refreshAppearance }}>
      {children}
    </AppearanceContext.Provider>
  );
}

export function AppearanceBackdrop() {
  const { appearance } = useAppearance();
  const mediaUrl = appearance.site_media_url;

  if (!mediaUrl) return null;

  return createPortal(
    <div
      className="appearance-backdrop"
      style={{ "--appearance-overlay": appearance.overlay_opacity ?? 0.45 }}
      aria-hidden="true"
    >
      {appearance.site_media_type === "video" ? (
        <video src={mediaUrl} autoPlay muted loop playsInline preload="metadata" />
      ) : (
        <img src={mediaUrl} alt="" />
      )}
    </div>,
    document.body
  );
}
