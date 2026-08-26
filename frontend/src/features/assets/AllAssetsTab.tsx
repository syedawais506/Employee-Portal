import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DownloadIcon from "@mui/icons-material/Download";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import HistoryIcon from "@mui/icons-material/History";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import {
  assignAsset,
  createAsset,
  deleteAsset,
  downloadAssetExportCsv,
  getAssetSummary,
  listAssetTypes,
  listAssets,
  returnAsset,
  updateAsset,
  type AssetInput,
} from "@/api/assets";
import { extractApiErrorMessage } from "@/api/client";
import { listEmployees } from "@/api/employees";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { AssetFormDialog } from "@/features/assets/AssetFormDialog";
import { AssetHistoryDialog } from "@/features/assets/AssetHistoryDialog";
import { AssignAssetDialog } from "@/features/assets/AssignAssetDialog";
import { useAuthStore } from "@/store/authStore";
import type { Asset } from "@/types";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  available: "success",
  assigned: "info",
  retired: "default",
  lost: "error",
  damaged: "error",
};

function SummaryCard({ label, value }: { label: string; value: string | number }) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="h1" sx={{ mt: 0.5 }}>
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

export function AllAssetsTab() {
  const queryClient = useQueryClient();
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canCreate = hasPermission("asset", "create");
  const canUpdate = hasPermission("asset", "update");
  const canDelete = hasPermission("asset", "delete");
  const canExport = hasPermission("asset", "export");

  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [assetTypeFilter, setAssetTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [form, setForm] = useState<{ open: boolean; editing: Asset | null }>({ open: false, editing: null });
  const [pendingDelete, setPendingDelete] = useState<Asset | null>(null);
  const [assigning, setAssigning] = useState<Asset | null>(null);
  const [viewingHistory, setViewingHistory] = useState<Asset | null>(null);

  const { data: summary } = useQuery({ queryKey: ["assets", "summary"], queryFn: getAssetSummary });
  const { data: assetTypes } = useQuery({ queryKey: ["assets", "types"], queryFn: listAssetTypes });
  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 200 }),
    enabled: canUpdate,
  });
  const { data, isLoading } = useQuery({
    queryKey: ["assets", "list", page, pageSize, assetTypeFilter, statusFilter],
    queryFn: () =>
      listAssets(page + 1, pageSize, { assetTypeId: assetTypeFilter || undefined, status: statusFilter || undefined }),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["assets"] });
  };

  const saveMutation = useMutation({
    mutationFn: ({ id, payload }: { id?: string; payload: AssetInput }) =>
      id ? updateAsset(id, payload) : createAsset(payload),
    onSuccess: () => {
      invalidate();
      setForm({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAsset,
    onSuccess: () => {
      invalidate();
      setPendingDelete(null);
    },
    onError: (error) => {
      setErrorMessage(extractApiErrorMessage(error));
      setPendingDelete(null);
    },
  });

  const assignMutation = useMutation({
    mutationFn: ({ id, employeeId }: { id: string; employeeId: string }) => assignAsset(id, employeeId),
    onSuccess: () => {
      invalidate();
      setAssigning(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const returnMutation = useMutation({
    mutationFn: returnAsset,
    onSuccess: invalidate,
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  async function handleExport() {
    setExporting(true);
    try {
      await downloadAssetExportCsv({ assetTypeId: assetTypeFilter || undefined, status: statusFilter || undefined });
    } finally {
      setExporting(false);
    }
  }

  const items = data?.items ?? [];

  return (
    <>
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} sm={3} md={2}>
          <SummaryCard label="Total" value={summary?.total ?? "—"} />
        </Grid>
        <Grid item xs={6} sm={3} md={2}>
          <SummaryCard label="Available" value={summary?.available ?? "—"} />
        </Grid>
        <Grid item xs={6} sm={3} md={2}>
          <SummaryCard label="Assigned" value={summary?.assigned ?? "—"} />
        </Grid>
        <Grid item xs={6} sm={3} md={2}>
          <SummaryCard label="Retired" value={summary?.retired ?? "—"} />
        </Grid>
        <Grid item xs={6} sm={3} md={2}>
          <SummaryCard label="Lost" value={summary?.lost ?? "—"} />
        </Grid>
        <Grid item xs={6} sm={3} md={2}>
          <SummaryCard label="Damaged" value={summary?.damaged ?? "—"} />
        </Grid>
      </Grid>

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }} flexWrap="wrap" gap={1}>
        <Stack direction="row" spacing={1.5}>
          <TextField
            select
            size="small"
            label="Type"
            value={assetTypeFilter}
            onChange={(event) => {
              setAssetTypeFilter(event.target.value);
              setPage(0);
            }}
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="">All types</MenuItem>
            {(assetTypes ?? []).map((assetType) => (
              <MenuItem key={assetType.id} value={assetType.id}>
                {assetType.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label="Status"
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value);
              setPage(0);
            }}
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="">All statuses</MenuItem>
            <MenuItem value="available">Available</MenuItem>
            <MenuItem value="assigned">Assigned</MenuItem>
            <MenuItem value="retired">Retired</MenuItem>
            <MenuItem value="lost">Lost</MenuItem>
            <MenuItem value="damaged">Damaged</MenuItem>
          </TextField>
        </Stack>
        <Stack direction="row" spacing={1.5}>
          {canExport && (
            <Button startIcon={<DownloadIcon />} onClick={handleExport} disabled={exporting}>
              Export CSV
            </Button>
          )}
          {canCreate && (
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setForm({ open: true, editing: null })}>
              Add Asset
            </Button>
          )}
        </Stack>
      </Stack>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Tag</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Current holder</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((asset) => (
              <TableRow key={asset.id} hover>
                <TableCell>{asset.asset_tag}</TableCell>
                <TableCell>{asset.name}</TableCell>
                <TableCell>{asset.asset_type_name}</TableCell>
                <TableCell>
                  <Chip label={asset.status} size="small" color={STATUS_COLOR[asset.status]} />
                </TableCell>
                <TableCell>{asset.current_employee_name ?? "—"}</TableCell>
                <TableCell align="right">
                  {canUpdate && asset.status === "available" && (
                    <Button size="small" onClick={() => setAssigning(asset)}>
                      Assign
                    </Button>
                  )}
                  {canUpdate && asset.status === "assigned" && (
                    <Button size="small" onClick={() => returnMutation.mutate(asset.id)}>
                      Return
                    </Button>
                  )}
                  <IconButton size="small" onClick={() => setViewingHistory(asset)}>
                    <HistoryIcon fontSize="small" />
                  </IconButton>
                  {canUpdate && (
                    <IconButton size="small" onClick={() => setForm({ open: true, editing: asset })}>
                      <EditOutlinedIcon fontSize="small" />
                    </IconButton>
                  )}
                  {canDelete && (
                    <IconButton size="small" onClick={() => setPendingDelete(asset)}>
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  )}
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && items.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">No assets found.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={data?.total ?? 0}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={pageSize}
          onRowsPerPageChange={(event) => {
            setPageSize(Number(event.target.value));
            setPage(0);
          }}
        />
      </TableContainer>

      <AssetFormDialog
        open={form.open}
        assetTypes={assetTypes ?? []}
        editing={form.editing}
        submitting={saveMutation.isPending}
        onClose={() => setForm({ open: false, editing: null })}
        onSubmit={(payload) => saveMutation.mutate({ id: form.editing?.id, payload })}
      />
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete asset"
        description={`Delete "${pendingDelete?.asset_tag ?? ""}"? This is only possible if it has no assignment history.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
      <AssignAssetDialog
        open={Boolean(assigning)}
        employees={employees?.items ?? []}
        loading={assignMutation.isPending}
        onClose={() => setAssigning(null)}
        onConfirm={(employeeId) => assigning && assignMutation.mutate({ id: assigning.id, employeeId })}
      />
      <AssetHistoryDialog open={Boolean(viewingHistory)} asset={viewingHistory} onClose={() => setViewingHistory(null)} />
    </>
  );
}
