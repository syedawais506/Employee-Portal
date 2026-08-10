import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { type ClientInput, createClient, deleteClient, listClients, updateClient } from "@/api/clients";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PermissionGate } from "@/components/PermissionGate";
import type { Client } from "@/types";

export function ClientsTab() {
  const queryClient = useQueryClient();
  const [formState, setFormState] = useState<{ open: boolean; editing: Client | null }>({
    open: false,
    editing: null,
  });
  const [pendingDelete, setPendingDelete] = useState<Client | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: clients } = useQuery({ queryKey: ["clients"], queryFn: listClients });

  const { control, handleSubmit, reset } = useForm<ClientInput>({
    defaultValues: { name: "", contact_name: "", contact_email: "", contact_phone: "" },
  });

  function openCreate() {
    setErrorMessage(null);
    reset({ name: "", contact_name: "", contact_email: "", contact_phone: "" });
    setFormState({ open: true, editing: null });
  }

  function openEdit(client: Client) {
    setErrorMessage(null);
    reset({
      name: client.name,
      contact_name: client.contact_name ?? "",
      contact_email: client.contact_email ?? "",
      contact_phone: client.contact_phone ?? "",
    });
    setFormState({ open: true, editing: client });
  }

  const createMutation = useMutation({
    mutationFn: createClient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setFormState({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ClientInput }) => updateClient(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setFormState({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteClient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setPendingDelete(null);
    },
  });

  function onSubmit(values: ClientInput) {
    if (formState.editing) {
      updateMutation.mutate({ id: formState.editing.id, payload: values });
    } else {
      createMutation.mutate(values);
    }
  }

  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Typography variant="h3">Clients</Typography>
        <PermissionGate module="project" action="create">
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
            New Client
          </Button>
        </PermissionGate>
      </Stack>

      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Contact</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Phone</TableCell>
            <TableCell align="right">Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {(clients ?? []).map((client) => (
            <TableRow key={client.id} hover>
              <TableCell>{client.name}</TableCell>
              <TableCell>{client.contact_name ?? "—"}</TableCell>
              <TableCell>{client.contact_email ?? "—"}</TableCell>
              <TableCell>{client.contact_phone ?? "—"}</TableCell>
              <TableCell align="right">
                <PermissionGate module="project" action="update">
                  <IconButton size="small" onClick={() => openEdit(client)}>
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                </PermissionGate>
                <PermissionGate module="project" action="delete">
                  <IconButton size="small" onClick={() => setPendingDelete(client)}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </PermissionGate>
              </TableCell>
            </TableRow>
          ))}
          {(clients ?? []).length === 0 && (
            <TableRow>
              <TableCell colSpan={5} align="center" sx={{ py: 4, color: "text.secondary" }}>
                No clients yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      <Dialog open={formState.open} onClose={() => setFormState({ open: false, editing: null })} maxWidth="xs" fullWidth>
        <DialogTitle>{formState.editing ? "Edit Client" : "New Client"}</DialogTitle>
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
                  value={field.value ?? ""}
                  label="Client name"
                  autoFocus
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
            <Controller
              name="contact_name"
              control={control}
              render={({ field }) => <TextField {...field} value={field.value ?? ""} label="Contact name" fullWidth />}
            />
            <Controller
              name="contact_email"
              control={control}
              render={({ field }) => <TextField {...field} value={field.value ?? ""} label="Contact email" fullWidth />}
            />
            <Controller
              name="contact_phone"
              control={control}
              render={({ field }) => <TextField {...field} value={field.value ?? ""} label="Contact phone" fullWidth />}
            />
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setFormState({ open: false, editing: null })}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSubmit(onSubmit)}
            disabled={createMutation.isPending || updateMutation.isPending}
          >
            {formState.editing ? "Save changes" : "Create client"}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete client"
        description={`Are you sure you want to delete "${pendingDelete?.name}"? Projects using this client will keep their other data but lose the client link.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
    </Paper>
  );
}
