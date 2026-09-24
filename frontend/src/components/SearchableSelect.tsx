import { Autocomplete, TextField, Typography } from "@mui/material";

export interface SearchableSelectOption {
  value: string;
  label: string;
  /** Shown as a second, muted line under the label in the dropdown. */
  subtitle?: string;
  /** Extra terms (code, department, designation, ...) matched as the user types, in addition to the label. */
  searchText?: string;
}

interface SearchableSelectProps {
  label: string;
  options: SearchableSelectOption[];
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  size?: "small" | "medium";
  fullWidth?: boolean;
}

/**
 * Type-ahead replacement for a plain dropdown — filters as you type against
 * the label plus any extra searchText (so e.g. an employee code or
 * department matches even though only the name is shown), not just a
 * prefix/substring match on the visible label alone.
 */
export function SearchableSelect({
  label,
  options,
  value,
  onChange,
  placeholder,
  size = "small",
  fullWidth = true,
}: SearchableSelectProps) {
  const selected = options.find((option) => option.value === value) ?? null;

  return (
    <Autocomplete
      size={size}
      fullWidth={fullWidth}
      options={options}
      value={selected}
      onChange={(_, option) => onChange(option?.value ?? "")}
      getOptionLabel={(option) => option.label}
      isOptionEqualToValue={(option, other) => option.value === other.value}
      filterOptions={(opts, state) => {
        const query = state.inputValue.trim().toLowerCase();
        if (!query) return opts;
        return opts.filter((option) => {
          const corpus = `${option.label} ${option.searchText ?? ""}`.toLowerCase();
          return query.split(/\s+/).every((word) => corpus.includes(word));
        });
      }}
      renderOption={(props, option) => (
        <li {...props} key={option.value}>
          <div>
            <Typography variant="body2">{option.label}</Typography>
            {option.subtitle && (
              <Typography variant="caption" color="text.secondary">
                {option.subtitle}
              </Typography>
            )}
          </div>
        </li>
      )}
      renderInput={(params) => <TextField {...params} label={label} placeholder={placeholder} />}
    />
  );
}
