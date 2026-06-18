import { Donut, Sparkline, PALETTE } from "./charts.jsx";

const money = (n) => "$" + (n || 0).toFixed(n >= 1 ? 2 : 4);
const compact = (n) => {
  if (n >= 1e6) return (n / 1e6).toFixed(1) + "M";
  if (n >= 1e3) return (n / 1e3).toFixed(1) + "k";
  return String(n || 0);
};
const shortModel = (m) => m.replace("claude-", "").replace(/-\d+$/, "");

export default function CostPanel({ metrics }) {
  if (!metrics) return null;
  const { today, total, by_model, daily } = metrics;
  const projected = (today?.cost || 0) * 30;

  const donutData = (by_model || [])
    .filter((m) => m.cost > 0)
    .map((m, i) => ({ label: shortModel(m.model), value: m.cost, color: PALETTE[i % PALETTE.length] }));
  const series = (daily || []).map((d) => d.cost);

  return (
    <div className="cost-panel">
      <div className="cost-cards">
        <Money label="Today" value={today?.cost} />
        <Money label="All-time" value={total?.cost} />
        <Money label="Projected / mo" value={projected} muted />
      </div>

      <div className="cost-charts">
        <div className="cost-donut">
          <Donut data={donutData} center={money(total?.cost || 0)} />
          <div className="legend">
            {donutData.length === 0 && <span className="muted">no spend yet</span>}
            {donutData.map((d) => (
              <div className="legend-row" key={d.label}>
                <span className="legend-dot" style={{ background: d.color }} />
                <span className="legend-label">{d.label}</span>
                <span className="legend-val">{money(d.value)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="cost-trend">
          <div className="cost-trend-head">
            <span>Daily spend</span>
            <span className="muted">{compact((total?.tokens_in || 0) + (total?.tokens_out || 0))} tok</span>
          </div>
          <Sparkline values={series} />
        </div>
      </div>
    </div>
  );
}

function Money({ label, value, muted }) {
  return (
    <div className={`cost-card ${muted ? "muted-card" : ""}`}>
      <div className="cost-value">{money(value || 0)}</div>
      <div className="cost-label">{label}</div>
    </div>
  );
}
