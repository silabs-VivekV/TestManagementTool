import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";
import {
  AppBar,
  Box,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Tooltip,
  Typography,
} from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";
import ListAltIcon from "@mui/icons-material/ListAlt";
import AssignmentIcon from "@mui/icons-material/Assignment";
import AssignmentIndIcon from "@mui/icons-material/AssignmentInd";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import InsightsIcon from "@mui/icons-material/Insights";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import LogoutIcon from "@mui/icons-material/Logout";
import DarkModeIcon from "@mui/icons-material/DarkMode";
import LightModeIcon from "@mui/icons-material/LightMode";
import { useAuth } from "@/hooks/useAuth";
import { useColorMode } from "@/hooks/useColorMode";
import type { UserRole } from "@/types";

const DRAWER_WIDTH = 232;

interface NavItem {
  label: string;
  to: string;
  icon: JSX.Element;
  roles?: UserRole[];
}

const NAV: NavItem[] = [
  { label: "Dashboard", to: "/", icon: <DashboardIcon /> },
  { label: "Test Cases", to: "/test-cases", icon: <ListAltIcon /> },
  { label: "Assignments", to: "/assignments", icon: <AssignmentIcon /> },
  { label: "Assign", to: "/assign", icon: <AssignmentIndIcon />, roles: ["ADMIN", "TEAM_LEAD"] },
  { label: "Import", to: "/import", icon: <UploadFileIcon />, roles: ["ADMIN", "TEAM_LEAD"] },
  { label: "Analytics", to: "/analytics", icon: <InsightsIcon />, roles: ["ADMIN", "TEAM_LEAD"] },
  {
    label: "Weekly Progress",
    to: "/analytics/weekly",
    icon: <TrendingUpIcon />,
    roles: ["ADMIN", "TEAM_LEAD"],
  },
];

export default function Layout() {
  const { user, logout, hasRole } = useAuth();
  const { mode, toggle } = useColorMode();
  const location = useLocation();
  const items = NAV.filter((n) => !n.roles || hasRole(...n.roles));

  return (
    <Box sx={{ display: "flex" }}>
      <AppBar position="fixed" color="default" sx={{ zIndex: (t) => t.zIndex.drawer + 1 }} elevation={0}>
        <Toolbar sx={{ borderBottom: "1px solid", borderColor: "divider" }}>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Test Case Tracker
          </Typography>
          <Typography variant="body2" sx={{ mr: 2, opacity: 0.7 }}>
            {user?.name} · {user?.role}
          </Typography>
          <Tooltip title="Toggle theme">
            <IconButton onClick={toggle}>{mode === "dark" ? <LightModeIcon /> : <DarkModeIcon />}</IconButton>
          </Tooltip>
          <Tooltip title="Logout">
            <IconButton onClick={logout}>
              <LogoutIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: DRAWER_WIDTH, boxSizing: "border-box" },
        }}
      >
        <Toolbar />
        <List sx={{ px: 1 }}>
          {items.map((item) => (
            <ListItemButton
              key={item.to}
              component={RouterLink}
              to={item.to}
              selected={location.pathname === item.to}
              sx={{ borderRadius: 2, mb: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: 3, minHeight: "100vh" }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
