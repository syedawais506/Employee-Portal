import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/layouts/AppLayout";
import { AuthLayout } from "@/layouts/AuthLayout";
import { ForgotPasswordPage } from "@/features/auth/ForgotPasswordPage";
import { LoginPage } from "@/features/auth/LoginPage";
import { ResetPasswordPage } from "@/features/auth/ResetPasswordPage";
import { AssetsPage } from "@/features/assets/AssetsPage";
import { AttendancePage } from "@/features/attendance/AttendancePage";
import { CompanyListPage } from "@/features/companies/CompanyListPage";
import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { DepartmentListPage } from "@/features/departments/DepartmentListPage";
import { EmployeeDetailPage } from "@/features/employees/EmployeeDetailPage";
import { EmployeeListPage } from "@/features/employees/EmployeeListPage";
import { IntegrationsPage } from "@/features/integrations/IntegrationsPage";
import { LeavePage } from "@/features/leave/LeavePage";
import { OnboardingPage } from "@/features/onboarding/OnboardingPage";
import { OnboardingReviewPage } from "@/features/onboarding/OnboardingReviewPage";
import { PublicOnboardingPage } from "@/features/onboarding/PublicOnboardingPage";
import { MyProfilePage } from "@/features/profile/MyProfilePage";
import { ProjectDetailPage } from "@/features/projects/ProjectDetailPage";
import { ProjectsEntryPage } from "@/features/projects/ProjectsEntryPage";
import { ReportsPage } from "@/features/reports/ReportsPage";
import { RoleListPage } from "@/features/roles/RoleListPage";
import { TimesheetsPage } from "@/features/timesheets/TimesheetsPage";
import { ProtectedRoute, RequirePermission, RequireSuperAdmin } from "@/routes/ProtectedRoute";

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
          { path: "/attendance", element: <AttendancePage /> },
          { path: "/projects", element: <ProjectsEntryPage /> },
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
          { path: "/assets", element: <AssetsPage /> },
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
