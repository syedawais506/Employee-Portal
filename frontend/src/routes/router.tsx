import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/layouts/AppLayout";
import { AuthLayout } from "@/layouts/AuthLayout";
import { ProtectedRoute, RequireNotSuperAdmin, RequirePermission, RequireSuperAdmin } from "@/routes/ProtectedRoute";

// Every page is its own chunk, only fetched when its route is actually
// visited, instead of one >500KB bundle shipped on first load regardless of
// which page (if any) the user lands on. See App.tsx for the Suspense
// boundary that covers all of these.
const ForgotPasswordPage = lazy(() => import("@/features/auth/ForgotPasswordPage").then((m) => ({ default: m.ForgotPasswordPage })));
const LoginPage = lazy(() => import("@/features/auth/LoginPage").then((m) => ({ default: m.LoginPage })));
const ResetPasswordPage = lazy(() => import("@/features/auth/ResetPasswordPage").then((m) => ({ default: m.ResetPasswordPage })));
const AskHRPage = lazy(() => import("@/features/ai/AskHRPage").then((m) => ({ default: m.AskHRPage })));
const AssetsPage = lazy(() => import("@/features/assets/AssetsPage").then((m) => ({ default: m.AssetsPage })));
const AttendancePage = lazy(() => import("@/features/attendance/AttendancePage").then((m) => ({ default: m.AttendancePage })));
const CompanyListPage = lazy(() => import("@/features/companies/CompanyListPage").then((m) => ({ default: m.CompanyListPage })));
const DashboardPage = lazy(() => import("@/features/dashboard/DashboardPage").then((m) => ({ default: m.DashboardPage })));
const DepartmentListPage = lazy(() => import("@/features/departments/DepartmentListPage").then((m) => ({ default: m.DepartmentListPage })));
const EmployeeDetailPage = lazy(() => import("@/features/employees/EmployeeDetailPage").then((m) => ({ default: m.EmployeeDetailPage })));
const EmployeeListPage = lazy(() => import("@/features/employees/EmployeeListPage").then((m) => ({ default: m.EmployeeListPage })));
const IntegrationsPage = lazy(() => import("@/features/integrations/IntegrationsPage").then((m) => ({ default: m.IntegrationsPage })));
const LeavePage = lazy(() => import("@/features/leave/LeavePage").then((m) => ({ default: m.LeavePage })));
const OnboardingPage = lazy(() => import("@/features/onboarding/OnboardingPage").then((m) => ({ default: m.OnboardingPage })));
const OnboardingReviewPage = lazy(() => import("@/features/onboarding/OnboardingReviewPage").then((m) => ({ default: m.OnboardingReviewPage })));
const PublicOnboardingPage = lazy(() => import("@/features/onboarding/PublicOnboardingPage").then((m) => ({ default: m.PublicOnboardingPage })));
const MyProfilePage = lazy(() => import("@/features/profile/MyProfilePage").then((m) => ({ default: m.MyProfilePage })));
const ProjectDetailPage = lazy(() => import("@/features/projects/ProjectDetailPage").then((m) => ({ default: m.ProjectDetailPage })));
const ProjectsEntryPage = lazy(() => import("@/features/projects/ProjectsEntryPage").then((m) => ({ default: m.ProjectsEntryPage })));
const ReportsPage = lazy(() => import("@/features/reports/ReportsPage").then((m) => ({ default: m.ReportsPage })));
const RoleListPage = lazy(() => import("@/features/roles/RoleListPage").then((m) => ({ default: m.RoleListPage })));
const TimesheetsPage = lazy(() => import("@/features/timesheets/TimesheetsPage").then((m) => ({ default: m.TimesheetsPage })));

export const router = createBrowserRouter([
  { path: "/onboarding/:token", element: <PublicOnboardingPage /> },
  {
    element: <AuthLayout />,
    children: [
      { path: "/login", element: <LoginPage /> },
      { path: "/forgot-password", element: <ForgotPasswordPage /> },
      { path: "/reset-password", element: <ResetPasswordPage /> },
    ],
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppLayout />,
        children: [
          { path: "/", element: <DashboardPage /> },
          { path: "/profile", element: <MyProfilePage /> },
          {
            element: <RequirePermission module="employee" action="view" />,
            children: [
              { path: "/employees", element: <EmployeeListPage /> },
              { path: "/employees/:id", element: <EmployeeDetailPage /> },
            ],
          },
          {
            element: <RequirePermission module="department" action="view" />,
            children: [{ path: "/departments", element: <DepartmentListPage /> }],
          },
          {
            element: <RequirePermission module="role" action="view" />,
            children: [{ path: "/roles", element: <RoleListPage /> }],
          },
          {
            element: <RequirePermission module="onboarding" action="view" />,
            children: [
              { path: "/onboarding", element: <OnboardingPage /> },
              { path: "/onboarding/review/:employeeId", element: <OnboardingReviewPage /> },
            ],
          },
          {
            element: <RequireNotSuperAdmin />,
            children: [
              { path: "/attendance", element: <AttendancePage /> },
              { path: "/projects", element: <ProjectsEntryPage /> },
              { path: "/assets", element: <AssetsPage /> },
              { path: "/ask-hr", element: <AskHRPage /> },
            ],
          },
          {
            element: <RequirePermission module="project" action="view" />,
            children: [{ path: "/projects/:id", element: <ProjectDetailPage /> }],
          },
          {
            element: <RequirePermission module="timesheet" action="view" />,
            children: [{ path: "/timesheets", element: <TimesheetsPage /> }],
          },
          {
            element: <RequirePermission module="leave" action="view" />,
            children: [{ path: "/leave", element: <LeavePage /> }],
          },
          {
            element: <RequirePermission module="report" action="view" />,
            children: [{ path: "/reports", element: <ReportsPage /> }],
          },
          {
            element: <RequirePermission module="company" action="configure" />,
            children: [{ path: "/integrations", element: <IntegrationsPage /> }],
          },
          {
            element: <RequireSuperAdmin />,
            children: [{ path: "/companies", element: <CompanyListPage /> }],
          },
        ],
      },
    ],
  },
]);
