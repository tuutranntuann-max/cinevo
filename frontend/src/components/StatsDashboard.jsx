// Dashboard số liệu tổng quan cho manager/admin.
import { useEffect, useState } from "react";
import { panelService } from "../services/panelService";
import ErrorBox from "./ErrorBox";
import Loading from "./Loading";
import RevenueCharts from "./RevenueCharts";
import FinanceDashboard from "./FinanceDashboard";

export default function StatsDashboard({ title, endpoint }) {
  const [stats, setStats] = useState(null);
  const [revenue, setRevenue] = useState(null);
  const [finance, setFinance] = useState(null);
  const [expenses, setExpenses] = useState([]);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);

  useEffect(() => {
    panelService.list(endpoint).then((d) => {
      setStats(d.stats);
      setRevenue(d.revenue || null);
      setFinance(d.finance || null);
      setExpenses(d.expenses || []);
    }).catch((e) => setError(e.message));
  }, [endpoint, refresh]);

  return (
    <section>
      <h1 className="page-title">{title}</h1>
      <ErrorBox message={error} />
      {!stats && !error ? <Loading /> : (
        <div className="stats">
          {stats?.map((s) => <div key={s.label} className="stat"><b>{s.value}</b><span>{s.label}</span></div>)}
        </div>
      )}
      {revenue && <RevenueCharts revenue={revenue} />}
      {finance && <FinanceDashboard finance={finance} expenses={expenses} onChange={() => setRefresh((value) => value + 1)} />}
    </section>
  );
}
