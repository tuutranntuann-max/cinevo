import { useEffect, useState } from "react";
import ErrorBox from "../../components/ErrorBox";
import Loading from "../../components/Loading";
import { api } from "../../services/api";
import { useAppearance } from "../../context/AppearanceContext";

function PartnerLogoPreview({ name, logoUrl }) {
  const [failedUrls, setFailedUrls] = useState([]);
  const failed = failedUrls.includes(logoUrl);

  if (!logoUrl || failed) {
    return (
      <div className="appearance-partner-preview-fallback" role="status">
        <span>{name?.trim()?.charAt(0)?.toLocaleUpperCase("vi-VN") || "?"}</span>
        <small>{failed
          ? "Không tải được ảnh. Hãy dùng URL HTTPS trực tiếp tới tệp logo, không phải URL website hoặc trang chính sách."
          : "Chưa có logo trực tiếp. Nhập URL HTTPS tới tệp ảnh để xem trước."}</small>
      </div>
    );
  }

  return (
    <img className="appearance-partner-preview" src={logoUrl} alt=""
      onError={() => setFailedUrls((current) => [...current, logoUrl])} />
  );
}

export default function SystemSettings() {
  const { refreshAppearance } = useAppearance();
  const [settings, setSettings] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState("");
  const [preview, setPreview] = useState({});
  const [previewType, setPreviewType] = useState({});

  useEffect(() => {
    api.get("/admin/appearance").then(setSettings).catch((e) => setError(e.message));
  }, []);

  useEffect(() => () => {
    Object.values(preview).forEach((url) => URL.revokeObjectURL(url));
  }, [preview]);

  function update(field, value) {
    setSettings((current) => ({ ...current, [field]: value }));
  }

  function updateFooterEntry(field, index, key, value) {
    setSettings((current) => ({
      ...current,
      [field]: current[field].map((entry, entryIndex) =>
        entryIndex === index ? { ...entry, [key]: value } : entry
      ),
    }));
  }

  function addFooterEntry(field, entry) {
    setSettings((current) => ({ ...current, [field]: [...current[field], entry] }));
  }

  function removeFooterEntry(field, index) {
    setSettings((current) => ({
      ...current,
      [field]: current[field].filter((_, entryIndex) => entryIndex !== index),
    }));
  }

  async function save() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const saved = await api.patch("/admin/appearance", {
        accent_color: settings.accent_color,
        page_color: settings.page_color,
        surface_color: settings.surface_color,
        overlay_opacity: Number(settings.overlay_opacity),
        welcome_enabled: settings.welcome_enabled,
        welcome_title: settings.welcome_title,
        welcome_description: settings.welcome_description,
        welcome_button_text: settings.welcome_button_text,
        title_size: Number(settings.title_size),
        title_font: settings.title_font,
        title_frame: settings.title_frame,
        title_preset: settings.title_preset,
        title_motion: settings.title_motion,
        footer_company_name: settings.footer_company_name,
        footer_tax_code: settings.footer_tax_code,
        footer_email: settings.footer_email,
        footer_license: settings.footer_license,
        footer_registered: settings.footer_registered,
        footer_address: settings.footer_address,
        footer_version: settings.footer_version,
        footer_commerce_notice: settings.footer_commerce_notice,
        footer_links: settings.footer_links.filter((item) => item.label.trim()),
        footer_partners: settings.footer_partners.filter((partner) => partner.name.trim()),
        footer_partners_enabled: settings.footer_partners_enabled,
        footer_show_upcoming: settings.footer_show_upcoming,
      });
      setSettings((current) => ({ ...current, ...saved }));
      await refreshAppearance();
      setMessage("Đã lưu và áp dụng giao diện mới.");
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function uploadMedia(scope, file) {
    if (!file) return;
    const isLogo = scope === "logo";
    const allowedTypes = isLogo
      ? ["image/jpeg", "image/png", "image/webp"]
      : ["image/jpeg", "image/png", "image/webp", "video/mp4", "video/webm"];
    if (!allowedTypes.includes(file.type)) {
      setError(isLogo
        ? "Logo chỉ hỗ trợ ảnh PNG, JPG hoặc WEBP."
        : "Chỉ hỗ trợ ảnh JPG, PNG, WEBP hoặc video MP4, WebM.");
      return;
    }
    const maxSize = isLogo ? 10 * 1024 * 1024 : 10 * 1024 * 1024 * 1024;
    if (file.size > maxSize) {
      setError(isLogo ? "Logo không được vượt quá 10 MB." : "Tệp nền không được vượt quá 10 GB.");
      return;
    }
    const localUrl = URL.createObjectURL(file);
    setPreviewType((current) => ({ ...current, [scope]: file.type.startsWith("video/") ? "video" : "image" }));
    setPreview((current) => {
      if (current[scope]) URL.revokeObjectURL(current[scope]);
      return { ...current, [scope]: localUrl };
    });
    const formData = new FormData();
    formData.append("media", file);
    setUploading(scope);
    setError("");
    setMessage("");
    try {
      const saved = await api.upload(`/admin/appearance/${scope}/media`, formData);
      setSettings((current) => ({ ...current, ...saved }));
      await refreshAppearance();
      const label = scope === "logo"
        ? "logo"
        : scope === "banner"
          ? "banner phim"
          : scope === "welcome"
            ? "nền màn chào"
            : "nền toàn website";
      setMessage(`Đã cập nhật ${label}.`);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading("");
      setPreview((current) => {
        if (current[scope]) URL.revokeObjectURL(current[scope]);
        const next = { ...current };
        delete next[scope];
        return next;
      });
      setPreviewType((current) => {
        const next = { ...current };
        delete next[scope];
        return next;
      });
    }
  }

  async function removeMedia(scope) {
    setError("");
    setMessage("");
    try {
      const saved = await api.delete(`/admin/appearance/${scope}/media`);
      setSettings((current) => ({ ...current, ...saved }));
      await refreshAppearance();
      setMessage(scope === "logo" ? "Đã xóa logo tùy chỉnh, đã trở về logo mặc định." : "Đã xóa ảnh/video nền.");
    } catch (e) {
      setError(e.message);
    }
  }

  if (!settings) return error ? <ErrorBox message={error} /> : <Loading />;

  const mediaCard = (scope, title, description, imageOnly = false) => {
    const mediaUrl = preview[scope] || settings[`${scope}_media_url`];
    const isVideo = preview[scope]
      ? previewType[scope] === "video"
      : settings[`${scope}_media_type`] === "video";
    return (
      <section className="appearance-media-card" key={scope}>
        <div>
          <h3>{title}</h3>
          <p className="muted small">{description}</p>
        </div>
        <div className={`appearance-preview${imageOnly ? " appearance-logo-preview" : ""}`}>
          {mediaUrl && isVideo
            ? <video src={mediaUrl} autoPlay muted loop playsInline />
            : mediaUrl
              ? <img src={mediaUrl} alt={`Xem trước ${title}`} />
              : <span>Chưa có ảnh/video nền</span>}
        </div>
        <div className="appearance-actions">
          <label className="btn btn-ghost btn-sm">
            {uploading === scope ? "Đang tải lên..." : imageOnly ? "Chọn logo" : "Chọn ảnh/video"}
            <input
              type="file"
              accept={imageOnly
                ? "image/jpeg,image/png,image/webp"
                : "image/jpeg,image/png,image/webp,video/mp4,video/webm"}
              disabled={uploading !== ""}
              onChange={(event) => {
                uploadMedia(scope, event.target.files?.[0]);
                event.target.value = "";
              }}
              hidden
            />
          </label>
          {settings[`${scope}_media_url`] && (
            <button className="btn btn-ghost btn-sm" type="button" onClick={() => removeMedia(scope)}>
              {imageOnly ? "Trở về logo mặc định" : "Xóa media"}
            </button>
          )}
        </div>
      </section>
    );
  };
  const titleFields = [
    {
      field: "title_font",
      label: "Kiểu chữ",
      options: [
        ["bebas", "Bebas Neue - điện ảnh"],
        ["sans", "Sans-serif - hiện đại"],
        ["serif", "Serif - sang trọng"],
        ["script", "Script - thư pháp"],
      ],
    },
    {
      field: "title_frame",
      label: "Khung chữ",
      options: [
        ["none", "Không khung"],
        ["underline", "Gạch nhấn"],
        ["rounded", "Khung bo góc"],
        ["geometric", "Khung hình học"],
        ["speech", "Bong bóng thoại"],
      ],
    },
    {
      field: "title_preset",
      label: "Mẫu chữ nghệ thuật",
      options: [
        ["cinema", "Điện ảnh chuyển sắc"],
        ["glow", "Phát sáng"],
        ["shadow", "Bóng đổ"],
        ["stroke", "Viền chữ"],
        ["three-d", "Nổi 3D"],
      ],
    },
    {
      field: "title_motion",
      label: "Chuyển động nhẹ",
      options: [
        ["none", "Không chuyển động"],
        ["bob", "Bập bồng nhẹ"],
        ["sway", "Đung đưa"],
        ["float", "Trôi nhẹ"],
        ["breathe", "Thở nhẹ"],
        ["tilt", "Nghiêng nhịp nhàng"],
        ["drift-left", "Lướt sang trái"],
        ["drift-right", "Lướt sang phải"],
        ["nod", "Gật nhẹ"],
        ["wave", "Lượn sóng"],
        ["swing", "Lắc mềm"],
        ["lift", "Nhấc nhẹ"],
        ["orbit", "Lắc vòng cung"],
        ["sway-wide", "Đung đưa rộng"],
        ["bounce-soft", "Nảy thật nhẹ"],
        ["rise-fall", "Lên xuống chậm"],
        ["shimmer", "Ánh sáng lướt"],
        ["rotate-soft", "Xoay rất nhẹ"],
        ["dance", "Nhịp phim"],
        ["hover", "Lơ lửng"],
      ],
    },
  ];

  return (
    <div className="admin-appearance">
      <h1 className="page-title">Tùy chỉnh giao diện</h1>
      <p className="muted">Cấu hình được lưu trên máy chủ và áp dụng cho website khách ngay sau khi lưu.</p>
      {error && <ErrorBox message={error} />}
      {message && <p className="appearance-success" role="status">{message}</p>}

      <section className="appearance-settings-card welcome-editor">
        <div className="welcome-editor-heading">
          <div>
            <h2>Màn chào trước khi vào website</h2>
            <p className="muted small">Khách sẽ thấy màn này một lần mỗi phiên trước khi vào các trang khách hàng.</p>
          </div>
          <a className="btn btn-ghost btn-sm" href="/user?welcomePreview=1" target="_blank" rel="noreferrer">
            Xem trước
          </a>
        </div>
        <label className="appearance-toggle">
          <input
            type="checkbox"
            checked={settings.welcome_enabled}
            onChange={(event) => update("welcome_enabled", event.target.checked)}
          />
          <span>Bật màn chào cho khách hàng</span>
        </label>
        <label className="welcome-editor-field">
          <span>Tiêu đề</span>
          <input
            value={settings.welcome_title}
            maxLength={120}
            onChange={(event) => update("welcome_title", event.target.value)}
          />
        </label>
        <label className="welcome-editor-field">
          <span>Mô tả</span>
          <textarea
            value={settings.welcome_description}
            maxLength={500}
            rows={3}
            onChange={(event) => update("welcome_description", event.target.value)}
          />
        </label>
        <label className="welcome-editor-field">
          <span>Chữ trên nút vào website</span>
          <input
            value={settings.welcome_button_text}
            maxLength={60}
            onChange={(event) => update("welcome_button_text", event.target.value)}
          />
        </label>
        <button className="btn btn-red" type="button" onClick={save} disabled={saving}>
          {saving ? "Đang lưu..." : "Lưu màn chào"}
        </button>
      </section>

      <section className="appearance-settings-card">
        <h2>Màu sắc giao diện</h2>
        <div className="appearance-colors">
          {[
            ["page_color", "Màu nền trang"],
            ["surface_color", "Màu thẻ / khung"],
            ["accent_color", "Màu nhấn"],
          ].map(([field, label]) => (
            <label className="appearance-color-field" key={field}>
              <span>{label}</span>
              <input type="color" value={settings[field]} onChange={(event) => update(field, event.target.value)} />
              <code>{settings[field]}</code>
            </label>
          ))}
        </div>
        <label className="appearance-opacity">
          <span>Độ tối lớp phủ trên nền toàn website: {Math.round(settings.overlay_opacity * 100)}%</span>
          <input
            type="range"
            min="0"
            max="0.9"
            step="0.05"
            value={settings.overlay_opacity}
            onChange={(event) => update("overlay_opacity", Number(event.target.value))}
          />
        </label>
        <button className="btn btn-red" type="button" onClick={save} disabled={saving}>
          {saving ? "Đang lưu..." : "Lưu tùy chỉnh"}
        </button>
      </section>

      <section className="appearance-settings-card appearance-typography">
        <h2>Kiểu chữ tên phim</h2>
        <p className="muted small">Áp dụng cho tên phim ở banner, thẻ phim và trang chi tiết.</p>
        <label className="appearance-title-size">
          <span>Cỡ tên phim trên banner: {settings.title_size ?? 78}%</span>
          <input
            type="range"
            min="60"
            max="100"
            step="5"
            value={settings.title_size ?? 78}
            onChange={(event) => update("title_size", Number(event.target.value))}
          />
        </label>
        <div className="appearance-title-options">
          {titleFields.map(({ field, label, options }) => (
            <label className="appearance-title-field" key={field}>
              <span>{label}</span>
              <select value={settings[field] || options[0][0]} onChange={(event) => update(field, event.target.value)}>
                {options.map(([value, text]) => <option value={value} key={value}>{text}</option>)}
              </select>
            </label>
          ))}
        </div>
        <div
          className="appearance-title-preview"
          data-title-frame={settings.title_frame || "none"}
          data-title-preset={settings.title_preset || "cinema"}
          data-title-motion={settings.title_motion || "bob"}
          style={{ "--movie-title-font": ({
            bebas: '"Bebas Neue", sans-serif',
            sans: '"Montserrat", "Be Vietnam Pro", sans-serif',
            serif: '"Playfair Display", Georgia, serif',
            script: '"Great Vibes", "Brush Script MT", cursive',
          })[settings.title_font] || '"Bebas Neue", sans-serif' }}
        >
          <span>Xem trước tiêu đề phim</span>
          <strong>CINEVO - Đêm điện ảnh</strong>
          <small>Hiệu ứng được làm nhẹ để không gây rối mắt.</small>
        </div>
        <p className="hint">Muốn thay tên chữ bằng logo ảnh riêng cho từng phim? Tải logo tại <a href="/admin/movies">Quản lý phim</a>; có thể chuyển lại tên chữ bất cứ lúc nào.</p>
        <button className="btn btn-red" type="button" onClick={save} disabled={saving}>
          {saving ? "Đang lưu..." : "Lưu kiểu chữ"}
        </button>
      </section>

      <section className="appearance-settings-card">
        <h2>Thông tin chân trang</h2>
        <p className="muted small">Nội dung công ty, liên kết và phim sắp chiếu hiển thị cuối trang khách hàng.</p>
        <div className="appearance-footer-fields">
          {[
            ["footer_company_name", "Tên công ty / thương hiệu"],
            ["footer_tax_code", "Số ĐKKD / mã số thuế"],
            ["footer_email", "Email liên hệ"],
            ["footer_license", "Thông tin cấp phép"],
            ["footer_registered", "Ngày đăng ký lần đầu"],
            ["footer_address", "Địa chỉ"],
            ["footer_version", "Phiên bản hiển thị"],
            ["footer_commerce_notice", "Nhãn thông báo thương mại (chỉ khi đã đăng ký)"],
          ].map(([field, label]) => (
            <label className="appearance-title-field" key={field}>
              <span>{label}</span>
              <input type={field === "footer_email" ? "email" : "text"}
                value={settings[field] || ""} maxLength={field === "footer_address" ? 300 : 240}
                onChange={(event) => update(field, event.target.value)} />
            </label>
          ))}
        </div>
        <p className="hint">Logo chân trang dùng biểu tượng Cinevo tròn đỏ theo mẫu. Thông tin cấp phép và địa chỉ chỉ hiển thị khi được điền.</p>
        <label className="appearance-footer-toggle">
          <input type="checkbox" checked={settings.footer_show_upcoming}
            onChange={(event) => update("footer_show_upcoming", event.target.checked)} />
          <span>Hiển thị danh sách phim sắp chiếu (tự lấy từ kho phim)</span>
        </label>
        <label className="appearance-footer-toggle">
          <input type="checkbox" checked={settings.footer_partners_enabled}
            onChange={(event) => update("footer_partners_enabled", event.target.checked)} />
          <span>Hiển thị khu vực đối tác</span>
        </label>

        <div className="appearance-footer-editor">
          <div className="appearance-footer-editor-heading">
            <h3>Liên kết chân trang</h3>
            <button className="btn btn-ghost btn-sm" type="button"
              onClick={() => addFooterEntry("footer_links", { label: "", url: "" })}>
              Thêm liên kết
            </button>
          </div>
          {settings.footer_links.map((item, index) => (
            <div className="appearance-footer-entry" key={`footer-link-${index}`}>
              <label><span>Tên liên kết</span>
                <input value={item.label} maxLength={60}
                  onChange={(event) => updateFooterEntry("footer_links", index, "label", event.target.value)} />
              </label>
              <label><span>Đường dẫn</span>
                <input value={item.url} maxLength={2048} placeholder="https://... hoặc /duong-dan"
                  onChange={(event) => updateFooterEntry("footer_links", index, "url", event.target.value)} />
              </label>
              <button className="btn btn-ghost btn-sm" type="button"
                onClick={() => removeFooterEntry("footer_links", index)}>Xóa</button>
            </div>
          ))}
        </div>

        <div className="appearance-footer-editor">
          <div className="appearance-footer-editor-heading">
            <div>
              <h3>Đối tác</h3>
              <p className="muted small">Logo rõ nét cần URL HTTPS trực tiếp tới tệp ảnh PNG, JPG, WEBP hoặc SVG. URL trang web/chính sách không phải URL logo.</p>
            </div>
            <button className="btn btn-ghost btn-sm" type="button"
              onClick={() => addFooterEntry("footer_partners", { name: "", logo_url: "", url: "" })}>
              Thêm đối tác
            </button>
          </div>
          {settings.footer_partners.map((partner, index) => (
            <div className="appearance-footer-partner" key={`footer-partner-${index}`}>
              <div className="appearance-footer-entry">
                <label><span>Tên đối tác</span>
                  <input value={partner.name} maxLength={100}
                    onChange={(event) => updateFooterEntry("footer_partners", index, "name", event.target.value)} />
                </label>
                <label><span>URL logo</span>
                  <input type="url" value={partner.logo_url} maxLength={2048}
                    placeholder="https://.../logo.png (liên kết ảnh trực tiếp)"
                    onChange={(event) => updateFooterEntry("footer_partners", index, "logo_url", event.target.value)} />
                </label>
                <label><span>Website đối tác</span>
                  <input value={partner.url} maxLength={2048} placeholder="https://..."
                    onChange={(event) => updateFooterEntry("footer_partners", index, "url", event.target.value)} />
                </label>
                <button className="btn btn-ghost btn-sm" type="button"
                  onClick={() => removeFooterEntry("footer_partners", index)}>Xóa</button>
              </div>
              <PartnerLogoPreview name={partner.name} logoUrl={partner.logo_url} />
            </div>
          ))}
          {!settings.footer_partners.length && <p className="muted small">Chưa có đối tác. Thêm mục để hiển thị tại chân trang.</p>}
        </div>
        <button className="btn btn-red" type="button" onClick={save} disabled={saving}>
          {saving ? "Đang lưu..." : "Lưu thông tin chân trang"}
        </button>
      </section>

      <div className="appearance-media-grid">
        {mediaCard("logo", "Logo website", "Thay logo ở thanh điều hướng, khu vực admin/manager và trang đăng nhập admin. Chỉ nhận PNG, JPG hoặc WEBP, tối đa 10 MB.", true)}
        {mediaCard("banner", "Banner phim", "Ảnh hoặc video này thay cho trailer phim ở banner trang chủ.")}
        {mediaCard("welcome", "Video / ảnh giới thiệu màn chào", "Tải video intro hoặc ảnh nền chỉ dành cho màn chào này. Media này độc lập, không thay đổi nền các trang khác; hỗ trợ MP4, WebM, JPG, PNG, WEBP.")}
        {mediaCard("site", "Nền toàn website", "Ảnh/video phủ nền các trang; lớp tối giúp nội dung dễ đọc.")}
      </div>
      <p className="hint">Hỗ trợ JPG, PNG, WEBP, MP4, WebM. Video tối đa 10 GB.</p>
    </div>
  );
}
