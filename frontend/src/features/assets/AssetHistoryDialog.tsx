import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import { getAssetHistory } from "@/api/assets";
import type { Asset } from "@/types";

interface AssetHistoryDialogProps {
  open: boolean;
  asset: Asset | null;
  onClose: () => void;
}

export function AssetHistoryDialog({ open, asset, onClose }: AssetHistoryDialogProps) {
  const { data: history } = useQuery({
    queryKey: ["assets", "history", asset?.id],
    queryFn: () => getAssetHistory(asset!.id),
    enabled: open && Boolean(asset),
  });

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>History — {asset?.asset_tag}</DialogTitle>
      <DialogContent>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Employee</TableCell>
                <TableCell>Assigned</TableCell>
                <TableCell>Returned</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {(history ?? []).map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell>{entry.employee_name}</TableCell>
                  <TableCell>{new Date(entry.assigned_at).toLocaleDateString()}</TableCell>
                  <TableCell>{entry.returned_at ? new Date(entry.returned_at).toLocaleDateString() : "—"}</TableCell>
                </TableRow>
              ))}
              {(history ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={3} align="center" sx={{ py: 3 }}>
                    <Typography color="text.secondary">No assignment history yet.</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
