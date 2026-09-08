import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import SendIcon from "@mui/icons-material/Send";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import { Alert, Avatar, Box, IconButton, Paper, Stack, TextField, Typography } from "@mui/material";

import { sendChatMessage } from "@/api/ai";
import { extractApiErrorMessage } from "@/api/client";
import { PageHeader } from "@/components/PageHeader";
import { useAuthStore } from "@/store/authStore";
import type { ChatMessage } from "@/types";

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <Stack direction="row" justifyContent={isUser ? "flex-end" : "flex-start"} spacing={1}>
      {!isUser && (
        <Avatar sx={{ width: 28, height: 28, bgcolor: "primary.main" }}>
          <SmartToyIcon fontSize="small" />
        </Avatar>
      )}
      <Paper
        variant="outlined"
        sx={{
          p: 1.5,
          maxWidth: "75%",
          bgcolor: isUser ? "primary.main" : "background.paper",
          color: isUser ? "primary.contrastText" : "text.primary",
        }}
      >
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
          {message.content}
        </Typography>
      </Paper>
    </Stack>
  );
}

export function AskHRPage() {
  const fullName = useAuthStore((state) => state.user?.full_name);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content: `Hi${fullName ? ` ${fullName.split(" ")[0]}` : ""}! Ask me about leave types, the holiday calendar, or your own leave balance.`,
    },
  ]);
  const [draft, setDraft] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const chatMutation = useMutation({
    mutationFn: (vars: { message: string; history: ChatMessage[] }) =>
      sendChatMessage(vars.message, vars.history),
    onSuccess: (reply) => {
      setMessages((prev) => [...prev, { role: "assistant", content: reply }]);
      setErrorMessage(null);
    },
    onError: (error) => setErrorMessage(extractApiErrorMessage(error)),
  });

  function handleSend() {
    const message = draft.trim();
    if (!message || chatMutation.isPending) return;
    const history = messages;
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setDraft("");
    chatMutation.mutate({ message, history });
  }

  return (
    <Box>
      <PageHeader title="Ask HR" subtitle="Answers are based on your company's own leave policy and your balances." />

      {errorMessage && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setErrorMessage(null)}>
          {errorMessage}
        </Alert>
      )}

      <Paper variant="outlined" sx={{ p: 2, display: "flex", flexDirection: "column" }}>
        <Stack spacing={1.5} sx={{ maxHeight: "60vh", minHeight: 300, overflowY: "auto", pr: 1 }}>
          {messages.map((message, index) => (
            <MessageBubble key={index} message={message} />
          ))}
          {chatMutation.isPending && (
            <Stack direction="row" spacing={1}>
              <Avatar sx={{ width: 28, height: 28, bgcolor: "primary.main" }}>
                <SmartToyIcon fontSize="small" />
              </Avatar>
              <Typography variant="body2" color="text.secondary" sx={{ alignSelf: "center" }}>
                Thinking…
              </Typography>
            </Stack>
          )}
          <div ref={scrollRef} />
        </Stack>

        <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="e.g. How many sick days do I have left?"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                handleSend();
              }
            }}
          />
          <IconButton color="primary" onClick={handleSend} disabled={!draft.trim() || chatMutation.isPending}>
            <SendIcon />
          </IconButton>
        </Stack>
      </Paper>
    </Box>
  );
}
