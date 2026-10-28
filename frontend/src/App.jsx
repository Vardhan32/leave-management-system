import { Navigate, Outlet, Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { useAuth } from "./auth/AuthContext";
import ApprovalsPage from "./pages/ApprovalsPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import MyLeavePage from "./pages/MyLeavePage";
import NotFoundPage from "./pages/NotFoundPage";
import RegisterPage from "./pages/RegisterPage";
import TeamPage from "./pages/TeamPage";

function BootScreen() {
  return (
    <div className="boot-screen">
      <span className="spinner" />
    </div>
  );
}

function Protected() {
  const { user, booting } = useAuth();
  if (booting) return <BootScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

function GuestOnly({ children }) {
  const { user, booting } = useAuth();
  if (booting) return <BootScreen />;
  if (user) return <Navigate to="/" replace />;
  return children;
}

function AdminOnly() {
  const { user } = useAuth();
  if (user?.role !== "admin") return <Navigate to="/" replace />;
  return <Outlet />;
}

export default function App() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <GuestOnly>
            <LoginPage />
          </GuestOnly>
        }
      />
      <Route
        path="/register"
        element={
          <GuestOnly>
            <RegisterPage />
          </GuestOnly>
        }
      />

      <Route element={<Protected />}>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="leave" element={<MyLeavePage />} />
          <Route element={<AdminOnly />}>
            <Route path="approvals" element={<ApprovalsPage />} />
            <Route path="team" element={<TeamPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
