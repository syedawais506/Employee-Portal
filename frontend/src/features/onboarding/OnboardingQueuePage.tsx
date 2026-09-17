import type { ReactElement } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Box, Chip, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow } from "@mui/material";
import { alpha } from "@mui/material/styles";
import HowToRegIcon from "@mui/icons-material/HowToReg";
import MarkEmailReadIcon from "@mui/icons-material/MarkEmailRead";
import PendingActionsIcon from "@mui/icons-material/PendingActions";

import { getOnboardingQueue } from "@/api/onboarding";
import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";

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

const STATUS_ICON: Record<string, ReactElement> = {
  invited: <MarkEmailReadIcon fontSize="small" />,
  submitted: <PendingActionsIcon fontSize="small" />,
  hr_approved: <HowToRegIcon fontSize="small" />,
};

function initials(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase();
}

export function OnboardingQueuePage() {
  const navigate = useNavigate();
  const { data: queue, isLoading } = useQuery({ queryKey: ["onboarding-queue"], queryFn: getOnboardingQueue });

  return (
    <Box>
      <PageHeader
        title="Onboarding"
        subtitle="New hires currently working through document upload and HR/Admin review."
      />
      <Paper variant="outlined">
        <TableContainer>
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
                <TableRow
                  key={entry.id}
                  hover
                  sx={{ cursor: "pointer" }}
                  onClick={() => navigate(`/onboarding/review/${entry.id}`)}
                >
                  <TableCell>{entry.employee_code}</TableCell>
                  <TableCell>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
                      <Box
                        sx={{
                          width: 30,
                          height: 30,
                          borderRadius: "50%",
                          flexShrink: 0,
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "0.7rem",
                          fontWeight: 700,
                          bgcolor: (theme) => alpha(theme.palette.primary.main, 0.14),
                          color: "primary.main",
                        }}
                      >
                        {initials(entry.first_name, entry.last_name)}
                      </Box>
                      <span>
                        {entry.first_name} {entry.last_name}
                      </span>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={STATUS_LABEL[entry.onboarding_status]}
                      size="small"
                      color={STATUS_COLOR[entry.onboarding_status]}
                      icon={STATUS_ICON[entry.onboarding_status]}
                    />
                  </TableCell>
                </TableRow>
              ))}
              {!isLoading && (queue ?? []).length === 0 && (
                <TableRow>
                  <TableCell colSpan={3}>
                    <EmptyState
                      title="Nobody is currently in onboarding"
                      description="New hires you invite will show up here while they upload documents and go through review."
                      icon={<HowToRegIcon fontSize="inherit" />}
                    />
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Paper>
    </Box>
  );
}
