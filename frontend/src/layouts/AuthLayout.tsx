import { useMemo } from "react";
import { Outlet } from "react-router-dom";
import { Box, Paper, Stack, ThemeProvider, Typography } from "@mui/material";
import { alpha } from "@mui/material/styles";
import EventAvailableIcon from "@mui/icons-material/EventAvailable";
import SecurityIcon from "@mui/icons-material/Security";
import AccessTimeIcon from "@mui/icons-material/AccessTime";

import { LogoMark } from "@/components/LogoMark";
import { buildTheme } from "@/theme";

const HIGHLIGHTS = [
  { icon: <EventAvailableIcon fontSize="small" />, text: "Leave, timesheets & attendance in one place" },
  { icon: <SecurityIcon fontSize="small" />, text: "Role-based permissions with a full audit trail" },
  { icon: <AccessTimeIcon fontSize="small" />, text: "Live approvals — no more chasing email threads" },
];

// Fixed positions/sizes/delays for the twinkle accents — plain numbers, not
// Math.random(), so this renders identically every time rather than
// reshuffling on every remount.
const SPARKLES = [
  { top: "18%", left: "62%", size: 3, delay: "0s", duration: "3.2s" },
  { top: "30%", left: "85%", size: 2, delay: "0.6s", duration: "2.6s" },
  { top: "68%", left: "78%", size: 4, delay: "1.4s", duration: "3.6s" },
  { top: "82%", left: "58%", size: 2, delay: "2.1s", duration: "2.9s" },
  { top: "12%", left: "40%", size: 3, delay: "1.8s", duration: "3.1s" },
  { top: "48%", left: "92%", size: 2, delay: "0.9s", duration: "2.4s" },
];

/**
 * The whole page (both panels) shares one animated aurora backdrop rather
 * than a flat brand-colored panel next to a flat white one — deliberately
 * decoupled from the app's own light/dark toggle (see docs), since a login
 * screen is a one-time, high-impact moment where a fixed dramatic look
 * wins over strict theme consistency. The card floating on top is
 * glassmorphic (semi-transparent + backdrop-blur) specifically so that
 * backdrop keeps showing through it, tying the whole page together as one
 * scene instead of two flat blocks side by side.
 */
export function AuthLayout() {
  // The form itself always renders with dark-mode-correct MUI defaults
  // (text color, Checkbox, Link, Alert, ...) regardless of the app's own
  // light/dark toggle — the glass card's background is dark either way, so
  // its contents must be too, rather than manually overriding a dozen MUI
  // class selectors one at a time.
  const authFormTheme = useMemo(() => buildTheme("dark"), []);

  return (
    <Box sx={{ minHeight: "100vh", position: "relative", overflow: "hidden", bgcolor: "#0B0B1A" }}>
      <Box
        sx={{
          position: "absolute",
          inset: "-10%",
          backgroundImage:
            "linear-gradient(115deg, #1E1B4B 0%, #4F46E5 22%, #7C3AED 45%, #0EA5E9 68%, #1E1B4B 100%)",
          backgroundSize: "300% 300%",
          filter: "blur(90px) saturate(140%)",
          opacity: 0.75,
          animation: "auth-aurora-shift 22s ease-in-out infinite",
          "@keyframes auth-aurora-shift": {
            "0%": { backgroundPosition: "0% 40%" },
            "50%": { backgroundPosition: "100% 60%" },
            "100%": { backgroundPosition: "0% 40%" },
          },
        }}
      />
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          opacity: 0.35,
          backgroundImage: `radial-gradient(${alpha("#FFFFFF", 0.12)} 1px, transparent 1px)`,
          backgroundSize: "26px 26px",
        }}
      />
      {SPARKLES.map((s, i) => (
        <Box
          key={i}
          sx={{
            position: "absolute",
            top: s.top,
            left: s.left,
            width: s.size,
            height: s.size,
            borderRadius: "50%",
            bgcolor: "#fff",
            boxShadow: "0 0 6px 1px rgba(255,255,255,0.8)",
            animation: `auth-sparkle-twinkle ${s.duration} ease-in-out infinite`,
            animationDelay: s.delay,
            "@keyframes auth-sparkle-twinkle": {
              "0%, 100%": { opacity: 0, transform: "scale(0.6)" },
              "50%": { opacity: 1, transform: "scale(1.3)" },
            },
          }}
        />
      ))}

      <Box
        sx={{
          position: "relative",
          zIndex: 1,
          minHeight: "100vh",
          display: "flex",
          alignItems: "center",
          justifyContent: { xs: "center", md: "space-between" },
          gap: 4,
          px: { xs: 2, md: 8 },
          py: 4,
        }}
      >
        <Stack spacing={4} sx={{ display: { xs: "none", md: "flex" }, maxWidth: 480, color: "#fff" }}>
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Box
              sx={{
                position: "relative",
                width: 36,
                height: 36,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                "&::before": {
                  content: '""',
                  position: "absolute",
                  inset: -10,
                  borderRadius: "50%",
                  background: "radial-gradient(circle, rgba(129,140,248,0.55) 0%, transparent 70%)",
                  animation: "auth-logo-glow 2.6s ease-in-out infinite",
                },
                "@keyframes auth-logo-glow": {
                  "0%, 100%": { opacity: 0.5, transform: "scale(0.9)" },
                  "50%": { opacity: 1, transform: "scale(1.15)" },
                },
              }}
            >
              <LogoMark size={36} />
            </Box>
            <Typography
              variant="h2"
              sx={{
                position: "relative",
                backgroundImage: "linear-gradient(100deg, #FFFFFF 40%, #C7D2FE 50%, #FFFFFF 60%)",
                backgroundSize: "220% 100%",
                backgroundClip: "text",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                animation: "auth-text-shimmer 4s linear infinite",
                "@keyframes auth-text-shimmer": {
                  from: { backgroundPosition: "150% 0" },
                  to: { backgroundPosition: "-50% 0" },
                },
              }}
            >
              Employee Portal
            </Typography>
          </Stack>

          <Typography variant="h1" sx={{ color: "inherit", fontSize: "2.3rem" }}>
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
                    bgcolor: alpha("#FFFFFF", 0.1),
                    boxShadow: `inset 0 0 0 1px ${alpha("#FFFFFF", 0.16)}`,
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

          <Typography variant="caption" sx={{ color: alpha("#FFFFFF", 0.4) }}>
            © {new Date().getFullYear()} Employee Portal
          </Typography>
        </Stack>

        <ThemeProvider theme={authFormTheme}>
          <Paper
            elevation={0}
            sx={{
              width: "100%",
              maxWidth: 420,
              p: 4,
              bgcolor: alpha("#0F1226", 0.55),
              backdropFilter: "blur(20px) saturate(160%)",
              border: `1px solid ${alpha("#FFFFFF", 0.14)}`,
              borderRadius: 3,
              boxShadow: `0 30px 80px ${alpha("#000000", 0.45)}, inset 0 1px 0 ${alpha("#FFFFFF", 0.08)}`,
              animation: "auth-card-in 550ms ease-out",
              "@keyframes auth-card-in": {
                from: { opacity: 0, transform: "translateY(14px) scale(0.98)" },
                to: { opacity: 1, transform: "translateY(0) scale(1)" },
              },
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
        </ThemeProvider>
      </Box>
    </Box>
  );
}
