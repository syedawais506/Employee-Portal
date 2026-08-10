import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import {
  Button,
  Chip,
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

import { listClients } from "@/api/clients";
import { extractApiErrorMessage } from "@/api/client";
import { listEmployees } from "@/api/employees";
import { createProject, listProjects, type ProjectInput } from "@/api/projects";
import { PermissionGate } from "@/components/PermissionGate";
import { ProjectFormDialog } from "@/features/projects/ProjectFormDialog";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error"> = {
  active: "success",
  on_hold: "warning",
  completed: "default",
  cancelled: "error",
};

export function ProjectListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [formOpen, setFormOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["projects", statusFilter, page, pageSize],
    queryFn: () => listProjects(page + 1, pageSize, statusFilter || undefined),
  });

  const { data: clients } = useQuery({ queryKey: ["clients"], queryFn: listClients });
  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: (payload: ProjectInput) => createProject(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setFormOpen(false);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  return (
    <>
      <Stack direction="row" justifyContent="flex-end" sx={{ mb: 2 }}>
        <PermissionGate module="project" action="create">
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setErrorMessage(null);
              setFormOpen(true);
            }}
          >
            New Project
          </Button>
        </PermissionGate>
      </Stack>

      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
        <TextField
          select
          size="small"
          label="Status"
          value={statusFilter}
          onChange={(event) => {
            setStatusFilter(event.target.value);
            setPage(0);
          }}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All statuses</MenuItem>
          <MenuItem value="active">Active</MenuItem>
          <MenuItem value="on_hold">On hold</MenuItem>
          <MenuItem value="completed">Completed</MenuItem>
          <MenuItem value="cancelled">Cancelled</MenuItem>
        </TextField>
      </Stack>

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Client</TableCell>
              <TableCell>Members</TableCell>
              <TableCell>Billable</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.items ?? []).map((project) => (
              <TableRow key={project.id} hover sx={{ cursor: "pointer" }} onClick={() => navigate(`/projects/${project.id}`)}>
                <TableCell>{project.name}</TableCell>
                <TableCell>{project.client?.name ?? "—"}</TableCell>
                <TableCell>{project.member_count}</TableCell>
                <TableCell>{project.is_billable ? "Yes" : "No"}</TableCell>
                <TableCell>
                  <Chip label={project.status.replace("_", " ")} size="small" color={STATUS_COLOR[project.status]} />
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && (data?.items.length ?? 0) === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No projects match these filters.
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

      <ProjectFormDialog
        open={formOpen}
        clients={clients ?? []}
        employees={employees?.items ?? []}
        errorMessage={errorMessage}
        submitting={createMutation.isPending}
        onClose={() => setFormOpen(false)}
        onSubmit={(values) => createMutation.mutate(values)}
      />
    </>
  );
}
