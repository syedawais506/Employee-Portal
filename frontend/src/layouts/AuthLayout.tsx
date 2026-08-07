import { Outlet } from "react-router-dom";
import { Box, Paper, Stack, Typography } from "@mui/material";

export function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        bgcolor: "background.default",
        px: 2,
      }}
    >
      <Paper elevation={0} sx={{ width: "100%", maxWidth: 420, p: 4, border: "1px solid", borderColor: "divider" }}>
        <Stack spacing={0.5} sx={{ mb: 3 }}>
          <Typography variant="h2">Employee Portal</Typography>
          <Typography variant="body2" color="text.secondary">
            Multi-tenant workforce management
          </Typography>
        </Stack>
        <Outlet />
      </Paper>
    </Box>
  );
}
