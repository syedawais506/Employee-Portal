import { useQuery } from "@tanstack/react-query";
import { Chip, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import { listMyAssets } from "@/api/assets";
import { PageHeader } from "@/components/PageHeader";

export function MyAssetsTab() {
  const { data: assignments } = useQuery({ queryKey: ["assets", "mine"], queryFn: listMyAssets });

  return (
    <>
      <PageHeader title="My Assets" subtitle="Equipment currently or previously assigned to you." />
      <Paper variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Asset</TableCell>
              <TableCell>Tag</TableCell>
              <TableCell>Assigned</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(assignments ?? []).map((assignment) => (
              <TableRow key={assignment.id} hover>
                <TableCell>{assignment.asset_name}</TableCell>
                <TableCell>{assignment.asset_tag}</TableCell>
                <TableCell>{new Date(assignment.assigned_at).toLocaleDateString()}</TableCell>
                <TableCell>
                  <Chip
                    label={assignment.returned_at ? "Returned" : "In use"}
                    size="small"
                    color={assignment.returned_at ? "default" : "success"}
                  />
                </TableCell>
              </TableRow>
            ))}
            {(assignments ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">Nothing has been assigned to you yet.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>
    </>
  );
}
