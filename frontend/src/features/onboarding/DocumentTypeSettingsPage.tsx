import { useEffect, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import {
  Alert,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  Paper,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import {
  createDocumentType,
  deleteDocumentType,
  listDocumentTypes,
  updateDocumentType,
} from "@/api/documentTypes";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import type { DocumentType } from "@/types";

interface FormValues {
  name: string;
  is_required: boolean;
  sort_order: number;
}

export function DocumentTypeSettingsPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<DocumentType | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: documentTypes } = useQuery({ queryKey: ["document-types"], queryFn: listDocumentTypes });

  const { control, handleSubmit, reset } = useForm<FormValues>({
    defaultValues: { name: "", is_required: true, sort_order: (documentTypes?.length ?? 0) + 1 },
  });

  useEffect(() => {
    if (createOpen) reset({ name: "", is_required: true, sort_order: (documentTypes?.length ?? 0) + 1 });
  }, [createOpen, documentTypes, reset]);

  const createMutation = useMutation({
    mutationFn: createDocumentType,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
      setCreateOpen(false);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const toggleRequiredMutation = useMutation({
    mutationFn: ({ id, is_required }: { id: string; is_required: boolean }) => updateDocumentType(id, { is_required }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["document-types"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDocumentType,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document-types"] });
      setPendingDelete(null);
    },
  });

  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h3">Document Checklist</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            setErrorMessage(null);
            setCreateOpen(true);
          }}
        >
          Add Document Type
        </Button>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        New hires must upload every document marked "Required" before their onboarding can be submitted for review.
      </Typography>

      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Required</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(documentTypes ?? []).map((dt) => (
            <TableRow key={dt.id} hover>
              <TableCell>{dt.name}</TableCell>
              <TableCell>
                <Switch
                  checked={dt.is_required}
                  onChange={(event) => toggleRequiredMutation.mutate({ id: dt.id, is_required: event.target.checked })}
                />
              </TableCell>
              <TableCell align="right">
                <IconButton size="small" onClick={() => setPendingDelete(dt)}>
                  <DeleteOutlineIcon fontSize="small" />
                </IconButton>
              </TableCell>
            </TableRow>
          ))}
          {(documentTypes ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={3} align="center" sx={{ py: 4, color: "text.secondary" }}>
                No document types configured yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Add Document Type</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            {errorMessage && <Alert severity="error">{errorMessage}</Alert>}
            <Controller
              name="name"
              control={control}
              rules={{ required: "Name is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Document name"
                  autoFocus
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
            <Controller
              name="is_required"
              control={control}
              render={({ field }) => (
                <FormControlLabel control={<Checkbox {...field} checked={field.value} />} label="Required for onboarding" />
              )}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSubmit((values) => createMutation.mutate(values))}
            disabled={createMutation.isPending}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete document type"
        description={`Are you sure you want to delete "${pendingDelete?.name}"? Employees who already uploaded this document keep their file, but it won't be requested from future hires.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
    </Paper>
  );
}
