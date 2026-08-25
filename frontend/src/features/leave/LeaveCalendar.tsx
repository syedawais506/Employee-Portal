import { Box, Chip, Stack, Tooltip, Typography } from "@mui/material";

import type { LeaveRequest } from "@/types";
import { toISODate, weekdayLabels } from "@/utils/timesheetPeriod";

const STATUS_COLOR: Record<string, "success" | "warning" | "default" | "error" | "info"> = {
  pending: "warning",
  manager_approved: "info",
  approved: "success",
  rejected: "error",
  cancelled: "default",
};

interface LeaveCalendarProps {
  days: Date[];
  currentMonth: number;
  weekStartDay: number;
  requestsByDate: Record<string, LeaveRequest[]>;
  holidaysByDate: Record<string, string>;
  onDayClick: (dateIso: string) => void;
  onRequestClick: (request: LeaveRequest) => void;
}

export function LeaveCalendar({
  days,
  currentMonth,
  weekStartDay,
  requestsByDate,
  holidaysByDate,
  onDayClick,
  onRequestClick,
}: LeaveCalendarProps) {
  return (
    <Box>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 1, mb: 1 }}>
        {weekdayLabels(weekStartDay).map((label) => (
          <Typography key={label} variant="caption" color="text.secondary" align="center" sx={{ fontWeight: 600 }}>
            {label}
          </Typography>
        ))}
      </Box>
      <Box sx={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 1 }}>
        {days.map((day) => {
          const dayIso = toISODate(day);
          const inMonth = day.getMonth() === currentMonth;
          const holidayName = holidaysByDate[dayIso];
          const requests = requestsByDate[dayIso] ?? [];

          return (
            <Box
              key={dayIso}
              onClick={() => onDayClick(dayIso)}
              sx={{
                minHeight: 96,
                border: "1px solid",
                borderColor: holidayName ? "secondary.main" : "divider",
                borderRadius: 1,
                p: 1,
                opacity: inMonth ? 1 : 0.4,
                bgcolor: holidayName && inMonth ? "action.hover" : "transparent",
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                gap: 0.5,
              }}
            >
              <Typography variant="caption" color="text.secondary">
                {day.getDate()}
              </Typography>
              {holidayName && (
                <Tooltip title={holidayName}>
                  <Typography variant="caption" color="secondary.main" noWrap>
                    {holidayName}
                  </Typography>
                </Tooltip>
              )}
              <Stack spacing={0.5} sx={{ flexGrow: 1, overflow: "hidden" }}>
                {requests.map((request) => (
                  <Chip
                    key={request.id}
                    label={request.leave_type_name}
                    size="small"
                    color={STATUS_COLOR[request.status]}
                    onClick={(event) => {
                      event.stopPropagation();
                      onRequestClick(request);
                    }}
                    sx={{ justifyContent: "flex-start", maxWidth: "100%" }}
                  />
                ))}
              </Stack>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
