import { useCallback, useEffect, useState } from "react";
import ErrorBox from "./ErrorBox";
import Loading from "./Loading";
import { api } from "../services/api";

const INITIAL = {
  title: "",
  summary: "",
  body: "",
  category: "Tin điện ảnh",
  source: "",
  image_url: "",
  starts_at: "",
  ends_at: "",
  published_at: "",
  code: "",
  description: "",
  discount_percent: 10,
  active: true,
};

function fromDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function toDateTime(value) {
  return value ? new Date(value).toISOString() : null;
}

function initialForm(kind) {
  if (kind === "news") return { ...INITIAL, published_at: fromDateTime(new Date().toISOString()) };
  return { ...INITIAL };
}

function rowToForm(kind, row) {
  return {
    ...initialForm(kind),
    ...row,
    starts_at: fromDateTime(row.starts_at),
    ends_at: fromDateTime(row.ends_at),
    published_at: fromDateTime(row.published_at),
  };
}

function contentEndpoint(kind) {
  return `/content/manage/${kind}`;
}

export default function ContentManagementPage({ kind, title, description }) {
  const [rows, setRows] = useState(null);
  const [form, setForm] = useState(() => initialForm(kind));
  const [editingId, setEditingId] = useState(null);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const result = await api.get(contentEndpoint(kind));
      setRows(result);
      setError("");
    } catch (loadError) {
      setError(loadError.message);
    }
  }, [kind]);

  useEffect(() => {
    setRows(null);
    setForm(initialForm(kind));
    setEditingId(null);
    load();
  }, [kind, load]);

  useEffect(() => {
    if (!imageFile) {
      setImagePreview("");
      return undefined;
    }
    const preview = URL.createObjectURL(imageFile);
    setImagePreview(preview);
    return () => URL.revokeObjectURL(preview);
  }, [imageFile]);

  function update(event) {
    const { name, type, checked, value } = event.target;
    setForm((current) => ({ ...current, [name]: type === "checkbox" ? checked : value }));
  }

  function edit(row) {
    setEditingId(row.id);
    setForm(rowToForm(kind, row));
    setImageFile(null);
    setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function reset() {
    setEditingId(null);
    setForm(initialForm(kind));
    setImageFile(null);
    setError("");
  }

  async function save(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      let imageUrl = form.image_url;
      if (imageFile) {
        const data = new FormData();
        data.append("image", imageFile);
        const result = await api.upload("/content/manage/media", data);
        imageUrl = result.image_url;
      }
      const payload = { ...form, image_url: imageUrl || null };
      if (kind === "news") payload.published_at = toDateTime(form.published_at);
      if (kind === "events") {
        payload.starts_at = toDateTime(form.starts_at);
        payload.ends_at = toDateTime(form.ends_at);
      }
      if (kind === "promotions") payload.discount_percent = Number(form.discount_percent);
      if (editingId) {
        await api.put(`${contentEndpoint(kind)}/${editingId}`, payload);
      } else {
        await api.post(contentEndpoint(kind), payload);
      }
      reset();
      await load();
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  }

  async function remove(row) {
    if (!window.confirm(`Bạn chắc chắn muốn xóa "${row.title || row.code}"?`)) return;
    setError("");
    try {
      await api.delete(`${contentEndpoint(kind)}/${row.id}`);
      if (editingId === row.id) reset();
      await load();
    } catch (deleteError) {
      setError(deleteError.message);
    }
  }

  const isPromotion = kind === "promotions";
  const isNews = kind === "news";

  return (
    <section className="content-management-page">
      <header>
        <h1 className="page-title">{title}</h1>
        <p className="muted">{description}</p>
      </header>
      <ErrorBox message={error} />
      <form className="content-editor card" onSubmit={save}>
        <h2>{editingId ? "Chỉnh sửa nội dung" : "Thêm nội dung mới"}</h2>
        {isPromotion ? (
          <>
            <label>Mã giảm giá
              <input name="code" maxLength={30} required value={form.code} onChange={update} />
            </label>
            <label>Mức giảm (%)
              <input name="discount_percent" type="number" min="1" max="100" required
                value={form.discount_percent} onChange={update} />
            </label>
            <label className="content-editor-wide">Mô tả
              <input name="description" maxLength={250} value={form.description} onChange={update} />
            </label>
          </>
        ) : (
          <>
            <label>Tiêu đề
              <input name="title" maxLength={200} required value={form.title} onChange={update} />
            </label>
            {isNews && (
              <>
                <label>Chuyên mục
                  <input name="category" maxLength={60} value={form.category} onChange={update} />
                </label>
                <label>Nguồn báo chí
                  <input name="source" maxLength={200} placeholder="Tên báo / nguồn tin" value={form.source} onChange={update} />
                </label>
              </>
            )}
            <label className="content-editor-wide">Mô tả ngắn
              <textarea name="summary" maxLength={500} required rows={2} value={form.summary} onChange={update} />
            </label>
            <label className="content-editor-wide">{isNews ? "Nội dung bài viết" : "Thông tin sự kiện"}
              <textarea name="body" maxLength={20000} rows={5} required={isNews}
                value={form.body} onChange={update} />
            </label>
            {isNews ? (
              <label>Ngày đăng
                <input name="published_at" type="datetime-local" value={form.published_at} onChange={update} />
              </label>
            ) : (
              <>
                <label>Bắt đầu sự kiện
                  <input name="starts_at" type="datetime-local" value={form.starts_at} onChange={update} />
                </label>
                <label>Kết thúc sự kiện
                  <input name="ends_at" type="datetime-local" value={form.ends_at} onChange={update} />
                </label>
              </>
            )}
          </>
        )}
        <label className="content-editor-wide">Poster / ảnh giới thiệu
          <input type="file" accept="image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp"
            onChange={(event) => setImageFile(event.target.files?.[0] || null)} />
        </label>
        {imageFile && <img className="content-editor-preview" src={imagePreview} alt="Ảnh xem trước sẽ tải lên" />}
        {!imageFile && form.image_url && <img className="content-editor-preview" src={form.image_url} alt="Poster nội dung" />}
        <label className="content-editor-toggle">
          <input name="active" type="checkbox" checked={form.active} onChange={update} />
          {isNews ? "Đăng và hiển thị công khai" : "Đang hoạt động"}
        </label>
        <div className="content-editor-actions">
          <button className="btn btn-red" type="submit" disabled={saving}>
            {saving ? "Đang lưu..." : editingId ? "Lưu chỉnh sửa" : "Thêm mới"}
          </button>
          {editingId && <button className="btn btn-ghost" type="button" onClick={reset}>Hủy chỉnh sửa</button>}
        </div>
      </form>

      <div className="content-records-heading">
        <h2>Danh sách đã tạo</h2>
        <span className="muted small">{rows?.length ?? 0} mục</span>
      </div>
      {!rows ? <Loading /> : rows.length ? (
        <div className="content-record-list">
          {rows.map((row) => (
            <article className="content-record card" key={row.id}>
              {row.image_url && <img src={row.image_url} alt="" />}
              <div className="content-record-copy">
                <strong>{isPromotion ? row.code : row.title}</strong>
                <p>{isPromotion ? `${row.discount_percent}% · ${row.description || "Chưa có mô tả"}` : row.summary}</p>
                <span className={`content-record-status ${row.active ? "active" : ""}`}>
                  {row.active ? "Đang hiển thị" : "Đang ẩn"}
                </span>
              </div>
              <div className="content-record-actions">
                <button className="btn btn-ghost btn-sm" type="button" onClick={() => edit(row)}>Sửa</button>
                <button className="btn btn-danger btn-sm" type="button" onClick={() => remove(row)}>Xóa</button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="state-box">Chưa có nội dung. Dùng biểu mẫu bên trên để thêm mục đầu tiên.</div>
      )}
    </section>
  );
}
