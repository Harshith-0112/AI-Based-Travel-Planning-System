import { Link, NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const navLinkClass = ({ isActive }) =>
  `rounded-full px-4 py-2 text-sm font-semibold transition ${
    isActive ? "bg-white/15 text-white" : "text-slate-300 hover:bg-white/10 hover:text-white"
  }`;

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="sticky top-0 z-30 border-b border-white/10 bg-slate-950/55 backdrop-blur-2xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
        <Link to="/dashboard" className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl bg-teal-300 font-black text-slate-950">
            AI
          </div>
          <div>
            <p className="text-sm font-black uppercase tracking-[0.22em] text-teal-200">Travel</p>
            <p className="-mt-1 text-lg font-black text-white">Planner</p>
          </div>
        </Link>

        <nav className="hidden items-center gap-2 md:flex">
          <NavLink to="/dashboard" className={navLinkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/create-trip" className={navLinkClass}>
            Create Trip
          </NavLink>
          <NavLink to="/trips" className={navLinkClass}>
            Trips
          </NavLink>
        </nav>

        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block">
            <p className="text-sm font-semibold text-white">{user?.full_name || "Traveler"}</p>
            <p className="text-xs text-slate-400">{user?.email}</p>
          </div>
          <button onClick={handleLogout} className="secondary-button px-4 py-2">
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
