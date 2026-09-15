import { Box, CircularProgress } from "@mui/material";

export function RouteLoadingFallback() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "40vh" }}>
      <CircularProgress />
    </Box>
  );
}
