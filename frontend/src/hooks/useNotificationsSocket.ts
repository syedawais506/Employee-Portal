import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { getNotificationsWebSocketUrl } from "@/api/notifications";
import { useAuthStore } from "@/store/authStore";

const RECONNECT_DELAY_MS = 3000;

/** Opens a live WebSocket connection for the current user and invalidates
 * the notification queries whenever a push arrives, so the bell badge and
 * dropdown feed update without polling. REST stays the source of truth —
 * this is additive, not required for correctness (a page refresh always
 * shows the real state via GET /notifications). */
export function useNotificationsSocket(): void {
  const queryClient = useQueryClient();
  const accessToken = useAuthStore((state) => state.accessToken);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!accessToken) return undefined;

    let cancelled = false;

    function connect() {
      if (cancelled) return;
      const url = getNotificationsWebSocketUrl();
      if (!url) return;

      const socket = new WebSocket(url);
      socketRef.current = socket;

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data as string);
          if (message.type === "notification") {
            queryClient.invalidateQueries({ queryKey: ["notifications"] });
          }
        } catch {
          // ignore malformed frames
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      };
    }

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      socketRef.current?.close();
    };
  }, [accessToken, queryClient]);
}
