import { useEffect } from "react";
import { Controller, useForm } from "react-hook-form";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  MenuItem,
  TextField,
} from "@mui/material";

import type { AssetInput } from "@/api/assets";
import type { Asset, AssetType } from "@/types";

interface FormValues {
  asset_type_id: string;
  asset_tag: string;
  name: string;
  purchase_date: string;
  warranty_expiry: string;
  notes: string;
}

interface AssetFormDialogProps {
  open: boolean;
  assetTypes: AssetType[];
  editing: Asset | null;
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (values: AssetInput) => void;
}

const EMPTY_VALUES: FormValues = {
  asset_type_id: "",
  asset_tag: "",
  name: "",
  purchase_date: "",
  warranty_expiry: "",
  notes: "",
};

export function AssetFormDialog({ open, assetTypes, editing, submitting, onClose, onSubmit }: AssetFormDialogProps) {
  const { control, handleSubmit, reset } = useForm<FormValues>({ defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    reset(
      editing
        ? {
            asset_type_id: editing.asset_type_id,
            asset_tag: editing.asset_tag,
            name: editing.name,
            purchase_date: editing.purchase_date ?? "",
            warranty_expiry: editing.warranty_expiry ?? "",
            notes: editing.notes ?? "",
          }
        : EMPTY_VALUES,
    );
  }, [open, editing, reset]);

  function submit(values: FormValues) {
    onSubmit({
      asset_type_id: values.asset_type_id,
      asset_tag: values.asset_tag,
      name: values.name,
      purchase_date: values.purchase_date || null,
      warranty_expiry: values.warranty_expiry || null,
      notes: values.notes || null,
    });
  }

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>{editing ? "Edit Asset" : "New Asset"}</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12} sm={6}>
            <Controller
              name="asset_type_id"
              control={control}
              rules={{ required: "Asset type is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  select
                  label="Asset type"
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                >
                  {assetTypes.map((assetType) => (
                    <MenuItem key={assetType.id} value={assetType.id}>
                      {assetType.name}
                    </MenuItem>
                  ))}
                </TextField>
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="asset_tag"
              control={control}
              rules={{ required: "Asset tag is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Asset tag / serial number"
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="name"
              control={control}
              rules={{ required: "Name is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Name"
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="purchase_date"
              control={control}
              render={({ field }) => (
                <TextField {...field} type="date" label="Purchase date" fullWidth InputLabelProps={{ shrink: true }} />
              )}
            />
          </Grid>
          <Grid item xs={12} sm={6}>
            <Controller
              name="warranty_expiry"
              control={control}
              render={({ field }) => (
                <TextField {...field} type="date" label="Warranty expiry" fullWidth InputLabelProps={{ shrink: true }} />
              )}
            />
          </Grid>
          <Grid item xs={12}>
            <Controller
              name="notes"
              control={control}
              render={({ field }) => <TextField {...field} label="Notes (optional)" fullWidth multiline minRows={2} />}
            />
          </Grid>
        </Grid>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={handleSubmit(submit)} disabled={submitting}>
          {editing ? "Save changes" : "Create"}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
