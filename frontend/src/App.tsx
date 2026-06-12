import { Navigate, Route, Routes } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "@/hooks/useAuth";
import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import TestCasesPage from "@/pages/TestCasesPage";
import AssignmentsPage from "@/pages/AssignmentsPage";
import AssignPage from "@/pages/AssignPage";
import ImportPage from "@/pages/ImportPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import WeeklyProgressPage from "@/pages/WeeklyProgressPage";

export default function App() {
  const { loading } = useAuth();
  if (loading) {
    return (
      <Box sx={{ display: "grid", placeItems: "center", height: "100vh" }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/test-cases" element={<TestCasesPage />} />
        <Route path="/assignments" element={<AssignmentsPage />} />
        <Route
          path="/assign"
          element={
            <ProtectedRoute roles={["ADMIN", "TEAM_LEAD"]}>
              <AssignPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/import"
          element={
            <ProtectedRoute roles={["ADMIN", "TEAM_LEAD"]}>
              <ImportPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics"
          element={
            <ProtectedRoute roles={["ADMIN", "TEAM_LEAD"]}>
              <AnalyticsPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analytics/weekly"
          element={
            <ProtectedRoute roles={["ADMIN", "TEAM_LEAD"]}>
              <WeeklyProgressPage />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
