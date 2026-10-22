import { useEffect, useState } from "react";
import { formatVND } from "../utils/format";
import { useUserPreferences } from "../context/UserPreferencesContext";

export default function BankTransferInstructions({ settings, amount, reference, showQr = true }) {
  const { t } = useUserPreferences();
  const generatedQrUrl = settings?.bank_bin && settings?.account_number
    ? `https://img.vietqr.io/image/${encodeURIComponent(settings.bank_bin)}-${encodeURIComponent(settings.account_number)}-compact2.png?amount=${encodeURIComponent(amount)}&addInfo=${encodeURIComponent(reference)}&accountName=${encodeURIComponent(settings.account_name || "")}`
    : "";
  const imageUrl = settings?.qr_image_url || generatedQrUrl;
  const [qrFailed, setQrFailed] = useState(false);

  useEffect(() => setQrFailed(false), [imageUrl]);

  return (
    <section className={`card bank-transfer ${showQr ? "" : "no-qr"}`}>
      <h2>{showQr ? t("Thanh toán bằng VietQR") : t("Thông tin chuyển khoản")}</h2>
      {showQr && (imageUrl && !qrFailed
        ? <img className="bank-transfer-qr" src={imageUrl} alt={`Mã QR thanh toán ${reference}`} onError={() => setQrFailed(true)} />
        : <p className="hint" role="alert">{t("Chưa tải được mã VietQR. Vui lòng chuyển khoản thủ công theo thông tin bên dưới.")}</p>)}
      <dl>
        <div><dt>{t("Ngân hàng")}</dt><dd>{settings?.bank_name || t("Chưa cấu hình")}</dd></div>
        <div><dt>{t("Chủ tài khoản")}</dt><dd>{settings?.account_name || t("Chưa cấu hình")}</dd></div>
        <div><dt>{t("Số tài khoản")}</dt><dd>{settings?.account_number || t("Chưa cấu hình")}</dd></div>
        <div><dt>{t("Số tiền")}</dt><dd>{formatVND(amount)}</dd></div>
        <div><dt>{t("Nội dung chuyển khoản")}</dt><dd className="payment-reference">{reference}</dd></div>
      </dl>
      <p className="hint">{t("Chuyển khoản không tự động xác nhận. Giao dịch chỉ hoàn tất sau khi nhân viên, quản lý hoặc Admin kiểm tra và duyệt.")}</p>
    </section>
  );
}
