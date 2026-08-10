import { MyProjectsPage } from "@/features/projects/MyProjectsPage";
import { ProjectsPage } from "@/features/projects/ProjectsPage";
import { useAuthStore } from "@/store/authStore";

/** Routes to the full management view for roles with project.view, or a
 * read-only "my projects" view for everyone else — matching the original
 * spec's "Employee: View Assigned Projects" without exposing budgets,
 * clients, or other employees' assignments to a plain Employee role. */
export function ProjectsEntryPage() {
  const canViewAllProjects = useAuthStore((state) => state.hasPermission("project", "view"));
  return canViewAllProjects ? <ProjectsPage /> : <MyProjectsPage />;
}
