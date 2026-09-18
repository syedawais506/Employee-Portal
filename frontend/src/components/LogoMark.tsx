import { Box } from "@mui/material";
import DashboardIcon from "@mui/icons-material/Dashboard";

interface LogoMarkProps {
  size?: number;
  /** Spins fast — use for an actual loading/buffering indicator. */
  spinning?: boolean;
}

/**
 * The app's gradient logo badge. A flat 2D rotation, deliberately — a 3D
 * cube treatment was tried and didn't land, this simple spin is the one
 * that did. Two speeds: a slow, subtle idle spin as a brand touch wherever
 * it's shown decoratively (sidebar, login panel), and a fast spin when
 * used as an actual loading indicator (see RouteLoadingFallback).
 */
export function LogoMark({ size = 32, spinning = false }: LogoMarkProps) {
  return (
    <Box
      sx={{
        width: size,
        height: size,
        borderRadius: 1.5,
        flexShrink: 0,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #4F46E5 0%, #0EA5E9 100%)",
        boxShadow: "0 2px 10px rgba(79, 70, 229, 0.35)",
        animation: `logo-mark-spin ${spinning ? "1s" : "9s"} linear infinite`,
        "@keyframes logo-mark-spin": {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
      }}
    >
      <DashboardIcon sx={{ fontSize: size * 0.56, color: "#fff" }} />
    </Box>
  );
}
