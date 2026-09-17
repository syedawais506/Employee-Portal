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
  useMediaQuery,
  useTheme,
} from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import ApartmentIcon from "@mui/icons-material/Apartment";
import AssessmentIcon from "@mui/icons-material/Assessment";
import BadgeIcon from "@mui/icons-material/Badge";
import BeachAccessIcon from "@mui/icons-material/BeachAccess";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import DashboardIcon from "@mui/icons-material/Dashboard";
import DomainIcon from "@mui/icons-material/Domain";
import HowToRegIcon from "@mui/icons-material/HowToReg";
import IntegrationInstructionsIcon from "@mui/icons-material/IntegrationInstructions";
import InventoryIcon from "@mui/icons-material/Inventory";
import LogoutIcon from "@mui/icons-material/Logout";
import MenuIcon from "@mui/icons-material/Menu";
import SecurityIcon from "@mui/icons-material/Security";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import WorkOutlineIcon from "@mui/icons-material/WorkOutline";

import { logout as logoutRequest } from "@/api/auth";
import { NotificationBell } from "@/components/NotificationBell";
import { useAuthStore } from "@/store/authStore";
import { useThemeStore } from "@/store/themeStore";

const DRAWER_WIDTH = 260;

interface NavItem {
  label: string;
  to: string;
  icon: React.ReactNode;
  match: (pathname: string) => boolean;
  visible: (opts: {
    isSuperAdmin: boolean;
    hasPermission: (m: string, a: string) => boolean;
    aiChatbotEnabled: boolean;
  }) => boolean;
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
    visible: ({ isSuperAdmin, hasPermission }) => !isSuperAdmin && hasPermission("employee", "view"),
  },
  {
    label: "Departments",
    to: "/departments",
    icon: <DomainIcon fontSize="small" />,
    match: (p) => p.startsWith("/departments"),
    visible: ({ isSuperAdmin, hasPermission }) => !isSuperAdmin && hasPermission("department", "view"),
  },
  {
    label: "Projects",
    to: "/projects",
    icon: <WorkOutlineIcon fontSize="small" />,
    match: (p) => p.startsWith("/projects"),
    visible: ({ isSuperAdmin }) => !isSuperAdmin,
  },
  {
    label: "Attendance",
    to: "/attendance",
    icon: <EventAvailableIcon fontSize="small" />,
    match: (p) => p.startsWith("/attendance"),
    visible: ({ isSuperAdmin }) => !isSuperAdmin,
  },
  {
    label: "Timesheets",
    to: "/timesheets",
    icon: <AccessTimeIcon fontSize="small" />,
    match: (p) => p.startsWith("/timesheets"),
    visible: ({ isSuperAdmin, hasPermission }) => !isSuperAdmin && hasPermission("timesheet", "view"),
  },
  {
    label: "Leave",
    to: "/leave",
    icon: <BeachAccessIcon fontSize="small" />,
    match: (p) => p.startsWith("/leave"),
    visible: ({ isSuperAdmin, hasPermission }) => !isSuperAdmin && hasPermission("leave", "view"),
  },
  {
    label: "Assets",
    to: "/assets",
    icon: <InventoryIcon fontSize="small" />,
    match: (p) => p.startsWith("/assets"),
    visible: ({ isSuperAdmin }) => !isSuperAdmin,
  },
  {
    label: "Ask HR",
    to: "/ask-hr",
    icon: <SmartToyIcon fontSize="small" />,
    match: (p) => p.startsWith("/ask-hr"),
    visible: ({ isSuperAdmin, aiChatbotEnabled }) => !isSuperAdmin && aiChatbotEnabled,
  },
  {
    label: "Onboarding",
    to: "/onboarding",
    icon: <HowToRegIcon fontSize="small" />,
    match: (p) => p.startsWith("/onboarding"),
    visible: ({ isSuperAdmin, hasPermission }) => !isSuperAdmin && hasPermission("onboarding", "view"),
  },
  {
    label: "Reports",
    to: "/reports",
    icon: <AssessmentIcon fontSize="small" />,
    match: (p) => p.startsWith("/reports"),
    visible: ({ isSuperAdmin, hasPermission }) => !isSuperAdmin && hasPermission("report", "view"),
  },
  {
    label: "Roles & Permissions",
    to: "/roles",
    icon: <SecurityIcon fontSize="small" />,
    match: (p) => p.startsWith("/roles"),
    visible: ({ isSuperAdmin, hasPermission }) => !isSuperAdmin && hasPermission("role", "view"),
  },
  {
    label: "Integrations",
    to: "/integrations",
    icon: <IntegrationInstructionsIcon fontSize="small" />,
    match: (p) => p.startsWith("/integrations"),
    visible: ({ isSuperAdmin, hasPermission }) => !isSuperAdmin && hasPermission("company", "configure"),
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
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const breadcrumbLabel = useBreadcrumbLabel(location.pathname);
  const isSuperAdmin = user?.is_super_admin ?? false;
  const aiChatbotEnabled = user?.ai_chatbot_enabled ?? false;
  const visibleNavItems = NAV_ITEMS.filter((item) => item.visible({ isSuperAdmin, hasPermission, aiChatbotEnabled }));

  async function handleLogout() {
    setMenuAnchor(null);
    try {
      await logoutRequest();
    } finally {
      clearSession();
      navigate("/login", { replace: true });
    }
  }

  const navList = (
    <>
      <Toolbar sx={{ px: 3, gap: 1.25 }}>
        <Box
          sx={{
            width: 32,
            height: 32,
            borderRadius: 1.5,
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "linear-gradient(135deg, #4F46E5 0%, #0EA5E9 100%)",
          }}
        >
          <DashboardIcon sx={{ fontSize: 18, color: "#fff" }} />
        </Box>
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
              onClick={() => setMobileNavOpen(false)}
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
    </>
  );

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", overflowX: "hidden" }}>
      <Drawer
        variant={isMobile ? "temporary" : "permanent"}
        open={isMobile ? mobileNavOpen : true}
        onClose={() => setMobileNavOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          width: isMobile ? 0 : DRAWER_WIDTH,
          flexShrink: 0,
          "& .MuiDrawer-paper": {
            width: DRAWER_WIDTH,
            boxSizing: "border-box",
            // "background" (not "bgcolor") since sidebar.background is a
            // gradient — bgcolor only ever maps to background-color, which
            // silently ignores a gradient value. Must be a theme-callback,
            // not a "sidebar.background" path string: sx only resolves
            // dotted palette-path strings for specially-recognized keys
            // (color, bgcolor, borderColor, ...) — "background" isn't one of
            // them, so a string here is passed straight through as a
            // (invalid) literal CSS value instead of being looked up.
            background: (theme) => theme.palette.sidebar.background,
            color: "sidebar.text",
            border: "none",
          },
        }}
      >
        {navList}
      </Drawer>

      <Box sx={{ flexGrow: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <AppBar
          position="sticky"
          color="transparent"
          elevation={0}
          sx={{ bgcolor: "background.paper", borderBottom: "1px solid", borderColor: "divider" }}
        >
          <Toolbar sx={{ justifyContent: "space-between", gap: 1 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 1, minWidth: 0 }}>
              <IconButton
                onClick={() => setMobileNavOpen(true)}
                size="small"
                aria-label="Open navigation menu"
                sx={{ display: { xs: "inline-flex", md: "none" } }}
              >
                <MenuIcon fontSize="small" />
              </IconButton>
              <Breadcrumbs sx={{ display: { xs: "none", sm: "flex" } }}>
                <Link component={RouterLink} to="/" underline="hover" color="text.secondary">
                  Home
                </Link>
                <Typography color="text.primary">{breadcrumbLabel}</Typography>
              </Breadcrumbs>
              <Typography color="text.primary" sx={{ display: { xs: "block", sm: "none" } }} noWrap>
                {breadcrumbLabel}
              </Typography>
            </Box>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <IconButton onClick={toggleMode} size="small" aria-label="Toggle color mode">
                {mode === "dark" ? <Brightness7Icon fontSize="small" /> : <Brightness4Icon fontSize="small" />}
              </IconButton>
              {!isSuperAdmin && <NotificationBell />}
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

        <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: { xs: 2, sm: 3, md: 4 } }}>
          <Outlet />
        </Box>
      </Box>
    </Box>
  );
}
