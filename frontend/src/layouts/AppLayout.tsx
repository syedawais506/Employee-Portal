import { useState } from "react";
import { Link as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  Breadcrumbs,
  Divider,
  Drawer,
  IconButton,
  Link,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
} from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import ApartmentIcon from "@mui/icons-material/Apartment";
import BadgeIcon from "@mui/icons-material/Badge";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import DashboardIcon from "@mui/icons-material/Dashboard";
import DomainIcon from "@mui/icons-material/Domain";
import HowToRegIcon from "@mui/icons-material/HowToReg";
import LogoutIcon from "@mui/icons-material/Logout";
import SecurityIcon from "@mui/icons-material/Security";
import WorkOutlineIcon from "@mui/icons-material/WorkOutline";

import { logout as logoutRequest } from "@/api/auth";
import { useAuthStore } from "@/store/authStore";
import { useThemeStore } from "@/store/themeStore";

const DRAWER_WIDTH = 260;

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
  match: (pathname: string) => boolean;
  visible: (opts: { isSuperAdmin: boolean; hasPermission: (m: string, a: string) => boolean }) => boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    to: "/",
    icon: <DashboardIcon fontSize="small" />,
    match: (p) => p === "/",
    visible: () => true,
  },
  {
    label: "Employees",
    to: "/employees",
    icon: <BadgeIcon fontSize="small" />,
    match: (p) => p.startsWith("/employees"),
    visible: ({ hasPermission }) => hasPermission("employee", "view"),
  },
  {
    label: "Departments",
    to: "/departments",
    icon: <DomainIcon fontSize="small" />,
    match: (p) => p.startsWith("/departments"),
    visible: ({ hasPermission }) => hasPermission("department", "view"),
  },
  {
    label: "Projects",
    to: "/projects",
    icon: <WorkOutlineIcon fontSize="small" />,
    match: (p) => p.startsWith("/projects"),
    visible: ({ isSuperAdmin }) => !isSuperAdmin,
  },
  {
    label: "Timesheets",
    to: "/timesheets",
    icon: <AccessTimeIcon fontSize="small" />,
    match: (p) => p.startsWith("/timesheets"),
    visible: ({ hasPermission }) => hasPermission("timesheet", "view"),
  },
  {
    label: "Onboarding",
    to: "/onboarding",
    icon: <HowToRegIcon fontSize="small" />,
    match: (p) => p.startsWith("/onboarding"),
    visible: ({ hasPermission }) => hasPermission("onboarding", "view"),
  },
  {
    label: "Roles & Permissions",
    to: "/roles",
    icon: <SecurityIcon fontSize="small" />,
    match: (p) => p.startsWith("/roles"),
    visible: ({ hasPermission }) => hasPermission("role", "view"),
  },
  {
    label: "Companies",
    to: "/companies",
    icon: <ApartmentIcon fontSize="small" />,
    match: (p) => p.startsWith("/companies"),
    visible: ({ isSuperAdmin }) => isSuperAdmin,
  },
];

function useBreadcrumbLabel(pathname: string): string {
  const active = NAV_ITEMS.find((item) => item.match(pathname) && item.to !== "/");
  return active?.label ?? "Dashboard";
}

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const clearSession = useAuthStore((state) => state.clearSession);
  const { mode, toggleMode } = useThemeStore();
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);

  const breadcrumbLabel = useBreadcrumbLabel(location.pathname);
  const isSuperAdmin = user?.is_super_admin ?? false;
  const visibleNavItems = NAV_ITEMS.filter((item) => item.visible({ isSuperAdmin, hasPermission }));

  async function handleLogout() {
    setMenuAnchor(null);
    try {
      await logoutRequest();
    } finally {
      clearSession();
      navigate("/login", { replace: true });
    }
  }

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Drawer
        variant="permanent"
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
            bgcolor: "sidebar.background",
            color: "sidebar.text",
            border: "none",
          },
        }}
      >
        <Toolbar sx={{ px: 3 }}>
          <Typography variant="h3" sx={{ color: "sidebar.text" }}>
            Employee Portal
          </Typography>
        </Toolbar>
        <Divider sx={{ borderColor: "rgba(255,255,255,0.08)" }} />
        <List sx={{ px: 1.5, py: 2 }}>
          {visibleNavItems.map((item) => {
            const active = item.match(location.pathname);
            return (
              <ListItemButton
                key={item.to}
                component={RouterLink}
                to={item.to}
                selected={active}
                sx={{
                  borderRadius: 2,
                  mb: 0.5,
                  color: "sidebar.text",
                  "&.Mui-selected": { bgcolor: "primary.main", color: "#fff" },
                  "&.Mui-selected:hover": { bgcolor: "primary.dark" },
                }}
              >
                <ListItemIcon sx={{ color: "inherit", minWidth: 36 }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            );
          })}
        </List>
      </Drawer>

      <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
        <AppBar
          position="sticky"
          color="transparent"
          elevation={0}
          sx={{ bgcolor: "background.paper", borderBottom: "1px solid", borderColor: "divider" }}
        >
          <Toolbar sx={{ justifyContent: "space-between" }}>
            <Breadcrumbs>
              <Link component={RouterLink} to="/" underline="hover" color="text.secondary">
                Home
              </Link>
              <Typography color="text.primary">{breadcrumbLabel}</Typography>
            </Breadcrumbs>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <IconButton onClick={toggleMode} size="small" aria-label="Toggle color mode">
                {mode === "dark" ? <Brightness7Icon fontSize="small" /> : <Brightness4Icon fontSize="small" />}
              </IconButton>
              <IconButton onClick={(event) => setMenuAnchor(event.currentTarget)} size="small">
                <Avatar sx={{ width: 32, height: 32, bgcolor: "primary.main", fontSize: 14 }}>
                  {(user?.full_name ?? user?.email ?? "?").charAt(0).toUpperCase()}
                </Avatar>
              </IconButton>
              <Menu anchorEl={menuAnchor} open={Boolean(menuAnchor)} onClose={() => setMenuAnchor(null)}>
                <Box sx={{ px: 2, py: 1, minWidth: 200 }}>
                  <Typography variant="body2" fontWeight={600}>
                    {user?.full_name ?? "Super Admin"}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {user?.email}
                  </Typography>
                </Box>
                <Divider />
                <MenuItem component={RouterLink} to="/profile" onClick={() => setMenuAnchor(null)}>
                  My Profile
                </MenuItem>
                <MenuItem onClick={handleLogout}>
                  <ListItemIcon>
                    <LogoutIcon fontSize="small" />
                  </ListItemIcon>
                  Logout
                </MenuItem>
              </Menu>
            </Box>
          </Toolbar>
        </AppBar>

        <Box component="main" sx={{ flexGrow: 1, p: 4 }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
