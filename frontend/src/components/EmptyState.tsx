import type { ReactNode } from "react";
import { Box, Stack, Typography, useTheme } from "@mui/material";
import { alpha } from "@mui/material/styles";
import InboxIcon from "@mui/icons-material/Inbox";

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
  /** Shrinks padding/illustration for use inside a smaller card (e.g. a dashboard widget) rather than a full page. */
  compact?: boolean;
}

/**
 * A lightweight, theme-aware "nothing here yet" illustration — a soft
 * gradient badge behind an icon, rather than a bundled illustration asset
 * (keeps this dependency-free and automatically matches the active
 * primary/secondary colors in both light and dark mode).
 */
export function EmptyState({ title, description, icon, action, compact = false }: EmptyStateProps) {
  const theme = useTheme();

  return (
    <Stack
      alignItems="center"
      textAlign="center"
      spacing={compact ? 1 : 1.5}
      sx={{ py: compact ? 3 : 6, px: 2 }}
    >
      <Box
        sx={{
          width: compact ? 56 : 88,
          height: compact ? 56 : 88,
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.16)} 0%, ${alpha(
            theme.palette.secondary.main,
            0.12,
          )} 100%)`,
          color: theme.palette.primary.main,
        }}
      >
        <Box sx={{ fontSize: compact ? 26 : 40, display: "flex" }}>{icon ?? <InboxIcon fontSize="inherit" />}</Box>
      </Box>
      <Typography variant={compact ? "body2" : "h3"} sx={{ fontWeight: 600 }}>
        {title}
      </Typography>
      {description && (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 360 }}>
          {description}
        </Typography>
      )}
      {action}
    </Stack>
  );
}
