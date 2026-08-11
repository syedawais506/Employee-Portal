import { useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, Grid, MenuItem, TextField } from "@mui/material";

import type { Department } from "@/types";

interface DepartmentExportDialogProps {
  open: boolean;
  departments: Department[];
  exporting?: boolean;
  onClose: () => void;
  onExport: (filters: {
    search: string;
    parentDepartmentId: string;
    createdFrom: string;
    createdTo: string;
  }) => void;
}

const EMPTY_FILTERS = { search: "", parentDepartmentId: "", createdFrom: "", createdTo: "" };

export function DepartmentExportDialog({ open, departments, exporting, onClose, onExport }: DepartmentExportDialogProps) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  function update<K extends keyof typeof EMPTY_FILTERS>(key: K, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="xs" fullWidth>
      <DialogTitle>Export Departments</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12}>
            <TextField
              label="Search by name"
              fullWidth
              size="small"
              value={filters.search}
              onChange={(e) => update("search", e.target.value)}
            />
          </Grid>
          <Grid item xs={12}>
            <TextField
              select
              label="Parent department"
              fullWidth
              size="small"
              value={filters.parentDepartmentId}
              onChange={(e) => update("parentDepartmentId", e.target.value)}
            >
              <MenuItem value="">All departments</MenuItem>
              {departments.map((dept) => (
                <MenuItem key={dept.id} value={dept.id}>
                  {dept.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={6}>
            <TextField
              type="date"
              label="Created from"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={filters.createdFrom}
              onChange={(e) => update("createdFrom", e.target.value)}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              type="date"
              label="Created to"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={filters.createdTo}
              onChange={(e) => update("createdTo", e.target.value)}
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
