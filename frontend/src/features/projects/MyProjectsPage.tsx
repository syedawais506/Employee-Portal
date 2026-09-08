import { useQuery } from "@tanstack/react-query";
import { Chip, Paper, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Typography } from "@mui/material";

import { listMyProjects } from "@/api/projects";
import { PageHeader } from "@/components/PageHeader";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error"> = {
  active: "success",
  on_hold: "warning",
  completed: "default",
  cancelled: "error",
};

export function MyProjectsPage() {
  const { data: projects, isLoading } = useQuery({ queryKey: ["projects", "mine"], queryFn: listMyProjects });

  return (
    <>
      <PageHeader title="My Projects" subtitle="Projects you're currently assigned to." />
      <Paper variant="outlined">
        <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Your role</TableCell>
              <TableCell>Start date</TableCell>
              <TableCell>End date</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(projects ?? []).map((project) => (
              <TableRow key={project.id} hover>
                <TableCell>{project.name}</TableCell>
                <TableCell>{project.role_on_project}</TableCell>
                <TableCell>{project.start_date ?? "—"}</TableCell>
                <TableCell>{project.end_date ?? "—"}</TableCell>
                <TableCell>
                  <Chip label={project.status.replace("_", " ")} size="small" color={STATUS_COLOR[project.status]} />
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && (projects ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">You're not assigned to any projects yet.</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        </TableContainer>
      </Paper>
    </>
  );
}
