import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import { Alert, Button, IconButton, Paper, Stack, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { createAssetType, deleteAssetType, listAssetTypes, updateAssetType } from "@/api/assets";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { AssetTypeFormDialog } from "@/features/assets/AssetTypeFormDialog";
import { useAuthStore } from "@/store/authStore";
import type { AssetType } from "@/types";

export function AssetTypesTab() {
  const queryClient = useQueryClient();
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canCreate = hasPermission("asset", "create");
  const canUpdate = hasPermission("asset", "update");
  const canDelete = hasPermission("asset", "delete");

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [form, setForm] = useState<{ open: boolean; editing: AssetType | null }>({ open: false, editing: null });
  const [pendingDelete, setPendingDelete] = useState<AssetType | null>(null);

  const { data: assetTypes } = useQuery({ queryKey: ["assets", "types"], queryFn: listAssetTypes });

  const saveMutation = useMutation({
    mutationFn: ({ id, name }: { id?: string; name: string }) => (id ? updateAssetType(id, name) : createAssetType(name)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets", "types"] });
      setForm({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAssetType,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assets", "types"] });
      setPendingDelete(null);
    },
    onError: (error) => {
      setErrorMessage(extractApiErrorMessage(error));
      setPendingDelete(null);
    },
  });

  return (
    <>
      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      {canCreate && (
        <Stack direction="row" justifyContent="flex-end" sx={{ mb: 1.5 }}>
          <Button size="small" startIcon={<AddIcon />} onClick={() => setForm({ open: true, editing: null })}>
            Add Asset Type
          </Button>
        </Stack>
      )}

      <Paper variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              {(canUpdate || canDelete) && <TableCell align="right">Actions</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {(assetTypes ?? []).map((assetType) => (
              <TableRow key={assetType.id} hover>
                <TableCell>{assetType.name}</TableCell>
                {(canUpdate || canDelete) && (
                  <TableCell align="right">
                    {canUpdate && (
                      <IconButton size="small" onClick={() => setForm({ open: true, editing: assetType })}>
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                    )}
                    {canDelete && (
                      <IconButton size="small" onClick={() => setPendingDelete(assetType)}>
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    )}
                  </TableCell>
                )}
              </TableRow>
            ))}
            {(assetTypes ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={2} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No asset types yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      <AssetTypeFormDialog
        open={form.open}
        editing={form.editing}
        submitting={saveMutation.isPending}
        onClose={() => setForm({ open: false, editing: null })}
        onSubmit={(name) => saveMutation.mutate({ id: form.editing?.id, name })}
      />
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete asset type"
        description={`Delete "${pendingDelete?.name ?? ""}"? This is only possible if no assets use it.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
    </>
  );
}
