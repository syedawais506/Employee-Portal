import { Grid, MenuItem, TextField } from "@mui/material";

import type { ReportFieldConfig, ReportFieldOption } from "@/features/reports/reportModules";

interface ReportFilterFormProps {
  fields: ReportFieldConfig[];
  values: Record<string, string>;
  optionsBySource: Record<string, ReportFieldOption[]>;
  onChange: (name: string, value: string) => void;
}

export function ReportFilterForm({ fields, values, optionsBySource, onChange }: ReportFilterFormProps) {
  return (
    <Grid container spacing={2}>
      {fields.map((field) => {
        const value = values[field.name] ?? "";
        if (field.type === "text") {
          return (
            <Grid item xs={12} sm={6} md={4} key={field.name}>
              <TextField
                label={field.label}
                fullWidth
                size="small"
                value={value}
                onChange={(event) => onChange(field.name, event.target.value)}
              />
            </Grid>
          );
        }
        if (field.type === "date") {
          return (
            <Grid item xs={12} sm={6} md={4} key={field.name}>
              <TextField
                type="date"
                label={field.label}
                fullWidth
                size="small"
                InputLabelProps={{ shrink: true }}
                value={value}
                onChange={(event) => onChange(field.name, event.target.value)}
              />
            </Grid>
          );
        }
        if (field.type === "boolean") {
          return (
            <Grid item xs={12} sm={6} md={4} key={field.name}>
              <TextField
                select
                label={field.label}
                fullWidth
                size="small"
                value={value}
                onChange={(event) => onChange(field.name, event.target.value)}
              >
                <MenuItem value="">Any</MenuItem>
                <MenuItem value="true">Yes</MenuItem>
                <MenuItem value="false">No</MenuItem>
              </TextField>
            </Grid>
          );
        }
        const options = field.options ?? (field.optionsSource ? optionsBySource[field.optionsSource] : []) ?? [];
        return (
          <Grid item xs={12} sm={6} md={4} key={field.name}>
            <TextField
              select
              label={field.label}
              fullWidth
              size="small"
              value={value}
              onChange={(event) => onChange(field.name, event.target.value)}
            >
              <MenuItem value="">Any</MenuItem>
              {options.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
        );
      })}
    </Grid>
  );
}
