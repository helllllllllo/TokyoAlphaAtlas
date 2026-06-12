import { NavLink } from "react-router-dom";

export function TopBar({ children }: { children?: React.ReactNode }) {
  const cls = ({ isActive }: { isActive: boolean }) => (isActive ? "active" : "");
  return (
    <nav className="topbar">
      <span className="brand">Tokyo Alpha Atlas</span>
      <NavLink to="/" end className={cls}>地図</NavLink>
      <NavLink to="/compare" className={cls}>比較</NavLink>
      <NavLink to="/benchmark" className={cls}>査定</NavLink>
      <div style={{ marginLeft: "auto" }}>{children}</div>
    </nav>
  );
}
