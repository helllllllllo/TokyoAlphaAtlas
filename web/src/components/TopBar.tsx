import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";

export function TopBar({ children }: { children?: ReactNode }) {
  const cls = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");
  return (
    <nav className="topbar">
      <span className="brand">Greater Tokyo Alpha Atlas</span>
      <NavLink to="/" end className={cls}>地図</NavLink>
      <NavLink to="/discover" className={cls}>発掘</NavLink>
      <NavLink to="/compare" className={cls}>比較</NavLink>
      <NavLink to="/benchmark" className={cls}>査定</NavLink>
      <div className="topbar-actions">{children}</div>
    </nav>
  );
}
