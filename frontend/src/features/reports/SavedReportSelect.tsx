import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DownloadIcon from "@mui/icons-material/Download";
import { IconButton, MenuItem, Stack, TextField } from "@mui/material";

import type { SavedReport } from "@/types";

interface SavedReportSelectProps {
  savedReports: SavedReport[];
  selectedId: string;
  canConfigure: boolean;
  onSelect: (report: SavedReport) => void;
  onExport: (report: SavedReport) => void;
  onDelete: (report: SavedReport) => void;
}

export function SavedReportSelect({
  savedReports,
  selectedId,
  canConfigure,
  onSelect,
  onExport,
  onDelete,
}: SavedReportSelectProps) {
  const selected = savedReports.find((report) => report.id === selectedId) ?? null;

  return (
    <Stack direction="row" spacing={0.5} alignItems="center">
      <TextField
        select
        label="Saved Report"
        fullWidth
        size="small"
        value={selectedId}
        onChange={(event) => {
          const report = savedReports.find((r) => r.id === event.target.value);
          if (report) onSelect(report);
        }}
      >
        <MenuItem value="">
          <em>None</em>
        </MenuItem>
        {savedReports.map((report) => (
          <MenuItem key={report.id} value={report.id}>
            {report.name}
          </MenuItem>
        ))}
      </TextField>
      {selected && (
        <>
          <IconButton size="small" onClick={() => onExport(selected)} title="Export this saved report">
            <DownloadIcon fontSize="small" />
          </IconButton>
          {canConfigure && (
            <IconButton size="small" onClick={() => onDelete(selected)} title="Delete this saved report">
              <DeleteOutlineIcon fontSize="small" />
            </IconButton>
          )}
        </>
      )}
    </Stack>
  );
}
