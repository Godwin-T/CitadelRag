import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

type NavItem = {
  label: string;
  path: string;
  icon: ReactNode;
};

type Props = {
  items: NavItem[];
  collapsed: boolean;
  onToggle: () => void;
  onLogout: () => void;
  theme: "light" | "dark";
  onThemeToggle: () => void;
};

export default function SidebarNav({ items, collapsed, onToggle, onLogout, theme, onThemeToggle }: Props) {
  return (
    <aside
      className={`card h-full flex flex-col gap-6 p-4 transition-all ${
        collapsed ? "w-[86px]" : "w-[260px]"
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-11 w-11 rounded-2xl bg-[color:var(--accent)] text-white flex items-center justify-center font-semibold">
            AI
          </div>
          {!collapsed && (
            <div>
              <div className="font-display text-sm">Admin Portal</div>
              <div className="text-[11px] uppercase tracking-[0.2em] text-[color:var(--muted)]">
                Enterprise RAG
              </div>
            </div>
          )}
        </div>
        <button
          className="h-7 w-7 rounded-full border border-[color:var(--border)] text-[color:var(--muted)] hover:text-[color:var(--accent)]"
          onClick={onToggle}
          title={collapsed ? "Expand" : "Collapse"}
        >
          {collapsed ? "›" : "‹"}
        </button>
      </div>

      <nav className="flex-1 space-y-2">
        {items.map((item) => (
          <NavLink
            key={item.label}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-2xl px-3 py-2 text-sm transition ${
                isActive
                  ? "bg-[color:var(--accent)] text-white shadow"
                  : "text-[color:var(--muted-strong)] hover:bg-[color:var(--bg-secondary)]"
              }`
            }
          >
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[color:var(--accent-soft)] text-[color:var(--accent)]">
              {item.icon}
            </span>
            {!collapsed && <span className="font-medium">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      <div className="space-y-3">
        <button
          className="w-full rounded-2xl border border-[color:var(--border)] px-3 py-2 text-xs uppercase tracking-[0.2em] text-[color:var(--muted)]"
          onClick={onThemeToggle}
        >
          {theme === "light" ? "Dark Mode" : "Light Mode"}
        </button>
        <button
          className="w-full rounded-2xl px-3 py-2 text-sm text-[color:var(--muted)] hover:text-[color:var(--accent)]"
          onClick={onLogout}
        >
          {collapsed ? "Logout" : "Log out"}
        </button>
      </div>
    </aside>
  );
}
