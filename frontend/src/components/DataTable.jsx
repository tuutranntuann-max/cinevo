// Bảng dữ liệu chung cho trang quản lý. columns: [{ key, label, render? }]
export default function DataTable({ columns, rows }) {
  if (!rows.length) return <div className="state-box">Chưa có dữ liệu.</div>;
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map((c) => <th key={c.key}>{c.label}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id ?? r.code ?? i}>
              {columns.map((c) => <td key={c.key}>{c.render ? c.render(r) : String(r[c.key] ?? "")}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
