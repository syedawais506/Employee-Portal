import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";

import { updateRolePermissions } from "@/api/roles";
import { extractApiErrorMessage } from "@/api/client";
import type { PermissionCatalogEntry, Role } from "@/types";

interface PermissionMatrixEditorProps {
  role: Role;
  catalog: PermissionCatalogEntry[];
}

export function PermissionMatrixEditor({ role, catalog }: PermissionMatrixEditorProps) {
  const queryClient = useQueryClient();
  const [grants, setGrants] = useState<Set<string>>(new Set());

  useEffect(() => {
    setGrants(new Set(role.permissions.filter((p) => p.granted).map((p) => `${p.module}.${p.action}`)));
  }, [role]);

  const mutation = useMutation({
    mutationFn: () =>
      updateRolePermissions(
        role.id,
        catalog.flatMap((entry) =>
          entry.actions.map((action) => ({
            module: entry.module,
            action,
            granted: grants.has(`${entry.module}.${action}`),
          })),
        ),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["roles"] }),
  });

  function toggle(module: string, action: string) {
    const key = `${module}.${action}`;
    setGrants((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="h3">{role.name}</Typography>
          {role.is_system && <Chip label="System role" size="small" />}
        </Stack>
        <Button
          variant="contained"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
        >
          Save permissions
        </Button>
      </Stack>

      {mutation.isError && <Alert severity="error" sx={{ mb: 2 }}>{extractApiErrorMessage(mutation.error)}</Alert>}
      {mutation.isSuccess && <Alert severity="success" sx={{ mb: 2 }}>Permissions updated.</Alert>}

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Module</TableCell>
              {["view", "create", "update", "delete", "approve", "reject", "export", "import"].map((action) => (
                <TableCell key={action} align="center">
                  {action}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {catalog.map((entry) => (
              <TableRow key={entry.module} hover>
                <TableCell sx={{ textTransform: "capitalize" }}>{entry.module}</TableCell>
                {["view", "create", "update", "delete", "approve", "reject", "export", "import"].map((action) => {
                  const supported = entry.actions.includes(action);
                  return (
                    <TableCell key={action} align="center">
                      {supported ? (
                        <Checkbox
                          size="small"
                          checked={grants.has(`${entry.module}.${action}`)}
                          onChange={() => toggle(entry.module, action)}
                        />
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
}
