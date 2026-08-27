import { apiClient } from "@/api/client";
import { useAuthStore } from "@/store/authStore";
import type { Notification, Page } from "@/types";

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

export interface ListNotificationsFilters {
  unreadOnly?: boolean;
  page?: number;
  pageSize?: number;
}

export async function listNotifications(filters: ListNotificationsFilters = {}): Promise<Page<Notification>> {
  const response = await apiClient.get<Page<Notification>>("/notifications", {
    params: {
      unread_only: filters.unreadOnly,
      page: filters.page ?? 1,
      page_size: filters.pageSize ?? 25,
    },
  });
  return response.data;
}

export async function getUnreadCount(): Promise<number> {
  const response = await apiClient.get<{ unread_count: number }>("/notifications/unread-count");
  return response.data.unread_count;
}

export async function markNotificationRead(id: string): Promise<Notification> {
  const response = await apiClient.post<Notification>(`/notifications/${id}/read`);
  return response.data;
}

export async function markAllNotificationsRead(): Promise<number> {
  const response = await apiClient.post<{ marked_read: number }>("/notifications/read-all");
  return response.data.marked_read;
}

/** Same-origin WebSocket URL, mirroring how `apiClient`'s baseURL resolves —
 * relative by default (proxied by Vite in dev, by nginx in Docker), so this
 * just swaps the http(s) scheme for ws(s) rather than hardcoding a host. */
export function getNotificationsWebSocketUrl(): string | null {
  const token = useAuthStore.getState().accessToken;
  if (!token) return null;

  if (/^https?:\/\//.test(API_BASE_URL)) {
    const url = new URL(`${API_BASE_URL}/notifications/ws`);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.searchParams.set("token", token);
    return url.toString();
  }

  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const path = `${API_BASE_URL}/notifications/ws`.replace(/\/{2,}/g, "/");
  return `${wsProtocol}//${window.location.host}${path}?token=${encodeURIComponent(token)}`;
}
