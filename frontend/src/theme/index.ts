import { alpha, createTheme } from "@mui/material/styles";

declare module "@mui/material/styles" {
  interface Palette {
    sidebar: { background: string; text: string };
  }
  interface PaletteOptions {
    sidebar?: { background: string; text: string };
  }
}

export function buildTheme(mode: "light" | "dark") {
  const isDark = mode === "dark";

  const primaryMain = "#4F46E5";
  const secondaryMain = "#0EA5E9";

  return createTheme({
    palette: {
      mode,
      primary: { main: primaryMain, light: "#8280EE", dark: "#3730A3" },
      secondary: { main: secondaryMain },
      background: {
        default: isDark ? "#0B0D12" : "#F6F7FB",
        paper: isDark ? "#161923" : "#FFFFFF",
      },
      // A gradient, not a flat color — consumed via sx={{ background: ... }}
      // (not "bgcolor", which only maps to background-color and would
      // silently drop the gradient).
      sidebar: {
        background: isDark
          ? "linear-gradient(180deg, #12141C 0%, #0B0D12 100%)"
          : "linear-gradient(180deg, #171B2B 0%, #111325 100%)",
        text: "#E5E7EB",
      },
      success: { main: "#16A34A" },
      warning: { main: "#D97706" },
      error: { main: "#DC2626" },
      info: { main: secondaryMain },
      divider: isDark ? alpha("#FFFFFF", 0.08) : alpha("#0F172A", 0.08),
    },
    shape: { borderRadius: 12 },
    typography: {
      fontFamily: [
        "Inter",
        "-apple-system",
        "BlinkMacSystemFont",
        "Segoe UI",
        "Roboto",
        "Helvetica Neue",
        "Arial",
        "sans-serif",
      ].join(","),
      h1: { fontSize: "1.85rem", fontWeight: 700, letterSpacing: "-0.01em" },
      h2: { fontSize: "1.4rem", fontWeight: 700, letterSpacing: "-0.01em" },
      h3: { fontSize: "1.1rem", fontWeight: 600 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            // A very subtle radial tint in the corners, not a wash over the
            // whole page — same trick either theme, just dimmer in light
            // mode so it doesn't compete with card content.
            backgroundImage: `radial-gradient(1200px circle at 0% 0%, ${alpha(primaryMain, isDark ? 0.1 : 0.06)}, transparent 40%),
               radial-gradient(1000px circle at 100% 0%, ${alpha(secondaryMain, isDark ? 0.08 : 0.05)}, transparent 40%)`,
            backgroundAttachment: "fixed",
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: { borderRadius: 8, boxShadow: "none" },
          contained: {
            boxShadow: `0 1px 2px ${alpha("#0F172A", 0.16)}`,
            "&:hover": { boxShadow: `0 4px 12px ${alpha(primaryMain, 0.28)}` },
          },
        },
      },
      MuiPaper: {
        styleOverrides: { root: { backgroundImage: "none" } },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            border: `1px solid ${isDark ? alpha("#FFFFFF", 0.08) : alpha("#0F172A", 0.07)}`,
            boxShadow: isDark ? "none" : `0 1px 2px ${alpha("#0F172A", 0.04)}`,
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: {
            fontWeight: 700,
            fontSize: "0.75rem",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            color: isDark ? alpha("#FFFFFF", 0.6) : alpha("#0F172A", 0.55),
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 600 },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: { borderRadius: 10 },
        },
      },
    },
  });
}
