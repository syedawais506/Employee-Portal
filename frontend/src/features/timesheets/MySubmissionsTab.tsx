import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Chip,
  Paper,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from "@mui/material";

import { listMyTimesheetSubmissions, type TimesheetBucket } from "@/api/timesheets";
import { PageHeader } from "@/components/PageHeader";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  submitted: "info",
  manager_approved: "info",
  approved: "success",
  rejected: "error",
};

const STATUS_LABEL: Record<string, string> = {
  submitted: "Awaiting manager approval",
  manager_approved: "Awaiting finance sign-off",
  approved: "Approved",
  rejected: "Rejected",
};

export function MySubmissionsTab() {
  const [bucket, setBucket] = useState<TimesheetBucket>("pending");

  const { data: submissions } = useQuery({
    queryKey: ["timesheets", "submissions", "mine", bucket],
    queryFn: () => listMyTimesheetSubmissions(bucket),
  });

  return (
    <>
      <PageHeader title="My Submissions" subtitle="What you've submitted, and where it stands." />

      <Tabs value={bucket} onChange={(_, value) => setBucket(value)} sx={{ mb: 2 }}>
        <Tab value="pending" label="Pending" />
        <Tab value="approved" label="Approved" />
        <Tab value="rejected" label="Rejected" />
      </Tabs>

      <Paper variant="outlined">
        <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Period</TableCell>
              <TableCell>Total hours</TableCell>
              <TableCell>Submitted</TableCell>
              <TableCell>Status</TableCell>
              {bucket === "rejected" && <TableCell>Reason</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {(submissions ?? []).map((submission) => (
              <TableRow key={submission.id} hover>
                <TableCell>
                  {submission.period_start} – {submission.period_end}
                </TableCell>
                <TableCell>{submission.total_hours}</TableCell>
                <TableCell>{new Date(submission.submitted_at).toLocaleDateString()}</TableCell>
                <TableCell>
                  <Chip
                    label={STATUS_LABEL[submission.status] ?? submission.status}
                    size="small"
                    color={STATUS_COLOR[submission.status]}
                  />
                </TableCell>
                {bucket === "rejected" && <TableCell>{submission.rejection_reason ?? "—"}</TableCell>}
              </TableRow>
            ))}
            {(submissions ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={bucket === "rejected" ? 5 : 4} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">Nothing here yet.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        </TableContainer>
      </Paper>

      {bucket === "rejected" && (submissions ?? []).length > 0 && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Open the Drafts tab to fix rejected entries, then resubmit them from there.
        </Alert>
      )}
    </>
  );
}
