// Lớp gọi API dùng chung: tự gắn JWT, tự ném lỗi có message tiếng Việt từ backend.
const BASE = import.meta.env.VITE_API_URL || "/api";
export const TOKEN_KEY = "cinevo_token";

async function request(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw Object.assign(new Error("Không kết nối được máy chủ. Hãy kiểm tra backend đang chạy."), { code: "NETWORK" });
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw Object.assign(new Error(data.message || "Có lỗi xảy ra."), { status: res.status, code: data.code, data });
  }
  return data;
}

export const api = {
  get: (p) => request(p),
  post: (p, body) => request(p, { method: "POST", body }),
  patch: (p, body) => request(p, { method: "PATCH", body }),
  put: (p, body) => request(p, { method: "PUT", body }),
  delete: (p) => request(p, { method: "DELETE" }),
  upload: async (path, formData) => {
    const headers = {};
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) headers.Authorization = `Bearer ${token}`;
    let res;
    try {
      res = await fetch(`${BASE}${path}`, { method: "POST", headers, body: formData });
    } catch {
      throw Object.assign(new Error("Không kết nối được máy chủ. Hãy kiểm tra backend đang chạy."), { code: "NETWORK" });
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw Object.assign(new Error(data.message || "Có lỗi xảy ra."), { status: res.status, code: data.code, data });
    }
    return data;
  },
  uploadWithProgress: (path, formData, onProgress) => new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const token = localStorage.getItem(TOKEN_KEY);
    xhr.open("POST", `${BASE}${path}`);
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.upload.addEventListener("progress", (event) => {
      if (!event.lengthComputable) return;
      onProgress?.(Math.min(99, Math.round((event.loaded / event.total) * 100)));
    });
    xhr.addEventListener("load", () => {
      let data = {};
      try {
        data = xhr.responseText ? JSON.parse(xhr.responseText) : {};
      } catch {
        reject(new Error("Máy chủ trả về dữ liệu không hợp lệ."));
        return;
      }
      if (xhr.status < 200 || xhr.status >= 300) {
        reject(Object.assign(new Error(data.message || "Có lỗi xảy ra."), {
          status: xhr.status,
          code: data.code,
          data,
        }));
        return;
      }
      onProgress?.(100);
      resolve(data);
    });
    xhr.addEventListener("error", () => {
      reject(Object.assign(new Error("Không kết nối được máy chủ. Hãy kiểm tra backend đang chạy."), { code: "NETWORK" }));
    });
    xhr.addEventListener("abort", () => reject(new Error("Đã hủy tải video lên.")));
    xhr.send(formData);
  }),
};
