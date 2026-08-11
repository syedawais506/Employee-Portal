import { useState } from "react";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  TextField,
} from "@mui/material";

import { EMPLOYEE_LOCATIONS, type Department, type EmployeeSummary } from "@/types";

interface EmployeeExportDialogProps {
  open: boolean;
  departments: Department[];
  managers: EmployeeSummary[];
  exporting?: boolean;
  onClose: () => void;
  onExport: (filters: {
    search: string;
    departmentId: string;
    status: string;
    managerId: string;
    employmentType: string;
    location: string;
    joiningDateFrom: string;
    joiningDateTo: string;
  }) => void;
}

const EMPTY_FILTERS = {
  search: "",
  departmentId: "",
  status: "",
  managerId: "",
  employmentType: "",
  location: "",
  joiningDateFrom: "",
  joiningDateTo: "",
};

export function EmployeeExportDialog({
  open,
  departments,
  managers,
  exporting,
  onClose,
  onExport,
}: EmployeeExportDialogProps) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  function update<K extends keyof typeof EMPTY_FILTERS>(key: K, value: string) {
    setFilters((prev) => ({ ...prev, [key]: value }));
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Export Employees</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12}>
            <TextField
              label="Search by name or code"
              fullWidth
              size="small"
              value={filters.search}
              onChange={(e) => update("search", e.target.value)}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              select
              label="Department"
              fullWidth
              size="small"
              value={filters.departmentId}
              onChange={(e) => update("departmentId", e.target.value)}
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
              select
              label="Status"
              fullWidth
              size="small"
              value={filters.status}
              onChange={(e) => update("status", e.target.value)}
            >
              <MenuItem value="">All statuses</MenuItem>
              <MenuItem value="active">Active</MenuItem>
              <MenuItem value="on_leave">On leave</MenuItem>
              <MenuItem value="exited">Exited</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={6}>
            <TextField
              select
              label="Employment type"
              fullWidth
              size="small"
              value={filters.employmentType}
              onChange={(e) => update("employmentType", e.target.value)}
            >
              <MenuItem value="">All types</MenuItem>
              <MenuItem value="full_time">Full time</MenuItem>
              <MenuItem value="part_time">Part time</MenuItem>
              <MenuItem value="contract">Contract</MenuItem>
              <MenuItem value="intern">Intern</MenuItem>
            </TextField>
          </Grid>
          <Grid item xs={6}>
            <TextField
              select
              label="Location"
              fullWidth
              size="small"
              value={filters.location}
              onChange={(e) => update("location", e.target.value)}
            >
              <MenuItem value="">All locations</MenuItem>
              {EMPLOYEE_LOCATIONS.map((location) => (
                <MenuItem key={location} value={location}>
                  {location}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12}>
            <TextField
              select
              label="Manager"
              fullWidth
              size="small"
              value={filters.managerId}
              onChange={(e) => update("managerId", e.target.value)}
            >
              <MenuItem value="">All managers</MenuItem>
              {managers.map((m) => (
                <MenuItem key={m.id} value={m.id}>
                  {m.first_name} {m.last_name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={6}>
            <TextField
              type="date"
              label="Joined from"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={filters.joiningDateFrom}
              onChange={(e) => update("joiningDateFrom", e.target.value)}
            />
          </Grid>
          <Grid item xs={6}>
            <TextField
              type="date"
              label="Joined to"
              fullWidth
              size="small"
              InputLabelProps={{ shrink: true }}
              value={filters.joiningDateTo}
              onChange={(e) => update("joiningDateTo", e.target.value)}
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
