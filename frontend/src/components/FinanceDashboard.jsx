import { useState } from "react";
import { useUserPreferences } from "../context/UserPreferencesContext";
import { api } from "../services/api";
import { formatVND } from "../utils/format";
import ErrorBox from "./ErrorBox";

function localDateValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function FinanceChart({ title, series }) {
  const { t } = useUserPreferences();
  const items = series?.items || [];
  const maxValue = Math.max(1, ...items.flatMap((item) => [item.income, item.expense]));

  return (
    <article className="finance-panel">
      <h3>{title}</h3>
      <div className="finance-totals">
        <span>{t("Thu")}: <b>{formatVND(series?.income)}</b></span>
        <span>{t("Chi")}: <b>{formatVND(series?.expense)}</b></span>
        <span>{t("Lãi/lỗ")}: <b className={(series?.profit || 0) < 0 ? "finance-loss" : ""}>{formatVND(series?.profit)}</b></span>
      </div>
      <div className="finance-bars">
        {items.map((item) => (
          <div className="finance-bar-row" key={item.label}>
            <span className="finance-bar-label">{item.label}</span>
            <div className="finance-bar-track" aria-label={`${item.label}: ${t("Thu")} ${formatVND(item.income)}, ${t("Chi")} ${formatVND(item.expense)}`}>
              <i className="finance-income-bar" style={{ width: `${item.income / maxValue * 100}%` }} />
              <i className="finance-expense-bar" style={{ width: `${item.expense / maxValue * 100}%` }} />
            </div>
            <span className={`finance-profit${item.profit < 0 ? " finance-loss" : ""}`}>{formatVND(item.profit)}</span>
          </div>
        ))}
      </div>
      <div className="finance-legend">
        <span><i className="finance-income-bar" />{t("Thu")}</span>
        <span><i className="finance-expense-bar" />{t("Chi")}</span>
      </div>
    </article>
  );
}

export default function FinanceDashboard({ finance, expenses, onChange }) {
  const { t } = useUserPreferences();
  const [spentOn, setSpentOn] = useState(localDateValue);
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const saveExpense = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/admin/expenses", {
        spent_on: spentOn,
        description: description.trim(),
        amount: Number(amount),
      });
      setDescription("");
      setAmount("");
      onChange();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const deleteExpense = async (id) => {
    setError("");
    try {
      await api.delete(`/admin/expenses/${id}`);
      onChange();
    } catch (err) {
      setError(err.message);
    }
  };

  const charts = [
    [t("Tuần này"), finance?.week],
    [t("Tháng này"), finance?.month],
    [t("Năm nay"), finance?.year],
  ];

  return (
    <section className="finance-dashboard" aria-label={t("Theo dõi thu chi")}>
      <h2 className="section-title">{t("Thu - chi - lãi/lỗ")}</h2>
      <div className="finance-panels">
        {charts.map(([title, series]) => <FinanceChart key={title} title={title} series={series} />)}
      </div>
      <section className="finance-expenses">
        <h3>{t("Quản lý khoản chi")}</h3>
        <form className="admin-catalog-form finance-expense-form" onSubmit={saveExpense}>
          <div className="admin-catalog-fields">
            <label>{t("Ngày chi")}
              <input type="date" value={spentOn} onChange={(event) => setSpentOn(event.target.value)} required />
            </label>
            <label>{t("Nội dung")}
              <input value={description} onChange={(event) => setDescription(event.target.value)} maxLength={250} required />
            </label>
            <label>{t("Số tiền (đ)")}
              <input type="number" min="1" max="2000000000" step="1" value={amount} onChange={(event) => setAmount(event.target.value)} required />
            </label>
            <button className="btn btn-red" disabled={busy}>{busy ? t("Đang lưu...") : t("Thêm khoản chi")}</button>
          </div>
        </form>
        <ErrorBox message={error} />
        <div className="table-wrap">
          <table>
            <thead><tr><th>{t("Ngày")}</th><th>{t("Nội dung")}</th><th>{t("Số tiền")}</th><th /></tr></thead>
            <tbody>
              {(expenses || []).map((expense) => (
                <tr key={expense.id}>
                  <td>{expense.spent_on}</td>
                  <td>{expense.description}</td>
                  <td>{formatVND(expense.amount)}</td>
                  <td><button className="btn btn-ghost btn-sm" onClick={() => deleteExpense(expense.id)}>{t("Xóa")}</button></td>
                </tr>
              ))}
              {!expenses?.length && <tr><td colSpan="4" className="muted">{t("Chưa có khoản chi nào.")}</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}
