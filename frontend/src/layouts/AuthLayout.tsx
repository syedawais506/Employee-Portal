import { Outlet } from "react-router-dom";
import { Box, Paper, Stack, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import DashboardIcon from "@mui/icons-material/Dashboard";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";
import SecurityIcon from "@mui/icons-material/Security";
import AccessTimeIcon from "@mui/icons-material/AccessTime";

const HIGHLIGHTS = [
  { icon: <EventAvailableIcon fontSize="small" />, text: "Leave, timesheets & attendance in one place" },
  { icon: <SecurityIcon fontSize="small" />, text: "Role-based permissions with a full audit trail" },
  { icon: <AccessTimeIcon fontSize="small" />, text: "Live approvals — no more chasing email threads" },
];

export function AuthLayout() {
  return (
    <Box sx={{ minHeight: "100vh", display: "flex" }}>
      <Box
        sx={{
          display: { xs: "none", md: "flex" },
          flexDirection: "column",
          justifyContent: "space-between",
          width: "42%",
          maxWidth: 560,
          p: 6,
          color: "sidebar.text",
          // Theme-callback, not a "sidebar.background" path string — sx only
          // resolves dotted palette-path strings for specially-recognized
          // keys (color, bgcolor, ...); "background" isn't one of them.
          background: (theme) => theme.palette.sidebar.background,
          position: "relative",
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            backgroundImage: (theme) =>
              `radial-gradient(600px circle at 15% 15%, ${alpha(theme.palette.primary.main, 0.35)}, transparent 45%),
               radial-gradient(500px circle at 85% 85%, ${alpha(theme.palette.secondary.main, 0.25)}, transparent 45%)`,
          }}
        />
        <Stack direction="row" alignItems="center" spacing={1.25} sx={{ position: "relative" }}>
          <Box
            sx={{
              width: 36,
              height: 36,
              borderRadius: 1.5,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              background: "linear-gradient(135deg, #4F46E5 0%, #0EA5E9 100%)",
            }}
          >
            <DashboardIcon sx={{ fontSize: 20, color: "#fff" }} />
          </Box>
          <Typography variant="h2" sx={{ color: "inherit" }}>
            Employee Portal
          </Typography>
        </Stack>

        <Stack spacing={3} sx={{ position: "relative" }}>
          <Typography variant="h1" sx={{ color: "inherit", fontSize: "2.1rem" }}>
            Everything HR needs, in one calm workspace.
          </Typography>
          <Stack spacing={1.75}>
            {HIGHLIGHTS.map((item) => (
              <Stack key={item.text} direction="row" spacing={1.5} alignItems="center">
                <Box
                  sx={{
                    width: 32,
                    height: 32,
                    borderRadius: "50%",
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    bgcolor: alpha("#FFFFFF", 0.08),
                    color: "inherit",
                  }}
                >
                  {item.icon}
                </Box>
                <Typography variant="body2" sx={{ color: alpha("#FFFFFF", 0.85) }}>
                  {item.text}
                </Typography>
              </Stack>
            ))}
          </Stack>
        </Stack>

        <Typography variant="caption" sx={{ color: alpha("#FFFFFF", 0.4), position: "relative" }}>
          © {new Date().getFullYear()} Employee Portal
        </Typography>
      </Box>

      <Box
        sx={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          bgcolor: "background.default",
          px: 2,
        }}
      >
        <Paper
          elevation={0}
          sx={{
            width: "100%",
            maxWidth: 420,
            p: 4,
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          <Stack spacing={0.5} sx={{ mb: 3, display: { xs: "flex", md: "none" } }}>
            <Typography variant="h2">Employee Portal</Typography>
            <Typography variant="body2" color="text.secondary">
              Multi-tenant workforce management
            </Typography>
          </Stack>
          <Stack spacing={0.5} sx={{ mb: 3, display: { xs: "none", md: "flex" } }}>
            <Typography variant="h2">Welcome back</Typography>
            <Typography variant="body2" color="text.secondary">
              Sign in to continue to your workspace.
            </Typography>
          </Stack>
          <Outlet />
        </Paper>
      </Box>
    </Box>
  );
}
