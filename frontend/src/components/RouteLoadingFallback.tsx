import { Box } from "@mui/material";

import { LogoMark } from "@/components/LogoMark";

export function RouteLoadingFallback() {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "40vh" }}>
      <LogoMark size={48} spinning />
    </Box>
  );
}
