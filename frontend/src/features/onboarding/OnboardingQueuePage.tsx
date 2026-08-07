import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Chip, Paper, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";

import { getOnboardingQueue } from "@/api/onboarding";

const STATUS_LABEL: Record<string, string> = {
  invited: "Invited",
  submitted: "Submitted",
  hr_approved: "HR Approved",
};

const STATUS_COLOR: Record<string, "default" | "info" | "warning"> = {
  invited: "default",
  submitted: "info",
  hr_approved: "warning",
};

export function OnboardingQueuePage() {
  const navigate = useNavigate();
  const { data: queue, isLoading } = useQuery({ queryKey: ["onboarding-queue"], queryFn: getOnboardingQueue });

  return (
    <Paper variant="outlined">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Employee Code</TableCell>
            <TableCell>Name</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(queue ?? []).map((entry) => (
            <TableRow key={entry.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/onboarding/review/${entry.id}`)}>
              <TableCell>{entry.employee_code}</TableCell>
              <TableCell>
                {entry.first_name} {entry.last_name}
              </TableCell>
              <TableCell>
                <Chip label={STATUS_LABEL[entry.onboarding_status]} size="small" color={STATUS_COLOR[entry.onboarding_status]} />
              </TableCell>
            </TableRow>
          ))}
          {!isLoading && (queue ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={3} align="center" sx={{ py: 4 }}>
                <Typography color="text.secondary">Nobody is currently in onboarding.</Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </Paper>
  );
}
