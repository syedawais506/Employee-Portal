from pydantic import BaseModel, Field

VALID_CHAT_ROLES = {"user", "assistant"}


class ChatMessage(BaseModel):
    role: str = Field(pattern=r"^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Prior turns of the same conversation — kept client-side only (see
    # docs/ROADMAP.md Phase 13), replayed on every request since this
    # endpoint is stateless. Capped to keep the context sent to the LLM
    # bounded regardless of how long a conversation runs.
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    reply: str
