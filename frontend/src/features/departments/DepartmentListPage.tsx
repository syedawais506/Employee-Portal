import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DownloadIcon from "@mui/icons-material/Download";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import {
  Alert,
  Button,
  IconButton,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
} from "@mui/material";

import {
  createDepartment,
  deleteDepartment,
  downloadDepartmentsExportCsv,
  listDepartments,
  updateDepartment,
} from "@/api/departments";
import { extractApiErrorMessage } from "@/api/client";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/PageHeader";
import { PermissionGate } from "@/components/PermissionGate";
import { DepartmentExportDialog } from "@/features/departments/DepartmentExportDialog";
import { DepartmentFormDialog } from "@/features/departments/DepartmentFormDialog";
import type { Department } from "@/types";

export function DepartmentListPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [formState, setFormState] = useState<{ open: boolean; editing: Department | null }>({
    open: false,
    editing: null,
  });
  const [pendingDelete, setPendingDelete] = useState<Department | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["departments", page, pageSize],
    queryFn: () => listDepartments(page + 1, pageSize),
  });
  const { data: allDepartments } = useQuery({
    queryKey: ["departments", "all"],
    queryFn: () => listDepartments(1, 100),
  });

  const createMutation = useMutation({
    mutationFn: createDepartment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setFormState({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof updateDepartment>[1] }) =>
      updateDepartment(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setFormState({ open: false, editing: null });
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteDepartment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["departments"] });
      setPendingDelete(null);
    },
  });

  function openCreate() {
    setErrorMessage(null);
    setFormState({ open: true, editing: null });
  }

  function openEdit(dept: Department) {
    setErrorMessage(null);
    setFormState({ open: true, editing: dept });
  }

  function handleSubmit(values: { name: string; parent_department_id: string | null; cost_center_code: string | null }) {
    if (formState.editing) {
      updateMutation.mutate({ id: formState.editing.id, payload: values });
    } else {
      createMutation.mutate(values);
    }
  }

  async function handleExport(filters: {
    search: string;
    parentDepartmentId: string;
    createdFrom: string;
    createdTo: string;
  }) {
    setExporting(true);
    try {
      await downloadDepartmentsExportCsv({
        search: filters.search || undefined,
        parentDepartmentId: filters.parentDepartmentId || undefined,
        createdFrom: filters.createdFrom || undefined,
        createdTo: filters.createdTo || undefined,
      });
      setExportOpen(false);
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Departments"
        subtitle="Organize your company into departments and cost centers."
        actions={
          <Stack direction="row" spacing={1.5}>
            <PermissionGate module="department" action="export">
              <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => setExportOpen(true)}>
                Export CSV
              </Button>
            </PermissionGate>
            <PermissionGate module="department" action="create">
              <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
                New Department
              </Button>
            </PermissionGate>
          </Stack>
        }
      />

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Cost Center</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.items ?? []).map((dept) => (
              <TableRow key={dept.id} hover>
                <TableCell>{dept.name}</TableCell>
                <TableCell>{dept.cost_center_code ?? "—"}</TableCell>
                <TableCell align="right">
                  <PermissionGate module="department" action="update">
                    <IconButton size="small" onClick={() => openEdit(dept)}>
                      <EditOutlinedIcon fontSize="small" />
                    </IconButton>
                  </PermissionGate>
                  <PermissionGate module="department" action="delete">
                    <IconButton size="small" onClick={() => setPendingDelete(dept)}>
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </PermissionGate>
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && (data?.items.length ?? 0) === 0 && (
              <TableRow>
                <TableCell colSpan={3} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No departments yet.
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

      <DepartmentFormDialog
        open={formState.open}
        initial={formState.editing}
        departments={data?.items ?? []}
        errorMessage={errorMessage}
        submitting={createMutation.isPending || updateMutation.isPending}
        onClose={() => setFormState({ open: false, editing: null })}
        onSubmit={handleSubmit}
      />

      <DepartmentExportDialog
        open={exportOpen}
        departments={allDepartments?.items ?? []}
        exporting={exporting}
        onClose={() => setExportOpen(false)}
        onExport={handleExport}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete department"
        description={`Are you sure you want to delete "${pendingDelete?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />

      {deleteMutation.isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {extractApiErrorMessage(deleteMutation.error)}
        </Alert>
      )}
    </>
  );
}
