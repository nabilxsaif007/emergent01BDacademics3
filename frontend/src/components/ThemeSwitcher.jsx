import { useEffect, useState } from "react";

const THEMES = [
  ["midnight", "Midnight", "#3ea6ff"],
  ["nord", "Nord", "#88c0d0"],
  ["mocha", "Mocha", "#cba6f7"],
  ["light", "Light", "#0969da"],
];

export default function ThemeSwitcher() {
  const [theme, setTheme] = useState(() => localStorage.getItem("fv-theme") || "midnight");

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("fv-theme", theme);
  }, [theme]);

  return (
    <div className="theme-switch">
      <span className="theme-label">Theme</span>
      <div className="theme-dots">
        {THEMES.map(([id, label, color]) => (
          <button
            key={id}
            title={label}
            className={`theme-dot ${theme === id ? "active" : ""}`}
            style={{ background: color }}
            onClick={() => setTheme(id)}
          />
        ))}
      </div>
    </div>
  );
}
