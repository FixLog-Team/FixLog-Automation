import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import History from "./pages/History.jsx";
import RunDetail from "./pages/RunDetail.jsx";
import RunSettings from "./pages/RunSettings.jsx";
import Scenarios from "./pages/Scenarios.jsx";

const MENU = [
  { to: "/", label: "대시보드", end: true },
  { to: "/scenarios", label: "시나리오" },
  { to: "/settings", label: "실행 설정" },
  { to: "/runs", label: "실행 이력" },
];

export default function App() {
  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">FixLog<span>Automation</span></div>
        <nav>
          {MENU.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scenarios" element={<Scenarios />} />
          <Route path="/settings" element={<RunSettings />} />
          <Route path="/runs" element={<History />} />
          <Route path="/runs/:runId" element={<RunDetail />} />
        </Routes>
      </main>
    </div>
  );
}
