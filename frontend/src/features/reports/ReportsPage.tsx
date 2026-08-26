import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import DownloadIcon from "@mui/icons-material/Download";
import { Alert, Button, Grid, MenuItem, Paper, Stack, TextField } from "@mui/material";

import { listAssetTypes } from "@/api/assets";
import { extractApiErrorMessage } from "@/api/client";
import { listClients } from "@/api/clients";
import { listDepartments } from "@/api/departments";
import { listEmployees } from "@/api/employees";
import { listLeaveTypes } from "@/api/leave";
import { listProjects } from "@/api/projects";
import {
  createSavedReport,
  deleteSavedReport,
  exportReportCsv,
  exportSavedReportCsv,
  listSavedReports,
  previewReport,
  runSavedReport,
} from "@/api/reports";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { PageHeader } from "@/components/PageHeader";
import { ReportFilterForm } from "@/features/reports/ReportFilterForm";
import { ReportPreviewTable } from "@/features/reports/ReportPreviewTable";
import { REPORT_MODULES, type ReportFieldOption } from "@/features/reports/reportModules";
import { SaveReportDialog } from "@/features/reports/SaveReportDialog";
import { SavedReportSelect } from "@/features/reports/SavedReportSelect";
import { useAuthStore } from "@/store/authStore";
import type { ReportModule, ReportPreview, SavedReport } from "@/types";

