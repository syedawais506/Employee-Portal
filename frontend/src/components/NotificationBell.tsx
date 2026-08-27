import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import NotificationsIcon from "@mui/icons-material/Notifications";
import {
  Badge,
  Box,
  Button,
  Divider,
  IconButton,
  ListItemButton,
  ListItemText,
  Menu,
  Stack,
  Typography,
} from "@mui/material";

import { getUnreadCount, listNotifications, markAllNotificationsRead, markNotificationRead } from "@/api/notifications";
import { useNotificationsSocket } from "@/hooks/useNotificationsSocket";
import type { Notification } from "@/types";

export function NotificationBell() {
  useNotificationsSocket();
  const queryClient = useQueryClient();
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const open = Boolean(anchorEl);

  const { data: unreadCount } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: getUnreadCount,
    refetchInterval: 60_000,
  });

  const { data: feed } = useQuery({
    queryKey: ["notifications", "list"],
    queryFn: () => listNotifications({ pageSize: 10 }),
    enabled: open,
  });

  const invalidate = () => queryClient.invalidateQueries({ queryKey: ["notifications"] });

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: invalidate,
  });

  const markAllReadMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidate,
  });

  function handleItemClick(notification: Notification) {
    if (!notification.is_read) markReadMutation.mutate(notification.id);
  }

  return (
    <>
      <IconButton onClick={(event) => setAnchorEl(event.currentTarget)} size="small" aria-label="Notifications">
        <Badge badgeContent={unreadCount ?? 0} color="error" max={99}>
          <NotificationsIcon fontSize="small" />
        </Badge>
      </IconButton>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{ paper: { sx: { width: 380, maxHeight: 480 } } }}
      >
        <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ px: 2, py: 1 }}>
          <Typography variant="body2" fontWeight={600}>
            Notifications
          </Typography>
          <Button
            size="small"
            onClick={() => markAllReadMutation.mutate()}
            disabled={!unreadCount || markAllReadMutation.isPending}
          >
            Mark all read
          </Button>
        </Stack>
        <Divider />
        {(feed?.items ?? []).map((notification) => (
          <ListItemButton
            key={notification.id}
            onClick={() => handleItemClick(notification)}
            sx={{ alignItems: "flex-start", bgcolor: notification.is_read ? "transparent" : "action.hover" }}
          >
            <ListItemText
              primary={notification.title}
              secondary={
                <>
                  {notification.body && (
                    <Typography variant="caption" color="text.secondary" display="block">
                      {notification.body}
                    </Typography>
                  )}
                  <Typography variant="caption" color="text.disabled">
                    {new Date(notification.created_at).toLocaleString()}
                  </Typography>
                </>
              }
            />
          </ListItemButton>
        ))}
        {(feed?.items ?? []).length === 0 && (
          <Box sx={{ px: 2, py: 3, textAlign: "center" }}>
            <Typography variant="body2" color="text.secondary">
              You're all caught up.
            </Typography>
          </Box>
        )}
      </Menu>
    </>
  );
}
