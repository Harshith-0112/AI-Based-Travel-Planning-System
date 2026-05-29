import { Navigate, Route, Routes } from "react-router-dom";

import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import CreateTrip from "./pages/CreateTrip";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Trips from "./pages/Trips";
import TripResult from "./pages/TripResult";

function AppShell({ children }) {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-7xl px-4 pb-10 pt-8 sm:px-6 lg:px-8">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<AppShell><Dashboard /></AppShell>} />
        <Route path="/create-trip" element={<AppShell><CreateTrip /></AppShell>} />
        <Route path="/trip-result" element={<AppShell><TripResult /></AppShell>} />
        <Route path="/trips" element={<AppShell><Trips /></AppShell>} />
        <Route path="/saved-trips" element={<Navigate to="/trips" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
