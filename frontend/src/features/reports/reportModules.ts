import type { ReportModule } from "@/types";

export interface ReportFieldOption {
  value: string;
  label: string;
}

export interface ReportFieldConfig {
  name: string;
  label: string;
  type: "text" | "date" | "select" | "boolean";
  options?: ReportFieldOption[];
  optionsSource?: "department" | "employee" | "project" | "client" | "leaveType" | "assetType";
}

const LOCATION_OPTIONS: ReportFieldOption[] = [
  { value: "United States", label: "United States" },
  { value: "India", label: "India" },
];

export interface ReportModuleConfig {
  value: ReportModule;
  label: string;
  fields: ReportFieldConfig[];
}

export const REPORT_MODULES: ReportModuleConfig[] = [
  {
    value: "employee",
    label: "Employees",
    fields: [
      { name: "search", label: "Search (name/email/code)", type: "text" },
      { name: "department_id", label: "Department", type: "select", optionsSource: "department" },
      {
        name: "status",
        label: "Status",
        type: "select",
        options: [
          { value: "active", label: "Active" },
          { value: "on_leave", label: "On Leave" },
          { value: "exited", label: "Exited" },
        ],
      },
      { name: "manager_id", label: "Manager", type: "select", optionsSource: "employee" },
      {
        name: "employment_type",
        label: "Employment Type",
        type: "select",
        options: [
          { value: "full_time", label: "Full-time" },
          { value: "part_time", label: "Part-time" },
          { value: "contract", label: "Contract" },
          { value: "intern", label: "Intern" },
        ],
      },
      { name: "location", label: "Location", type: "select", options: LOCATION_OPTIONS },
      { name: "joining_date_from", label: "Joined from", type: "date" },
      { name: "joining_date_to", label: "Joined to", type: "date" },
    ],
  },
  {
    value: "department",
    label: "Departments",
    fields: [
      { name: "search", label: "Search (name)", type: "text" },
      { name: "parent_department_id", label: "Parent department", type: "select", optionsSource: "department" },
      { name: "created_from", label: "Created from", type: "date" },
      { name: "created_to", label: "Created to", type: "date" },
    ],
  },
  {
    value: "project",
    label: "Projects",
    fields: [
      {
        name: "status",
        label: "Status",
        type: "select",
        options: [
          { value: "active", label: "Active" },
          { value: "on_hold", label: "On Hold" },
          { value: "completed", label: "Completed" },
          { value: "cancelled", label: "Cancelled" },
        ],
      },
      { name: "client_id", label: "Client", type: "select", optionsSource: "client" },
      { name: "is_billable", label: "Billable only", type: "boolean" },
      { name: "start_date_from", label: "Start date from", type: "date" },
      { name: "start_date_to", label: "Start date to", type: "date" },
    ],
  },
  {
    value: "timesheet",
    label: "Timesheets",
    fields: [
      { name: "date_from", label: "Date from", type: "date" },
      { name: "date_to", label: "Date to", type: "date" },
      { name: "employee_id", label: "Employee", type: "select", optionsSource: "employee" },
      { name: "project_id", label: "Project", type: "select", optionsSource: "project" },
      { name: "location", label: "Location", type: "select", options: LOCATION_OPTIONS },
    ],
  },
  {
    value: "leave",
    label: "Leave",
    fields: [
      { name: "date_from", label: "Date from", type: "date" },
      { name: "date_to", label: "Date to", type: "date" },
      { name: "employee_id", label: "Employee", type: "select", optionsSource: "employee" },
      { name: "leave_type_id", label: "Leave type", type: "select", optionsSource: "leaveType" },
      {
        name: "status",
        label: "Status",
        type: "select",
        options: [
          { value: "pending", label: "Pending" },
          { value: "manager_approved", label: "Awaiting HR" },
          { value: "approved", label: "Approved" },
          { value: "rejected", label: "Rejected" },
          { value: "cancelled", label: "Cancelled" },
        ],
      },
    ],
  },
  {
    value: "asset",
    label: "Assets",
    fields: [
      { name: "asset_type_id", label: "Asset type", type: "select", optionsSource: "assetType" },
      {
        name: "status",
        label: "Status",
        type: "select",
        options: [
          { value: "available", label: "Available" },
          { value: "assigned", label: "Assigned" },
          { value: "retired", label: "Retired" },
          { value: "lost", label: "Lost" },
          { value: "damaged", label: "Damaged" },
        ],
      },
    ],
  },
];