export function ReportsPage() {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canExport = hasPermission("report", "export");
  const canConfigure = hasPermission("report", "configure");
  const queryClient = useQueryClient();

  const [module, setModule] = useState<ReportModule>("employee");
  const [filterValues, setFilterValues] = useState<Record<string, string>>({});
  const [selectedSavedReportId, setSelectedSavedReportId] = useState("");
  const [preview, setPreview] = useState<ReportPreview | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [saveDialogOpen, setSaveDialogOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<SavedReport | null>(null);

  const moduleConfig = REPORT_MODULES.find((m) => m.value === module) ?? REPORT_MODULES[0];

  const { data: departments } = useQuery({ queryKey: ["departments", "all"], queryFn: () => listDepartments(1, 100) });
  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
  });
  const { data: projects } = useQuery({ queryKey: ["projects", "all"], queryFn: () => listProjects(1, 100) });
  const { data: clients } = useQuery({ queryKey: ["clients", "all"], queryFn: listClients });
  const { data: leaveTypes } = useQuery({ queryKey: ["leave", "types"], queryFn: listLeaveTypes });
  const { data: assetTypes } = useQuery({ queryKey: ["assets", "types"], queryFn: listAssetTypes });
  const { data: savedReports } = useQuery({ queryKey: ["reports", "saved"], queryFn: listSavedReports });

  const optionsBySource = useMemo<Record<string, ReportFieldOption[]>>(
    () => ({
      department: (departments?.items ?? []).map((d) => ({ value: d.id, label: d.name })),
      employee: (employees?.items ?? []).map((e) => ({ value: e.id, label: `${e.first_name} ${e.last_name}` })),
      project: (projects?.items ?? []).map((p) => ({ value: p.id, label: p.name })),
      client: (clients ?? []).map((c) => ({ value: c.id, label: c.name })),
      leaveType: (leaveTypes ?? []).map((lt) => ({ value: lt.id, label: lt.name })),
      assetType: (assetTypes ?? []).map((at) => ({ value: at.id, label: at.name })),
    }),
    [departments, employees, projects, clients, leaveTypes, assetTypes],
  );

  function buildFilters(): Record<string, unknown> {
    const filters: Record<string, unknown> = {};
    for (const field of moduleConfig.fields) {
      const raw = filterValues[field.name];
      if (raw === undefined || raw === "") continue;
      filters[field.name] = field.type === "boolean" ? raw === "true" : raw;
    }
    return filters;
  }

  const previewMutation = useMutation({
    mutationFn: () => previewReport(module, buildFilters()),
    onSuccess: (result) => {
      setPreview(result);
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const saveMutation = useMutation({
    mutationFn: (name: string) => createSavedReport({ name, module, filters: buildFilters() }),
    onSuccess: (report) => {
      queryClient.invalidateQueries({ queryKey: ["reports", "saved"] });
      setSelectedSavedReportId(report.id);
      setSaveDialogOpen(false);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteSavedReport,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reports", "saved"] });
      setSelectedSavedReportId((current) => (current === pendingDelete?.id ? "" : current));
      setPendingDelete(null);
    },
  });

  function handleModuleChange(next: ReportModule) {
    setModule(next);
    setFilterValues({});
    setSelectedSavedReportId("");
    setPreview(null);
  }

  async function handleExport() {
    setExporting(true);
    try {
      await exportReportCsv(module, buildFilters());
    } catch (error) {
      setErrorMessage(extractApiErrorMessage(error));
    } finally {
      setExporting(false);
    }
  }

  async function handleSelectSaved(report: SavedReport) {
    setSelectedSavedReportId(report.id);
    setModule(report.module);
    const stringValues: Record<string, string> = {};
    for (const [key, value] of Object.entries(report.filters)) stringValues[key] = String(value);
    setFilterValues(stringValues);
    setErrorMessage(null);
    try {
      setPreview(await runSavedReport(report.id));
    } catch (error) {
      setErrorMessage(extractApiErrorMessage(error));
    }
  }

  async function handleExportSaved(report: SavedReport) {
    try {
      await exportSavedReportCsv(report.id, report.name);
    } catch (error) {
      setErrorMessage(extractApiErrorMessage(error));
    }
  }

  return (
    <>
      <PageHeader title="Reports" subtitle="Preview and export cross-module data, or save a filter set to reuse later." />

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 2.5, mb: 3 }}>
        <Grid container spacing={2} sx={{ mb: 2 }}>
          <Grid item xs={12} sm={6} md={3}>
            <TextField
              select
              label="Module"
              fullWidth
              size="small"
              value={module}
              onChange={(event) => handleModuleChange(event.target.value as ReportModule)}
            >
              {REPORT_MODULES.map((m) => (
                <MenuItem key={m.value} value={m.value}>
                  {m.label}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={6} md={4}>
            <SavedReportSelect
              savedReports={savedReports ?? []}
              selectedId={selectedSavedReportId}
              canConfigure={canConfigure}
              onSelect={handleSelectSaved}
              onExport={handleExportSaved}
              onDelete={setPendingDelete}
            />
          </Grid>
        </Grid>

        <ReportFilterForm
          fields={moduleConfig.fields}
          values={filterValues}
          optionsBySource={optionsBySource}
          onChange={(name, value) => setFilterValues((prev) => ({ ...prev, [name]: value }))}
        />

        <Stack direction="row" spacing={1.5} sx={{ mt: 3 }}>
          <Button variant="contained" onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending}>
            Preview
          </Button>
          {canExport && (
            <Button startIcon={<DownloadIcon />} onClick={handleExport} disabled={exporting}>
              Export CSV
            </Button>
          )}
          {canConfigure && <Button onClick={() => setSaveDialogOpen(true)}>Save Report</Button>}
        </Stack>
      </Paper>

      <ReportPreviewTable preview={preview} />

      <SaveReportDialog
        open={saveDialogOpen}
        loading={saveMutation.isPending}
        onClose={() => setSaveDialogOpen(false)}
        onConfirm={(name) => saveMutation.mutate(name)}
      />
      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Delete saved report"
        description={`Delete "${pendingDelete?.name ?? ""}"?`}
        confirmLabel="Delete"
        destructive
        loading={deleteMutation.isPending}
        onClose={() => setPendingDelete(null)}
        onConfirm={() => pendingDelete && deleteMutation.mutate(pendingDelete.id)}
      />
    </>
  );
}
