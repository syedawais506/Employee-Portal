import { createTheme } from "@mui/material/styles";

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

  return createTheme({
    palette: {
      mode,
      primary: { main: "#4F46E5" },
      secondary: { main: "#0EA5E9" },
      background: {
        default: isDark ? "#0F1117" : "#F7F8FA",
        paper: isDark ? "#171A23" : "#FFFFFF",
      },
      sidebar: {
        background: isDark ? "#12141C" : "#111827",
        text: "#E5E7EB",
      },
      success: { main: "#16A34A" },
      warning: { main: "#D97706" },
      error: { main: "#DC2626" },
    },
    shape: { borderRadius: 10 },
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
      h1: { fontSize: "2rem", fontWeight: 600 },
      h2: { fontSize: "1.5rem", fontWeight: 600 },
      h3: { fontSize: "1.25rem", fontWeight: 600 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    components: {
      MuiButton: {
        styleOverrides: { root: { borderRadius: 8 } },
      },
      MuiPaper: {
        styleOverrides: { root: { backgroundImage: "none" } },
      },
      MuiTableCell: {
        styleOverrides: { head: { fontWeight: 600 } },
      },
    },
  });
}
