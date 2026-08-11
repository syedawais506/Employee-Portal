import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import DownloadIcon from "@mui/icons-material/Download";
import {
  Alert,
  Button,
  Chip,
  IconButton,
  InputAdornment,
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
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";

import { extractApiErrorMessage } from "@/api/client";
import { listDepartments } from "@/api/departments";
import { createEmployee, deleteEmployee, downloadEmployeesExportCsv, listEmployees } from "@/api/employees";
import { listRoles } from "@/api/roles";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/PageHeader";
import { PermissionGate } from "@/components/PermissionGate";
import { EmployeeExportDialog } from "@/features/employees/EmployeeExportDialog";
import { EmployeeFormDialog, type EmployeeFormValues } from "@/features/employees/EmployeeFormDialog";
import type { EmployeeSummary } from "@/types";

const STATUS_COLOR: Record<string, "success" | "warning" | "default"> = {
  active: "success",
  on_leave: "warning",
  exited: "default",
};

export function EmployeeListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [formOpen, setFormOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<EmployeeSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["employees", { search, departmentFilter, statusFilter, page, pageSize }],
    queryFn: () =>
      listEmployees({
        search: search || undefined,
        department_id: departmentFilter || undefined,
        status: statusFilter || undefined,
        page: page + 1,
        page_size: pageSize,
      }),
  });

  const { data: departments } = useQuery({ queryKey: ["departments", "all"], queryFn: () => listDepartments(1, 100) });
  const { data: roles } = useQuery({ queryKey: ["roles"], queryFn: listRoles });
  const { data: managers } = useQuery({
    queryKey: ["employees", "managers"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: (values: EmployeeFormValues) =>
      createEmployee({
        email: values.email,
        first_name: values.first_name,
        last_name: values.last_name,
        phone: values.phone || null,
        department_id: values.department_id || null,
        designation: values.designation || null,
        manager_id: values.manager_id || null,
        employment_type: values.employment_type,
        location: values.location || null,
        joining_date: values.joining_date || null,
        role_ids: values.role_ids,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setFormOpen(false);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["employees"] });
      setPendingDelete(null);
    },
  });

  async function handleExport(filters: {
    search: string;
    departmentId: string;
    status: string;
    managerId: string;
    employmentType: string;
    location: string;
    joiningDateFrom: string;
    joiningDateTo: string;
  }) {
    setExporting(true);
    try {
      await downloadEmployeesExportCsv({
        search: filters.search || undefined,
        departmentId: filters.departmentId || undefined,
        status: filters.status || undefined,
        managerId: filters.managerId || undefined,
        employmentType: filters.employmentType || undefined,
        location: filters.location || undefined,
        joiningDateFrom: filters.joiningDateFrom || undefined,
        joiningDateTo: filters.joiningDateTo || undefined,
      });
      setExportOpen(false);
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Employees"
        subtitle="Manage your company's employee directory."
        actions={
          <Stack direction="row" spacing={1.5}>
            <PermissionGate module="employee" action="export">
              <Button variant="outlined" startIcon={<DownloadIcon />} onClick={() => setExportOpen(true)}>
                Export CSV
              </Button>
            </PermissionGate>
            <PermissionGate module="employee" action="create">
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={() => {
                  setErrorMessage(null);
                  setFormOpen(true);
                }}
              >
                New Employee
              </Button>
            </PermissionGate>
          </Stack>
        }
      />

      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField
          placeholder="Search by name or employee code"
          size="small"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 280 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
          }}
        />
        <TextField
          select
          size="small"
          label="Department"
          value={departmentFilter}
          onChange={(event) => {
            setDepartmentFilter(event.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All departments</MenuItem>
          {(departments?.items ?? []).map((dept) => (
            <MenuItem key={dept.id} value={dept.id}>
              {dept.name}
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
          <MenuItem value="active">Active</MenuItem>
          <MenuItem value="on_leave">On leave</MenuItem>
          <MenuItem value="exited">Exited</MenuItem>
        </TextField>
      </Stack>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Employee Code</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Designation</TableCell>
              <TableCell>Department</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.items ?? []).map((employee) => (
              <TableRow key={employee.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/employees/${employee.id}`)}>
                <TableCell>{employee.employee_code}</TableCell>
                <TableCell>
                  {employee.first_name} {employee.last_name}
                </TableCell>
                <TableCell>{employee.designation ?? "—"}</TableCell>
                <TableCell>{employee.department?.name ?? "—"}</TableCell>
                <TableCell>
                  <Chip label={employee.status.replace("_", " ")} size="small" color={STATUS_COLOR[employee.status]} />
                </TableCell>
                <TableCell align="right" onClick={(event) => event.stopPropagation()}>
                  <PermissionGate module="employee" action="delete">
                    <IconButton size="small" onClick={() => setPendingDelete(employee)}>
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </PermissionGate>
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && (data?.items.length ?? 0) === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No employees match these filters.
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

      <EmployeeFormDialog
        open={formOpen}
        mode="create"
        departments={departments?.items ?? []}
        managers={managers?.items ?? []}
        roles={roles ?? []}
        errorMessage={errorMessage}
        submitting={createMutation.isPending}
        onClose={() => setFormOpen(false)}
        onSubmit={(values) => createMutation.mutate(values)}
      />

      <EmployeeExportDialog
        open={exportOpen}
        departments={departments?.items ?? []}
        managers={managers?.items ?? []}
        exporting={exporting}
        onClose={() => setExportOpen(false)}
        onExport={handleExport}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Remove employee"
        description={`Are you sure you want to remove ${pendingDelete?.first_name} ${pendingDelete?.last_name}? Their record is retained for audit history.`}
        confirmLabel="Remove"
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
