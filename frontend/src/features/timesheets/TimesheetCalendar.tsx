import { Box, Chip, Stack, Typography, useMediaQuery, useTheme } from "@mui/material";

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
  onDayClick: (dateIso: string) => void;
  onEntryClick: (entry: TimesheetEntry) => void;
}

const WEEKDAY_FULL = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export function TimesheetCalendar({
  days,
  currentMonth,
  periodStart,
  periodEnd,
  weekStartDay,
  entriesByDate,
  warnOnWeekend,
  onDayClick,
  onEntryClick,
}: TimesheetCalendarProps) {
  const theme = useTheme();
  // A 7-column month grid can't fit legibly on a phone-width screen, so
  // mobile gets an agenda-style vertical list of the same days instead.
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const periodStartIso = toISODate(periodStart);
  const periodEndIso = toISODate(periodEnd);

  function entryChips(entries: TimesheetEntry[]) {
    return entries.map((entry) => {
      const entryEditable = entry.status === "draft" || entry.status === "rejected";
      return (
        <Chip
          key={entry.id}
          label={`${entry.project_name}: ${entry.hours}h`}
          size="small"
          color={entry.status === "rejected" ? "error" : entry.status === "approved" ? "success" : "default"}
          onClick={(event) => {
            event.stopPropagation();
            if (entryEditable) onEntryClick(entry);
          }}
          sx={{ justifyContent: "flex-start", maxWidth: "100%" }}
        />
      );
    });
  }

  if (isMobile) {
    return (
      <Stack spacing={1}>
        {days
          .filter((day) => day.getMonth() === currentMonth)
          .map((day) => {
            const dayIso = toISODate(day);
            const inActivePeriod = dayIso >= periodStartIso && dayIso <= periodEndIso;
            const isWeekend = day.getDay() === 0 || day.getDay() === 6;
            const entries = entriesByDate[dayIso] ?? [];
            const totalHours = entries.reduce((sum, e) => sum + Number(e.hours), 0);

            return (
              <Box
                key={dayIso}
                onClick={() => inActivePeriod && onDayClick(dayIso)}
                sx={{
                  border: "1px solid",
                  borderColor: inActivePeriod ? "primary.main" : "divider",
                  borderRadius: 1,
                  p: 1.5,
                  bgcolor: isWeekend && warnOnWeekend ? "action.hover" : "transparent",
                  cursor: inActivePeriod ? "pointer" : "default",
                }}
              >
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="body2" fontWeight={600} color={inActivePeriod ? "primary.main" : "text.primary"}>
                    {WEEKDAY_FULL[day.getDay()]}, {day.toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                  </Typography>
                  {totalHours > 0 && (
                    <Typography variant="caption" color="text.secondary">
                      {totalHours.toFixed(2)}h
                    </Typography>
                  )}
                </Stack>
                {entries.length > 0 && (
                  <Stack direction="row" flexWrap="wrap" spacing={0.5} sx={{ mt: 1, rowGap: 0.5 }}>
                    {entryChips(entries)}
                  </Stack>
                )}
              </Box>
            );
          })}
      </Stack>
    );
  }

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
          const clickable = inActivePeriod;

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
                {entryChips(entries)}
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
