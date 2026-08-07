import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import AddIcon from "@mui/icons-material/Add";
import {
  Button,
  Chip,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
} from "@mui/material";

import { createCompany, listCompanies, updateCompanyStatus } from "@/api/companies";
import { extractApiErrorMessage } from "@/api/client";
import { PageHeader } from "@/components/PageHeader";
import { CompanyFormDialog } from "@/features/companies/CompanyFormDialog";

export function CompanyListPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [formOpen, setFormOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["companies", page, pageSize],
    queryFn: () => listCompanies(page + 1, pageSize),
  });

  const createMutation = useMutation({
    mutationFn: createCompany,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["companies"] });
      setFormOpen(false);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) => updateCompanyStatus(id, status),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["companies"] }),
  });

  return (
    <>
      <PageHeader
        title="Companies"
        subtitle="Every company's data is fully isolated from every other company."
        actions={
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              setErrorMessage(null);
              setFormOpen(true);
            }}
          >
            New Company
          </Button>
        }
      />

      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Slug</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(data?.items ?? []).map((company) => (
              <TableRow key={company.id} hover>
                <TableCell>{company.name}</TableCell>
                <TableCell>{company.slug}</TableCell>
                <TableCell>
                  <Chip
                    label={company.status}
                    size="small"
                    color={company.status === "active" ? "success" : "warning"}
                  />
                </TableCell>
                <TableCell align="right">
                  <Button
                    size="small"
                    onClick={() =>
                      statusMutation.mutate({
                        id: company.id,
                        status: company.status === "active" ? "suspended" : "active",
                      })
                    }
                  >
                    {company.status === "active" ? "Suspend" : "Reactivate"}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {!isLoading && (data?.items.length ?? 0) === 0 && (
              <TableRow>
                <TableCell colSpan={4} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No companies yet.
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

      <CompanyFormDialog
        open={formOpen}
        errorMessage={errorMessage}
        submitting={createMutation.isPending}
        onClose={() => setFormOpen(false)}
        onSubmit={(values) => createMutation.mutate(values)}
      />
    </>
  );
}
