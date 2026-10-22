import { useEffect, useState } from "react";
import { api } from "../services/api";
import { formatVND } from "../utils/format";
import ErrorBox from "./ErrorBox";
import Loading from "./Loading";

const EMPTY = {
  name: "",
  category: "Khác",
  description: "",
  price: "",
  stock_quantity: "0",
  is_combo: false,
  available: true,
  active: true,
};

export default function AdminCatalogPage({ title, endpoint, kind }) {
  const isFood = kind === "food";
  const [rows, setRows] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function loadRows() {
    setError("");
    try {
      setRows(await api.get(endpoint));
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    loadRows();
  }, [endpoint]);

  function editRow(row) {
    setEditingId(row.id);
    setForm({ ...EMPTY, ...row, price: String(row.price), stock_quantity: String(row.stock_quantity ?? 0) });
  }

  function resetForm() {
    setEditingId(null);
    setForm(EMPTY);
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const payload = {
      name: form.name,
      description: form.description,
      price: Number(form.price),
      ...(isFood
        ? { is_combo: form.is_combo, available: form.available }
        : { category: form.category, stock_quantity: Number(form.stock_quantity), active: form.active }),
    };
    try {
      if (editingId === null) await api.post(endpoint, payload);
      else await api.put(`${endpoint}/${editingId}`, payload);
      resetForm();
      await loadRows();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleRow(row) {
    setError("");
    try {
      const key = isFood ? "available" : "active";
      await api.put(`${endpoint}/${row.id}`, { [key]: !row[key] });
      await loadRows();
    } catch (e) {
      setError(e.message);
    }
  }

  function setField(event) {
    const { name, value, type, checked } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  return (
    <section>
      <h1 className="page-title">{title}</h1>
      <p className="muted">Chỉ tài khoản có quyền quản lý được phép thay đổi dữ liệu.</p>
      <ErrorBox message={error} />

      <form className="card admin-catalog-form" onSubmit={save}>
        <h2>{editingId === null ? "Thêm mặt hàng" : "Cập nhật mặt hàng"}</h2>
        <div className="admin-catalog-fields">
          <label>Tên mặt hàng<input name="name" value={form.name} onChange={setField} maxLength="100" required /></label>
          {!isFood && <label>Danh mục<input name="category" value={form.category} onChange={setField} maxLength="60" required /></label>}
          <label>Giá (VND)<input name="price" type="number" min="0" max="1000000000" value={form.price} onChange={setField} required /></label>
          {!isFood && <label>Tồn kho<input name="stock_quantity" type="number" min="0" max="1000000000" value={form.stock_quantity} onChange={setField} required /></label>}
          <label className="admin-catalog-wide">Mô tả<input name="description" value={form.description} onChange={setField} maxLength="200" /></label>
          {isFood ? (
            <>
              <label className="admin-catalog-check"><input name="is_combo" type="checkbox" checked={form.is_combo} onChange={setField} /> Là combo</label>
              <label className="admin-catalog-check"><input name="available" type="checkbox" checked={form.available} onChange={setField} /> Đang bán</label>
            </>
          ) : (
            <label className="admin-catalog-check"><input name="active" type="checkbox" checked={form.active} onChange={setField} /> Đang kinh doanh</label>
          )}
        </div>
        <div className="actions">
          {editingId !== null && <button className="btn btn-ghost" type="button" onClick={resetForm}>Hủy sửa</button>}
          <button className="btn btn-red" disabled={saving}>{saving ? "Đang lưu..." : editingId === null ? "Thêm mặt hàng" : "Lưu thay đổi"}</button>
        </div>
      </form>

      <h2 className="section-title">Danh sách mặt hàng</h2>
      {rows === null ? <Loading /> : rows.length === 0 ? <div className="state-box">Chưa có mặt hàng nào.</div> : (
        <div className="table-wrap">
          <table>
            <thead><tr>
              <th>Tên</th>
              {!isFood && <th>Danh mục</th>}
              {isFood && <th>Loại</th>}
              <th>Giá</th>
              {!isFood && <th>Tồn kho</th>}
              <th>Trạng thái</th>
              <th>Thao tác</th>
            </tr></thead>
            <tbody>{rows.map((row) => {
              const enabled = isFood ? row.available : row.active;
              return <tr key={row.id}>
                <td>{row.name}</td>
                {isFood ? <td>{row.is_combo ? "Combo" : "Đồ ăn / thức uống"}</td> : <td>{row.category}</td>}
                <td>{formatVND(row.price)}</td>
                {!isFood && <td>{row.stock_quantity}</td>}
                <td>{enabled ? "Đang bán" : "Ngừng bán"}</td>
                <td className="admin-catalog-actions">
                  <button className="btn btn-ghost btn-sm" onClick={() => editRow(row)}>Sửa</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => toggleRow(row)}>{enabled ? "Ngừng bán" : "Mở bán"}</button>
                </td>
              </tr>;
            })}</tbody>
          </table>
        </div>
      )}
    </section>
  );
}
