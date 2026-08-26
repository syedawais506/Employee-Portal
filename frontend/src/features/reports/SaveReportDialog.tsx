import { useState } from "react";
import { Button, Dialog, DialogActions, DialogContent, DialogTitle, TextField } from "@mui/material";

interface SaveReportDialogProps {
  open: boolean;
  loading?: boolean;
  onClose: () => void;
  onConfirm: (name: string) => void;
}

export function SaveReportDialog({ open, loading, onClose, onConfirm }: SaveReportDialogProps) {
  const [name, setName] = useState("");

  function handleClose() {
    setName("");
    onClose();
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle>Save Report</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          label="Report name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          sx={{ mt: 1 }}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose}>Cancel</Button>
        <Button variant="contained" disabled={!name.trim() || loading} onClick={() => onConfirm(name.trim())}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}
