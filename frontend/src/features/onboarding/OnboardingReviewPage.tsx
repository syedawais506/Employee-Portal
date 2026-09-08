import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CheckIcon from "@mui/icons-material/Check";
import CloseIcon from "@mui/icons-material/Close";
import DownloadIcon from "@mui/icons-material/Download";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { getEmployee } from "@/api/employees";
import {
  adminApproveOnboarding,
  getDocumentDownloadUrl,
  hrApproveOnboarding,
  listEmployeeDocuments,
  reviewEmployeeDocument,
} from "@/api/onboarding";
import { PageHeader } from "@/components/PageHeader";
import { PermissionGate } from "@/components/PermissionGate";
import type { EmployeeDocument } from "@/types";

const STATUS_COLOR: Record<string, "success" | "error" | "default"> = {
  approved: "success",
  rejected: "error",
  pending: "default",
};

export function OnboardingReviewPage() {
  const { employeeId } = useParams<{ employeeId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [rejecting, setRejecting] = useState<EmployeeDocument | null>(null);
  const [rejectNotes, setRejectNotes] = useState("");
  const [approving, setApproving] = useState<EmployeeDocument | null>(null);
  const [approveExpiryDate, setApproveExpiryDate] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: employee } = useQuery({
    queryKey: ["employees", employeeId],
    queryFn: () => getEmployee(employeeId as string),
    enabled: Boolean(employeeId),
  });

  const { data: documents, isLoading } = useQuery({
    queryKey: ["employee-documents", employeeId],
    queryFn: () => listEmployeeDocuments(employeeId as string),
    enabled: Boolean(employeeId),
  });

  function invalidateAll() {
    queryClient.invalidateQueries({ queryKey: ["employee-documents", employeeId] });
    queryClient.invalidateQueries({ queryKey: ["employees", employeeId] });
    queryClient.invalidateQueries({ queryKey: ["onboarding-queue"] });
  }

  const reviewMutation = useMutation({
    mutationFn: ({
      documentId,
      approve,
      notes,
      expiryDate,
    }: {
      documentId: string;
      approve: boolean;
      notes?: string;
      expiryDate?: string | null;
    }) => reviewEmployeeDocument(employeeId as string, documentId, approve, notes, expiryDate),
    onSuccess: () => {
      invalidateAll();
      setRejecting(null);
      setRejectNotes("");
      setApproving(null);
      setApproveExpiryDate("");
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const hrApproveMutation = useMutation({
    mutationFn: () => hrApproveOnboarding(employeeId as string),
    onSuccess: invalidateAll,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const adminApproveMutation = useMutation({
    mutationFn: () => adminApproveOnboarding(employeeId as string),
    onSuccess: invalidateAll,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  async function handleDownload(documentId: string) {
    const url = await getDocumentDownloadUrl(employeeId as string, documentId);
    window.open(url, "_blank", "noopener,noreferrer");
  }

  if (!employee || isLoading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate("/onboarding")} sx={{ mb: 2 }}>
        Back to Queue
      </Button>

      <PageHeader
        title={`${employee.first_name} ${employee.last_name}`}
        subtitle={employee.employee_code}
        actions={
          <Stack direction="row" spacing={1}>
            <Chip label={employee.onboarding_status.replace("_", " ")} />
            <PermissionGate module="onboarding" action="review">
              {employee.onboarding_status === "submitted" && (
                <Button
                  variant="contained"
                  onClick={() => hrApproveMutation.mutate()}
                  disabled={hrApproveMutation.isPending}
                >
                  Mark HR-Reviewed
                </Button>
              )}
            </PermissionGate>
            <PermissionGate module="onboarding" action="approve">
              {employee.onboarding_status === "hr_approved" && (
                <Button
                  variant="contained"
                  color="success"
                  onClick={() => adminApproveMutation.mutate()}
                  disabled={adminApproveMutation.isPending}
                >
                  Activate Account
                </Button>
              )}
            </PermissionGate>
          </Stack>
        }
      />

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Card variant="outlined">
        <CardContent>
          <Typography variant="h3" sx={{ mb: 2 }}>
            Submitted Documents
          </Typography>
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Document</TableCell>
                  <TableCell>File</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Expires</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(documents ?? []).map((doc) => (
                  <TableRow key={doc.id} hover>
                    <TableCell>{doc.document_type_name}</TableCell>
                    <TableCell>{doc.original_filename}</TableCell>
                    <TableCell>
                      <Chip label={doc.status} size="small" color={STATUS_COLOR[doc.status]} />
                    </TableCell>
                    <TableCell>{doc.expiry_date ?? "—"}</TableCell>
                    <TableCell align="right">
                      <IconButton size="small" onClick={() => handleDownload(doc.id)}>
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                      <PermissionGate module="onboarding" action="review">
                        <IconButton
                          size="small"
                          color="success"
                          onClick={() => {
                            setApproveExpiryDate(doc.expiry_date ?? "");
                            setApproving(doc);
                          }}
                          disabled={doc.status === "approved"}
                        >
                          <CheckIcon fontSize="small" />
                        </IconButton>
                        <IconButton size="small" color="error" onClick={() => setRejecting(doc)}>
                          <CloseIcon fontSize="small" />
                        </IconButton>
                      </PermissionGate>
                    </TableCell>
                  </TableRow>
                ))}
                {(documents ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} align="center" sx={{ py: 4, color: "text.secondary" }}>
                      No documents uploaded yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      <Dialog open={Boolean(rejecting)} onClose={() => setRejecting(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Reject "{rejecting?.document_type_name}"</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={3}
            label="Notes for the employee"
            value={rejectNotes}
            onChange={(event) => setRejectNotes(event.target.value)}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setRejecting(null)}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            disabled={reviewMutation.isPending}
            onClick={() =>
              rejecting && reviewMutation.mutate({ documentId: rejecting.id, approve: false, notes: rejectNotes })
            }
          >
            Reject
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(approving)} onClose={() => setApproving(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Approve "{approving?.document_type_name}"</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            fullWidth
            type="date"
            label="Expiry date (optional)"
            InputLabelProps={{ shrink: true }}
            value={approveExpiryDate}
            onChange={(event) => setApproveExpiryDate(event.target.value)}
            helperText="Set this for documents like a visa or ID card that expire — you'll get a reminder 7 days before."
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setApproving(null)}>Cancel</Button>
          <Button
            variant="contained"
            color="success"
            disabled={reviewMutation.isPending}
            onClick={() =>
              approving &&
              reviewMutation.mutate({ documentId: approving.id, approve: true, expiryDate: approveExpiryDate })
            }
          >
            Approve
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
