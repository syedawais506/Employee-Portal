import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DownloadIcon from "@mui/icons-material/Download";
import { IconButton, List, ListItemButton, ListItemText, Paper, Typography } from "@mui/material";

import { REPORT_MODULES } from "@/features/reports/reportModules";
import type { SavedReport } from "@/types";

interface SavedReportsListProps {
  savedReports: SavedReport[];
  canConfigure: boolean;
  onRun: (report: SavedReport) => void;
  onExport: (report: SavedReport) => void;
  onDelete: (report: SavedReport) => void;
}

function moduleLabel(module: string): string {
  return REPORT_MODULES.find((m) => m.value === module)?.label ?? module;
}

export function SavedReportsList({ savedReports, canConfigure, onRun, onExport, onDelete }: SavedReportsListProps) {
  return (
    <Paper variant="outlined">
      <List dense>
        {savedReports.map((report) => (
          <ListItemButton
            key={report.id}
            onClick={() => onRun(report)}
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            <ListItemText primary={report.name} secondary={moduleLabel(report.module)} sx={{ flexGrow: 1 }} />
            <IconButton
              size="small"
              onClick={(event) => {
                event.stopPropagation();
                onExport(report);
              }}
            >
              <DownloadIcon fontSize="small" />
            </IconButton>
            {canConfigure && (
              <IconButton
                size="small"
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(report);
                }}
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            )}
          </ListItemButton>
        ))}
        {savedReports.length === 0 && (
          <Typography color="text.secondary" variant="body2" sx={{ p: 2 }}>
            No saved reports yet.
          </Typography>
        )}
      </List>
    </Paper>
  );
}
