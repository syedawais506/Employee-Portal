import { useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid, MenuItem, TextField } from "@mui/material";

import type { Client } from "@/types";

interface ProjectExportDialogProps {
  open: boolean;
  clients: Client[];
  exporting?: boolean;
  onClose: () => void;
  onExport: (filters: {
    status: string;
    clientId: string;
    isBillable: string;
    startDateFrom: string;
    startDateTo: string;
  }) => void;
}

const EMPTY_FILTERS = { status: "", clientId: "", isBillable: "", startDateFrom: "", startDateTo: "" };

export function ProjectExportDialog({ open, clients, exporting, onClose, onExport }: ProjectExportDialogProps) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  function update<K extends keyof typeof EMPTY_FILTERS>(key: K, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Export Projects</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={6}>
            <TextField
              select
              label="Status"
              fullWidth
              size="small"
              value={filters.status}
              onChange={(e) => update("status", e.target.value)}
            >
              <MenuItem value="">All statuses</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="on_hold">On hold</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="cancelled">Cancelled</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={6}>
            <TextField
              select
              label="Client"
              fullWidth
              size="small"
              value={filters.clientId}
              onChange={(e) => update("clientId", e.target.value)}
            >
              <MenuItem value="">All clients</MenuItem>
              {clients.map((client) => (
                <MenuItem key={client.id} value={client.id}>
                  {client.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12}>
            <TextField
              select
              label="Billable"
              fullWidth
              size="small"
              value={filters.isBillable}
              onChange={(e) => update("isBillable", e.target.value)}
            >
              <MenuItem value="">Both</MenuItem>
              <MenuItem value="true">Billable only</MenuItem>
              <MenuItem value="false">Non-billable only</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={6}>
            <TextField
              type="date"
              label="Starts from"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={filters.startDateFrom}
              onChange={(e) => update("startDateFrom", e.target.value)}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              type="date"
              label="Starts to"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={filters.startDateTo}
              onChange={(e) => update("startDateTo", e.target.value)}
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={exporting} onClick={() => onExport(filters)}>
          Export CSV
        </Button>
      </DialogActions>
    </Dialog>
  );
}
