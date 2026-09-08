import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore } from "@/store/authStore";
import type { CurrentUser } from "@/types";

function buildUser(overrides: Partial<CurrentUser> = {}): CurrentUser {
  return {
    id: "user-1",
    email: "admin@acme-demo.com",
    company_id: "company-1",
    is_super_admin: false,
    is_verified: true,
    permissions: ["employee.view", "employee.create"],
    employee_id: "employee-1",
    full_name: "Alex Admin",
    ai_chatbot_enabled: false,
    ...overrides,
  };
}

describe("useAuthStore.hasPermission", () => {
  beforeEach(() => {
    useAuthStore.setState({ accessToken: null, user: null, isHydrating: false });
  });

  it("returns false when no user is logged in", () => {
    expect(useAuthStore.getState().hasPermission("employee", "view")).toBe(false);
  });

  it("returns true only for permissions the user's roles were granted", () => {
    useAuthStore.getState().setSession("token", buildUser());
    expect(useAuthStore.getState().hasPermission("employee", "view")).toBe(true);
    expect(useAuthStore.getState().hasPermission("employee", "delete")).toBe(false);
  });

  it("grants every permission to a super admin regardless of the permissions list", () => {
    useAuthStore.getState().setSession("token", buildUser({ is_super_admin: true, permissions: [] }));
    expect(useAuthStore.getState().hasPermission("employee", "delete")).toBe(true);
  });

  it("clearSession removes the token and user", () => {
    useAuthStore.getState().setSession("token", buildUser());
    useAuthStore.getState().clearSession();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
  });
});
