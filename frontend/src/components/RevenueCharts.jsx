const COLORS = [
  "#ef476f", "#ffd166", "#06d6a0", "#118ab2", "#9b5de5", "#f15bb5",
  "#00bbf9", "#fee440", "#00f5d4", "#fb8500", "#80ed99", "#c77dff",
];

function formatCurrency(value) {
  return `${Number(value || 0).toLocaleString("vi-VN")} đ`;
}

function PieChart({ title, summary, items }) {
  const total = items.reduce((sum, item) => sum + item.amount, 0);
  let progress = 0;
  const slices = items.filter((item) => item.amount > 0).map((item) => {
    const start = progress;
    progress += item.amount / total * 100;
    return `${item.color} ${start}% ${progress}%`;
  });
  const chart = slices.length ? `conic-gradient(${slices.join(", ")})` : "#34343b";

  return (
    <article className="revenue-panel">
      <h2>{title}</h2>
      <div className="revenue-chart-layout">
        <div className="revenue-pie" role="img" aria-label={`${title}: ${formatCurrency(total)}`} style={{ background: chart }}>
          <div className="revenue-pie-center">
            <span>Tổng thu</span>
            <strong>{formatCurrency(total)}</strong>
          </div>
        </div>
        <ul className="revenue-legend">
          {items.map((item) => {
            const percent = total ? (item.amount / total * 100).toFixed(1) : "0.0";
            return (
              <li key={item.label}>
                <span className="revenue-legend-label">
                  <i style={{ backgroundColor: item.color }} />
                  {item.label}
                </span>
                <span>{formatCurrency(item.amount)} <small>({percent}%)</small></span>
              </li>
            );
          })}
        </ul>
      </div>
      <p className="muted small">{summary}</p>
    </article>
  );
}

export default function RevenueCharts({ revenue }) {
  const charts = [
    ["Doanh thu tuần này", "Chia theo ngày trong tuần", revenue.week],
    ["Doanh thu tháng này", "Chia theo từng tuần trong tháng", revenue.month],
    ["Doanh thu năm nay", "Chia theo tháng trong năm", revenue.year],
  ];

  return (
    <section className="revenue-dashboard" aria-label="Biểu đồ doanh thu">
      <h2 className="section-title">Doanh thu</h2>
      <div className="revenue-panels">
        {charts.map(([title, summary, series]) => (
          <PieChart
            key={title}
            title={title}
            summary={summary}
            items={(series?.items || []).map((item, index) => ({
              ...item,
              color: COLORS[index % COLORS.length],
            }))}
          />
        ))}
      </div>
    </section>
  );
}
