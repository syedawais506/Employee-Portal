import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  TextField,
} from "@mui/material";

import { createRole, deleteRole, getPermissionCatalog, listRoles } from "@/api/roles";
import { extractApiErrorMessage } from "@/api/client";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/PageHeader";
import { PermissionGate } from "@/components/PermissionGate";
import { PermissionMatrixEditor } from "@/features/roles/PermissionMatrixEditor";
import type { Role } from "@/types";

export function RoleListPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [newRoleName, setNewRoleName] = useState("");
  const [pendingDelete, setPendingDelete] = useState<Role | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);

  const { data: roles } = useQuery({ queryKey: ["roles"], queryFn: listRoles });
  const { data: catalog } = useQuery({ queryKey: ["permission-catalog"], queryFn: getPermissionCatalog });

  const createMutation = useMutation({
    mutationFn: createRole,
    onSuccess: (role) => {
      queryClient.invalidateQueries({ queryKey: ["roles"] });
      setCreateOpen(false);
      setNewRoleName("");
      setSelectedId(role.id);
    },
    onError: (error) => setCreateError(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteRole,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roles"] });
      setPendingDelete(null);
      setSelectedId(null);
    },
  });

  const selectedRole = roles?.find((r) => r.id === selectedId) ?? roles?.[0] ?? null;

  return (
    <>
      <PageHeader
        title="Roles & Permissions"
        subtitle="Control what each role can view, create, update, or approve — no code changes required."
        actions={
          <PermissionGate module="role" action="create">
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateOpen(true)}>
              New Role
            </Button>
          </PermissionGate>
        }
      />

      <Grid container spacing={2}>
        <Grid item xs={12} md={3}>
          <Paper variant="outlined">
            <List disablePadding>
              {(roles ?? []).map((role) => (
                <ListItemButton
                  key={role.id}
                  selected={selectedRole?.id === role.id}
                  onClick={() => setSelectedId(role.id)}
                >
                  <ListItemText primary={role.name} secondary={role.is_system ? "System role" : undefined} />
                  {!role.is_system && (
                    <PermissionGate module="role" action="delete">
                      <IconButton
                        size="small"
                        edge="end"
                        onClick={(event) => {
                          event.stopPropagation();
                          setPendingDelete(role);
                        }}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </PermissionGate>
                  )}
                </ListItemButton>
              ))}
            </List>
          </Paper>
        </Grid>
        <Grid item xs={12} md={9}>
          <Paper variant="outlined" sx={{ p: 3 }}>
            {selectedRole && catalog ? (
              <PermissionMatrixEditor role={selectedRole} catalog={catalog} />
            ) : (
              <Box sx={{ color: "text.secondary" }}>Select a role to edit its permissions.</Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>New Role</DialogTitle>
        <DialogContent>
          {createError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {createError}
            </Alert>
          )}
          <TextField
            autoFocus
            fullWidth
            label="Role name"
            value={newRoleName}
            onChange={(event) => setNewRoleName(event.target.value)}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setCreateOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!newRoleName.trim() || createMutation.isPending}
            onClick={() => {
              setCreateError(null);
              createMutation.mutate(newRoleName.trim());
            }}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete role"
        description={`Are you sure you want to delete "${pendingDelete?.name}"? Users holding only this role will lose its permissions.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
    </>
  );
}
