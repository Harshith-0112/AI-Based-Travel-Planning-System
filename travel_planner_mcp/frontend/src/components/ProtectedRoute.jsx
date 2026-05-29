import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import LoadingState from "./LoadingState";

export default function ProtectedRoute() {
  const { initializing, isAuthenticated } = useAuth();

  if (initializing) {
    return <LoadingState title="Checking your session" subtitle="Preparing your travel workspace." />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <Outlet />;
}
