import { useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, TextField } from "@mui/material";

import type { EmployeeSummary } from "@/types";

interface AssignAssetDialogProps {
  open: boolean;
  employees: EmployeeSummary[];
  loading?: boolean;
  onClose: () => void;
  onConfirm: (employeeId: string) => void;
}

export function AssignAssetDialog({ open, employees, loading, onClose, onConfirm }: AssignAssetDialogProps) {
  const [employeeId, setEmployeeId] = useState("");

  function handleClose() {
    setEmployeeId("");
    onClose();
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>Assign Asset</DialogTitle>
      <DialogContent>
        <TextField
          select
          label="Employee"
          fullWidth
          value={employeeId}
          onChange={(event) => setEmployeeId(event.target.value)}
          sx={{ mt: 1 }}
        >
          {employees.map((employee) => (
            <MenuItem key={employee.id} value={employee.id}>
              {employee.first_name} {employee.last_name}
            </MenuItem>
          ))}
        </TextField>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" disabled={!employeeId || loading} onClick={() => onConfirm(employeeId)}>
          Assign
        </Button>
      </DialogActions>
    </Dialog>
  );
}
