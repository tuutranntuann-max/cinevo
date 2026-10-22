// Dùng cho các trang quản lý (manager/admin): chỉ cần GET một endpoint.
import { api } from "./api";
export const panelService = { list: (endpoint) => api.get(endpoint) };
