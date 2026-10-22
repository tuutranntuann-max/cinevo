// Trang quản lý dạng bảng: gọi 1 endpoint rồi hiển thị. Các trang manager/admin dùng lại component này.
// TODO (giai đoạn nghiệp vụ): thêm nút Thêm / Sửa / Xóa cho từng trang.
import { useEffect, useState } from "react";
import { panelService } from "../services/panelService";
import DataTable from "./DataTable";
import ErrorBox from "./ErrorBox";
import Loading from "./Loading";

export default function ResourcePage({ title, endpoint, columns, note }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setRows(null);
    panelService.list(endpoint).then(setRows).catch((e) => setError(e.message));
  }, [endpoint]);

  return (
    <section>
      {title && <h1 className="page-title">{title}</h1>}
      {note && <p className="muted">{note}</p>}
      <ErrorBox message={error} />
      {!rows && !error ? <Loading /> : rows && <DataTable columns={columns} rows={rows} />}
    </section>
  );
}
