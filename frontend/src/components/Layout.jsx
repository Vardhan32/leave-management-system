import { useEffect, useState } from "react";
import {
  CalendarDays,
  ClipboardCheck,
  LayoutDashboard,
  LogOut,
  Menu,
  Palmtree,
  Users,
  X,
} from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import Avatar from "./Avatar";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const isAdmin = user?.role === "admin";

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const links = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/leave", label: "My leave", icon: CalendarDays },
    ...(isAdmin
      ? [
          { to: "/approvals", label: "Approvals", icon: ClipboardCheck },
          { to: "/team", label: "Team", icon: Users },
        ]
      : []),
  ];

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar__inner">
          <Link className="brand" to="/" aria-label="LeaveDesk home">
            <span className="brand__mark">
              <Palmtree size={20} strokeWidth={2.2} />
            </span>
            <span className="brand__name">
              Leave<span>Desk</span>
            </span>
          </Link>

          <nav
            className={`topnav ${menuOpen ? "topnav--open" : ""}`}
            aria-label="Primary navigation"
          >
            {links.map(({ to, label, icon: Icon, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `topnav__link ${isActive ? "is-active" : ""}`
                }
              >
                <Icon size={16} />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="topbar__right">
            <div className="account">
              <Avatar name={user?.name} size="sm" />
              <span className="account__text">
                <strong>{user?.name}</strong>
                <small>
                  {user?.job_title || (isAdmin ? "HR administrator" : user?.department)}
                </small>
              </span>
            </div>
            <button
              type="button"
              className="icon-button topbar__logout"
              onClick={handleLogout}
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut size={17} />
            </button>
            <button
              type="button"
              className="icon-button topbar__menu"
              onClick={() => setMenuOpen((open) => !open)}
              aria-expanded={menuOpen}
              aria-label={menuOpen ? "Close navigation" : "Open navigation"}
            >
              {menuOpen ? <X size={19} /> : <Menu size={19} />}
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <span className="app-footer__brand">LeaveDesk</span>
        <span>Time off, minus the back-and-forth.</span>
      </footer>
    </div>
  );
}
