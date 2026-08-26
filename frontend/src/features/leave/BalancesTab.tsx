import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  MenuItem,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";

import { listEmployees } from "@/api/employees";
import { listCompanyLeaveBalances, listMyLeaveBalances } from "@/api/leave";
import { useAuthStore } from "@/store/authStore";

const CURRENT_YEAR = new Date().getFullYear();
const YEAR_OPTIONS = [CURRENT_YEAR - 1, CURRENT_YEAR, CURRENT_YEAR + 1];

export function BalancesTab() {
  const hasPermission = useAuthStore((state) => state.hasPermission);
  const canViewCompanyBalances = hasPermission("leave", "approve");
  const [year, setYear] = useState(CURRENT_YEAR);
  const [employeeId, setEmployeeId] = useState("");

  const { data: myBalances } = useQuery({
    queryKey: ["leave", "balances", "mine", year],
    queryFn: () => listMyLeaveBalances(year),
  });

  const { data: employees } = useQuery({
    queryKey: ["employees", "all"],
    queryFn: () => listEmployees({ page: 1, page_size: 100 }),
    enabled: canViewCompanyBalances,
  });

  const { data: companyBalances } = useQuery({
    queryKey: ["leave", "balances", "company", year, employeeId],
    queryFn: () => listCompanyLeaveBalances(year, employeeId || undefined),
    enabled: canViewCompanyBalances,
  });

  return (
    <>
      <TextField
        select
        label="Year"
        size="small"
        value={year}
        onChange={(event) => setYear(Number(event.target.value))}
        sx={{ mb: 3, width: 160 }}
      >
        {YEAR_OPTIONS.map((option) => (
          <MenuItem key={option} value={option}>
            {option}
          </MenuItem>
        ))}
      </TextField>

      <Typography variant="h3" sx={{ mb: 1.5 }}>
        My Balances
      </Typography>
      <Paper variant="outlined" sx={{ mb: 4 }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Leave type</TableCell>
              <TableCell align="right">Granted</TableCell>
              <TableCell align="right">Carried forward</TableCell>
              <TableCell align="right">Adjustment</TableCell>
              <TableCell align="right">Used</TableCell>
              <TableCell align="right">Available</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {(myBalances ?? []).map((balance) => (
              <TableRow key={balance.leave_type_id} hover>
                <TableCell>{balance.leave_type_name}</TableCell>
                <TableCell align="right">{balance.granted ?? "Unlimited"}</TableCell>
                <TableCell align="right">{balance.carried_forward}</TableCell>
                <TableCell align="right">{balance.adjustment}</TableCell>
                <TableCell align="right">{balance.used}</TableCell>
                <TableCell align="right">{balance.available ?? "—"}</TableCell>
              </TableRow>
            ))}
            {(myBalances ?? []).length === 0 && (
              <TableRow>
                <TableCell colSpan={6} align="center" sx={{ py: 4, color: "text.secondary" }}>
                  No leave types configured yet.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Paper>

      {canViewCompanyBalances && (
        <>
          <Typography variant="h3" sx={{ mb: 1.5 }}>
            Team Balances
          </Typography>
          <TextField
            select
            label="Employee"
            size="small"
            value={employeeId}
            onChange={(event) => setEmployeeId(event.target.value)}
            sx={{ mb: 2, width: 240 }}
          >
            <MenuItem value="">All employees</MenuItem>
            {(employees?.items ?? []).map((employee) => (
              <MenuItem key={employee.id} value={employee.id}>
                {employee.first_name} {employee.last_name}
              </MenuItem>
            ))}
          </TextField>
          <Paper variant="outlined">
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Employee</TableCell>
                  <TableCell>Leave type</TableCell>
                  <TableCell align="right">Granted</TableCell>
                  <TableCell align="right">Carried forward</TableCell>
                  <TableCell align="right">Used</TableCell>
                  <TableCell align="right">Available</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {(companyBalances ?? []).map((balance, index) => (
                  <TableRow key={`${balance.leave_type_id}-${index}`} hover>
                    <TableCell>{balance.employee_name ?? "—"}</TableCell>
                    <TableCell>{balance.leave_type_name}</TableCell>
                    <TableCell align="right">{balance.granted ?? "Unlimited"}</TableCell>
                    <TableCell align="right">{balance.carried_forward}</TableCell>
                    <TableCell align="right">{balance.used}</TableCell>
                    <TableCell align="right">{balance.available ?? "—"}</TableCell>
                  </TableRow>
                ))}
                {(companyBalances ?? []).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 4, color: "text.secondary" }}>
                      No balances to show.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}
    </>
  );
}
