import { Box, Chip, Stack, Typography } from "@mui/material";

import type { TimesheetEntry } from "@/types";
import { toISODate, weekdayLabels } from "@/utils/timesheetPeriod";

interface TimesheetCalendarProps {
  days: Date[];
  currentMonth: number;
  periodStart: Date;
  periodEnd: Date;
  weekStartDay: number;
  entriesByDate: Record<string, TimesheetEntry[]>;
  warnOnWeekend: boolean;
  isLocked: boolean;
  onDayClick: (dateIso: string) => void;
  onEntryClick: (entry: TimesheetEntry) => void;
}

export function TimesheetCalendar({
  days,
  currentMonth,
  periodStart,
  periodEnd,
  weekStartDay,
  entriesByDate,
  warnOnWeekend,
  isLocked,
  onDayClick,
  onEntryClick,
}: TimesheetCalendarProps) {
  const periodStartIso = toISODate(periodStart);
  const periodEndIso = toISODate(periodEnd);

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
          const inActivePeriod = dayIso >= periodStartIso && dayIso <= periodEndIso;
          const isWeekend = day.getDay() === 0 || day.getDay() === 6;
          const entries = entriesByDate[dayIso] ?? [];
          const totalHours = entries.reduce((sum, e) => sum + Number(e.hours), 0);
          const clickable = inActivePeriod && !isLocked;

          return (
            <Box
              key={dayIso}
              onClick={() => clickable && onDayClick(dayIso)}
              sx={{
                minHeight: 104,
                border: "1px solid",
                borderColor: inActivePeriod ? "primary.main" : "divider",
                borderRadius: 1,
                p: 1,
                opacity: inMonth ? 1 : 0.4,
                bgcolor: isWeekend && warnOnWeekend && inMonth ? "action.hover" : "transparent",
                cursor: clickable ? "pointer" : "default",
                display: "flex",
                flexDirection: "column",
                gap: 0.5,
              }}
            >
              <Typography variant="caption" color={inActivePeriod ? "primary.main" : "text.secondary"}>
                {day.getDate()}
              </Typography>
              <Stack spacing={0.5} sx={{ flexGrow: 1, overflow: "hidden" }}>
                {entries.map((entry) => (
                  <Chip
                    key={entry.id}
                    label={`${entry.project_name}: ${entry.hours}h`}
                    size="small"
                    color={entry.status === "rejected" ? "error" : entry.status === "approved" ? "success" : "default"}
                    onClick={(event) => {
                      event.stopPropagation();
                      if (inActivePeriod && !isLocked) onEntryClick(entry);
                    }}
                    sx={{ justifyContent: "flex-start", maxWidth: "100%" }}
                  />
                ))}
              </Stack>
              {totalHours > 0 && (
                <Typography variant="caption" color="text.secondary">
                  {totalHours.toFixed(2)}h
                </Typography>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}
