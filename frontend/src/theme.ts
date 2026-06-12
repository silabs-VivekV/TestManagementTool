import { createTheme, type Theme } from "@mui/material";

export function buildTheme(mode: "light" | "dark"): Theme {
  return createTheme({
    palette: {
      mode,
      primary: { main: "#2563eb" },
      secondary: { main: "#7c3aed" },
      ...(mode === "dark"
        ? { background: { default: "#0f172a", paper: "#1e293b" } }
        : { background: { default: "#f1f5f9", paper: "#ffffff" } }),
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: "'Inter', 'Segoe UI', system-ui, sans-serif",
      h5: { fontWeight: 700 },
      h6: { fontWeight: 600 },
    },
    components: {
      MuiCard: { defaultProps: { elevation: 0 }, styleOverrides: { root: { border: "1px solid", borderColor: mode === "dark" ? "#334155" : "#e2e8f0" } } },
    },
  });
}

export const STATUS_COLORS: Record<string, string> = {
  NOT_STARTED: "#94a3b8",
  IN_PROGRESS: "#3b82f6",
  BLOCKED: "#f59e0b",
  PASSED: "#22c55e",
  FAILED: "#ef4444",
  NEEDS_REVIEW: "#a855f7",
};
