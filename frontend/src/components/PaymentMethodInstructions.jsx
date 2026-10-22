import { useState } from "react";
import BankTransferInstructions from "./BankTransferInstructions";
import { PAYMENT_BANKS, PAYMENT_WALLETS } from "../data/paymentInstitutions";
import { useUserPreferences } from "../context/UserPreferencesContext";

export default function PaymentMethodInstructions({ settings, amount, reference, initialMethod = "VIETQR" }) {
  const { t } = useUserPreferences();
  const [method, setMethod] = useState(initialMethod);
  const [selectedInstitution, setSelectedInstitution] = useState("MBBank:970422");
  const institutions = [...PAYMENT_BANKS, ...PAYMENT_WALLETS];
  const institution = institutions.find((item) => `${item.name}:${item.bin || ""}` === selectedInstitution);

  return (
    <>
      <div className="payment-method-options" role="group" aria-label={t("Phương thức thanh toán")}>
        <button type="button" className={`btn ${method === "VIETQR" ? "btn-red" : "btn-outline"}`}
          aria-pressed={method === "VIETQR"} onClick={() => setMethod("VIETQR")}>
          {t("Quét mã VietQR")}
        </button>
        <button type="button" className={`btn ${method === "BANK" ? "btn-red" : "btn-outline"}`}
          aria-pressed={method === "BANK"} onClick={() => setMethod("BANK")}>
          {t("Mở ngân hàng / ví")}
        </button>
      </div>
      {method === "BANK" && (
        <>
          <label className="payment-institution-select">{t("Chọn website ngân hàng hoặc ví")}
            <select value={selectedInstitution} onChange={(event) => setSelectedInstitution(event.target.value)}>
              <optgroup label={t("Ngân hàng và ứng dụng chuyển khoản")}>
                {PAYMENT_BANKS.map((item) => (
                  <option key={`${item.name}-${item.bin}`} value={`${item.name}:${item.bin}`}>{item.name}</option>
                ))}
              </optgroup>
              <optgroup label={t("Ví và dịch vụ thanh toán")}>
                {PAYMENT_WALLETS.map((item) => <option key={item.name} value={`${item.name}:`}>{item.name}</option>)}
              </optgroup>
            </select>
          </label>
        </>
      )}
      <BankTransferInstructions settings={settings} amount={amount} reference={reference} showQr={method === "VIETQR"} />
      {method === "BANK" && (
        <div className="card bank-redirect">
          <h3>{t("Tiếp tục tại")} {institution?.name || t("ngân hàng")}</h3>
          <p className="muted">{t("Mở trang chính thức của ngân hàng/ví, đăng nhập và tự chuyển đúng số tiền cùng nội dung giao dịch ở trên. Cinevo không nhận thông tin đăng nhập ngân hàng.")}</p>
          {institution?.url && (
            <a className="btn btn-red" href={institution.url} target="_blank" rel="noopener noreferrer">
              {t("Mở website")} {institution.name}
            </a>
          )}
          {!institution?.url && <p className="hint">{t("Chưa có liên kết website đã xác minh cho đơn vị này. Bạn vẫn có thể chuyển khoản theo thông tin trên hoặc quay lại chọn VietQR.")}</p>}
          <p className="hint">{t("Đường dẫn chỉ mở website; không tự điền lệnh chuyển khoản và không xác nhận thanh toán tự động.")}</p>
        </div>
      )}
    </>
  );
}
