import { Alert, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import type { ReportPreview } from "@/types";

interface ReportPreviewTableProps {
  preview: ReportPreview | null;
}

export function ReportPreviewTable({ preview }: ReportPreviewTableProps) {
  if (!preview) {
    return (
      <Paper variant="outlined" sx={{ p: 4, textAlign: "center" }}>
        <Typography color="text.secondary">Choose a module and click Preview to see results here.</Typography>
      </Paper>
    );
  }

  return (
    <>
      {preview.truncated && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Showing the first {preview.rows.length} of {preview.total} rows — export the CSV for the full set.
        </Alert>
      )}
      <Paper variant="outlined" sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              {preview.header.map((column) => (
                <TableCell key={column}>{column}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {preview.rows.map((row, rowIndex) => (
              <TableRow key={rowIndex} hover>
                {row.map((cell, cellIndex) => (
                  <TableCell key={cellIndex}>{cell}</TableCell>
                ))}
              </TableRow>
            ))}
            {preview.rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={preview.header.length} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No rows match these filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>
    </>
  );
}
