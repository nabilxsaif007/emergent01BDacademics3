// Hand-rolled SVG charts — no charting dependency, matching FleetView's
// zero-dependency ethos (the same approach the openclaw dashboards use).

export const PALETTE = ["#3ea6ff", "#a371f7", "#3fb950", "#f0883e", "#f85149", "#56d4dd"];

// Donut chart from [{ label, value, color }]. Renders a centered total.
export function Donut({ data, size = 132, thickness = 16, center }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  let offset = 0;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="donut">
      <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none"
          stroke="var(--bg-3)" strokeWidth={thickness} />
        {total > 0 && data.map((d, i) => {
          const len = (d.value / total) * c;
          const seg = (
            <circle key={i} cx={size / 2} cy={size / 2} r={r} fill="none"
              stroke={d.color} strokeWidth={thickness}
              strokeDasharray={`${len} ${c - len}`} strokeDashoffset={-offset} />
          );
          offset += len;
          return seg;
        })}
      </g>
      {center != null && (
        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
          className="donut-center">{center}</text>
      )}
    </svg>
  );
}

// Filled sparkline from an array of numbers.
export function Sparkline({ values, width = 240, height = 56, color = "#3ea6ff" }) {
  if (!values || values.length === 0) return <div className="spark-empty">no data yet</div>;
  const max = Math.max(...values, 0.0001);
  const n = values.length;
  const dx = n > 1 ? width / (n - 1) : 0;
  const pts = values.map((v, i) => [i * dx, height - (v / max) * (height - 6) - 3]);
  const line = pts.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const area = `${pts[0][0]},${height} ${line} ${pts[n - 1][0]},${height}`;

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none" className="spark">
      <polygon points={area} fill={color} opacity="0.12" />
      <polyline points={line} fill="none" stroke={color} strokeWidth="2"
        strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
