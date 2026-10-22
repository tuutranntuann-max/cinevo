import { useAppearance } from "../context/AppearanceContext";

export default function BrandLogo({ brand = "CINEVO", className = "" }) {
  const { appearance } = useAppearance();

  return (
    <>
      <img
        className={`brand-logo ${className}`.trim()}
        src={appearance.logo_media_url || "/cinevo-logo.png"}
        alt="CINEVO"
      />
      {brand === "CINEVOADM" && <span className="brand-admin-label">ADM</span>}
    </>
  );
}
