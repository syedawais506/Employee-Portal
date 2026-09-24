import { SearchableSelect } from "@/components/SearchableSelect";
import type { EmployeeSummary } from "@/types";

interface EmployeeAutocompleteProps {
  employees: EmployeeSummary[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
  emptyOptionLabel?: string;
}

/**
 * Type-ahead employee picker — matches as you type against name, employee
 * code, designation, department, and location, not just the visible name.
 */
export function EmployeeAutocomplete({
  employees,
  value,
  onChange,
  label = "Employee",
  emptyOptionLabel = "All employees",
}: EmployeeAutocompleteProps) {
  const options = employees.map((employee) => {
    const subtitleParts = [employee.employee_code, employee.designation, employee.department?.name].filter(
      Boolean,
    );
    return {
      value: employee.id,
      label: `${employee.first_name} ${employee.last_name}`,
      subtitle: subtitleParts.join(" · "),
      searchText: [
        employee.employee_code,
        employee.designation,
        employee.department?.name,
        employee.location,
      ]
        .filter(Boolean)
        .join(" "),
    };
  });

  return (
    <SearchableSelect
      label={label}
      placeholder={emptyOptionLabel}
      options={options}
      value={value}
      onChange={onChange}
    />
  );
}
