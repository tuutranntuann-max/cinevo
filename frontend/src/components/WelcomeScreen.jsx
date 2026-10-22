import BrandLogo from "./BrandLogo";

export default function WelcomeScreen({ appearance, onEnter }) {
  const mediaUrl = appearance.welcome_media_url;
  const mediaType = appearance.welcome_media_type;
  const hasVideo = Boolean(mediaUrl && mediaType === "video");

  return (
    <main className="welcome-screen">
      <div className="welcome-screen-backdrop" aria-hidden="true">
        {mediaUrl && (hasVideo
          ? <video src={mediaUrl} autoPlay loop playsInline preload="auto" />
          : <img src={mediaUrl} alt="" />)}
      </div>
      <section className="welcome-screen-card" aria-labelledby="welcome-screen-title">
        <div className="welcome-screen-brand">
          <BrandLogo />
          <span>ĐẶT VÉ · XEM PHIM · CINEVO</span>
        </div>
        <p className="welcome-screen-eyebrow">CHÀO MỪNG BẠN ĐẾN VỚI CINEVO</p>
        <h1 id="welcome-screen-title">{appearance.welcome_title}</h1>
        <p className="welcome-screen-description">{appearance.welcome_description}</p>
        <button className="welcome-screen-enter" type="button" onClick={onEnter}>
          {appearance.welcome_button_text}
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M5 12h14m-6-6 6 6-6 6" />
          </svg>
        </button>
        <div className="welcome-screen-perks" aria-label="Trải nghiệm Cinevo">
          <span><strong>01</strong> Chọn phim yêu thích</span>
          <span><strong>02</strong> Chọn ghế dễ dàng</span>
          <span><strong>03</strong> Sẵn sàng thưởng thức</span>
        </div>
      </section>
    </main>
  );
}
