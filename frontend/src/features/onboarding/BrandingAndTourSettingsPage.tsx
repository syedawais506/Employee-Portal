import { useEffect, useRef, useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { extractApiErrorMessage } from "@/api/client";
import { getBranding, updateBrandingColor, uploadBrandingLogo } from "@/api/branding";
import { createTourStep, deleteTourStep, listTourSteps, updateTourStep } from "@/api/companyTour";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import type { CompanyTourStep } from "@/types";

interface TourStepFormValues {
  title: string;
  body: string;
  sort_order: number;
}

export function BrandingAndTourSettingsPage() {
  const queryClient = useQueryClient();
  const logoInputRef = useRef<HTMLInputElement>(null);
  const [color, setColor] = useState("#4F46E5");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [stepDialog, setStepDialog] = useState<{ open: boolean; editing: CompanyTourStep | null }>({
    open: false,
    editing: null,
  });
  const [stepImage, setStepImage] = useState<File | null>(null);
  const [pendingDelete, setPendingDelete] = useState<CompanyTourStep | null>(null);

  const { data: branding } = useQuery({ queryKey: ["branding"], queryFn: getBranding });
  const { data: steps } = useQuery({ queryKey: ["company-tour"], queryFn: listTourSteps });

  useEffect(() => {
    if (branding?.primary_color) setColor(branding.primary_color);
  }, [branding?.primary_color]);

  const { control, handleSubmit, reset } = useForm<TourStepFormValues>({
    defaultValues: { title: "", body: "", sort_order: (steps?.length ?? 0) + 1 },
  });

  useEffect(() => {
    if (!stepDialog.open) return;
    if (stepDialog.editing) {
      reset({
        title: stepDialog.editing.title,
        body: stepDialog.editing.body,
        sort_order: stepDialog.editing.sort_order,
      });
    } else {
      reset({ title: "", body: "", sort_order: (steps?.length ?? 0) + 1 });
    }
    setStepImage(null);
  }, [stepDialog, steps, reset]);

  const colorMutation = useMutation({
    mutationFn: () => updateBrandingColor(color),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branding"] });
      setSuccessMessage("Accent color saved.");
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const logoMutation = useMutation({
    mutationFn: uploadBrandingLogo,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["branding"] });
      setSuccessMessage("Logo uploaded.");
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const stepMutation = useMutation({
    mutationFn: (values: TourStepFormValues) =>
      stepDialog.editing
        ? updateTourStep(stepDialog.editing.id, {
            title: values.title,
            body: values.body,
            sortOrder: Number(values.sort_order),
          })
        : createTourStep({
            title: values.title,
            body: values.body,
            sortOrder: Number(values.sort_order),
            image: stepImage,
          }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-tour"] });
      setStepDialog({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTourStep,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["company-tour"] });
      setPendingDelete(null);
    },
  });

  return (
    <Stack spacing={4}>
      {successMessage && (
        <Alert severity="success" onClose={() => setSuccessMessage(null)}>
          {successMessage}
        </Alert>
      )}
      {errorMessage && (
        <Alert severity="error" onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h3" sx={{ mb: 1 }}>
          Branding
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Shown on the public onboarding link a new hire opens — your logo and accent color, not the generic Employee
          Portal look.
        </Typography>
        <Stack direction="row" spacing={4} alignItems="center" flexWrap="wrap">
          <Stack spacing={1} alignItems="center">
            <Avatar
              variant="rounded"
              src={branding?.logo_url ?? undefined}
              sx={{ width: 80, height: 80, bgcolor: "action.hover" }}
            >
              {branding?.name?.charAt(0) ?? "?"}
            </Avatar>
            <Button
              size="small"
              startIcon={<UploadFileIcon fontSize="small" />}
              onClick={() => logoInputRef.current?.click()}
              disabled={logoMutation.isPending}
            >
              Upload logo
            </Button>
            <input
              ref={logoInputRef}
              type="file"
              hidden
              accept="image/png,image/jpeg"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) logoMutation.mutate(file);
                event.target.value = "";
              }}
            />
          </Stack>
          <Stack spacing={1}>
            <Typography variant="body2">Accent color</Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <input
                type="color"
                value={color}
                onChange={(event) => setColor(event.target.value)}
                style={{ width: 40, height: 40, border: "none", background: "none", cursor: "pointer" }}
              />
              <TextField
                size="small"
                value={color}
                onChange={(event) => setColor(event.target.value)}
                sx={{ width: 140 }}
              />
              <Button variant="contained" size="small" onClick={() => colorMutation.mutate()}>
                Save
              </Button>
            </Stack>
          </Stack>
        </Stack>
      </Paper>

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="h3">Company Tour</Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setErrorMessage(null);
              setStepDialog({ open: true, editing: null });
            }}
          >
            Add Step
          </Button>
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          A short, skippable walkthrough shown to new hires before they set a password — welcome message, culture,
          whatever you want them to see first. Shown in this order.
        </Typography>

        <Stack spacing={1.5}>
          {(steps ?? []).map((step) => (
            <Paper key={step.id} variant="outlined" sx={{ p: 2 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={2}>
                <Box>
                  <Typography variant="body1" fontWeight={600}>
                    {step.sort_order}. {step.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {step.body}
                  </Typography>
                </Box>
                <Stack direction="row">
                  <IconButton size="small" onClick={() => setStepDialog({ open: true, editing: step })}>
                    <EditOutlinedIcon fontSize="small" />
                  </IconButton>
                  <IconButton size="small" onClick={() => setPendingDelete(step)}>
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Stack>
              </Stack>
            </Paper>
          ))}
          {(steps ?? []).length === 0 && (
            <Typography align="center" sx={{ py: 4, color: "text.secondary" }}>
              No tour steps yet — new hires go straight to setting a password.
            </Typography>
          )}
        </Stack>
      </Paper>

      <Dialog
        open={stepDialog.open}
        onClose={() => setStepDialog({ open: false, editing: null })}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>{stepDialog.editing ? "Edit Tour Step" : "Add Tour Step"}</DialogTitle>
        <DialogContent>
          <Stack spacing={2.5} sx={{ mt: 1 }}>
            <Controller
              name="title"
              control={control}
              rules={{ required: "Title is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Title"
                  autoFocus
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
            <Controller
              name="body"
              control={control}
              rules={{ required: "Body is required" }}
              render={({ field, fieldState }) => (
                <TextField
                  {...field}
                  label="Body"
                  multiline
                  minRows={3}
                  fullWidth
                  error={Boolean(fieldState.error)}
                  helperText={fieldState.error?.message}
                />
              )}
            />
            <Controller
              name="sort_order"
              control={control}
              render={({ field }) => <TextField {...field} type="number" label="Order" fullWidth />}
            />
            {!stepDialog.editing && (
              <Button component="label" variant="outlined" startIcon={<UploadFileIcon />}>
                {stepImage ? stepImage.name : "Attach image (optional)"}
                <input
                  type="file"
                  hidden
                  accept="image/png,image/jpeg"
                  onChange={(event) => setStepImage(event.target.files?.[0] ?? null)}
                />
              </Button>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setStepDialog({ open: false, editing: null })}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSubmit((values) => stepMutation.mutate(values))}
            disabled={stepMutation.isPending}
          >
            {stepDialog.editing ? "Save" : "Create"}
          </Button>
        </DialogActions>
      </Dialog>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete tour step"
        description={`Remove "${pendingDelete?.title ?? ""}" from the company tour?`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
    </Stack>
  );
}
