import type { TimesheetPeriodType } from "@/types";

export function toISODate(d: Date): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function fromISODate(value: string): Date {
  const [year, month, day] = value.split("-").map(Number);
  return new Date(year, month - 1, day);
}

/** Mirrors compute_period_bounds() in app/services/timesheet_service.py so the
 * period navigator always shows exactly what a submit action would capture. */
export function computePeriodBounds(periodType: TimesheetPeriodType, weekStartDay: number, refDate: Date): [Date, Date] {
  if (periodType === "daily") {
    return [refDate, refDate];
  }
  if (periodType === "weekly") {
    const pyWeekday = (refDate.getDay() + 6) % 7; // JS Sunday=0 -> Python Monday=0 convention
    const offset = ((pyWeekday - weekStartDay) % 7 + 7) % 7;
    const start = new Date(refDate);
    start.setDate(start.getDate() - offset);
    const end = new Date(start);
    end.setDate(end.getDate() + 6);
    return [start, end];
  }
  const start = new Date(refDate.getFullYear(), refDate.getMonth(), 1);
  const end = new Date(refDate.getFullYear(), refDate.getMonth() + 1, 0);
  return [start, end];
}

export function shiftPeriod(periodType: TimesheetPeriodType, refDate: Date, direction: 1 | -1): Date {
  const next = new Date(refDate);
  if (periodType === "daily") {
    next.setDate(next.getDate() + direction);
  } else if (periodType === "weekly") {
    next.setDate(next.getDate() + direction * 7);
  } else {
    next.setMonth(next.getMonth() + direction);
  }
  return next;
}

export function formatPeriodLabel(start: Date, end: Date): string {
  const startLabel = start.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  if (toISODate(start) === toISODate(end)) return startLabel;
  const endLabel = end.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  return `${startLabel} – ${endLabel}`;
}

export function startOfWeek(date: Date, weekStartDay: number): Date {
  const pyWeekday = (date.getDay() + 6) % 7;
  const offset = ((pyWeekday - weekStartDay) % 7 + 7) % 7;
  const start = new Date(date);
  start.setDate(start.getDate() - offset);
  return start;
}

/** Always a full calendar-month grid (padded to whole weeks), regardless of
 * the company's configured period type — the active submission period is
 * highlighted inside it, but the surrounding month stays visible for context. */
export function getMonthGridDates(refDate: Date, weekStartDay: number): Date[] {
  const firstOfMonth = new Date(refDate.getFullYear(), refDate.getMonth(), 1);
  const lastOfMonth = new Date(refDate.getFullYear(), refDate.getMonth() + 1, 0);
  const gridStart = startOfWeek(firstOfMonth, weekStartDay);
  const gridEnd = startOfWeek(lastOfMonth, weekStartDay);
  gridEnd.setDate(gridEnd.getDate() + 6);

  const dates: Date[] = [];
  const cursor = new Date(gridStart);
  while (cursor <= gridEnd) {
    dates.push(new Date(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return dates;
}

export function weekdayLabels(weekStartDay: number): string[] {
  const labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  return [...labels.slice(weekStartDay), ...labels.slice(0, weekStartDay)];
}
