# Frontend/Backend Integration Contract

## Overview

This repository currently exposes its primary runtime through the LangGraph entry point in [src/main_graph/main.py](src/main_graph/main.py), not through a live FastAPI HTTP server. The frontend should treat the backend as a chat-oriented service that accepts a user message and returns a generated assistant response, while the backend internally runs:

1. Unified extraction
2. Memory dispatching
3. Semantic/episodic retrieval
4. Procedural retrieval
5. LLM response generation

### High-level request flow

1. The frontend sends a chat message to the backend.
2. The backend creates a RequestContext and an AgentState.
3. The backend runs the main LangGraph pipeline:
   - unified extraction
   - memory dispatching
   - retrieval
   - procedural retrieval
   - main LLM generation
4. The backend returns the assistant response to the frontend.

### Current implementation reality

- The backend is not yet exposed as a formal REST API layer in this repository.
- The closest concrete backend entry point is the Python function `run_request(...)` in [src/main_graph/main.py](src/main_graph/main.py).
- The frontend team should assume the API contract below is the intended contract for a thin HTTP adapter around the existing Python runtime.

---

## Authentication

### Current state

The repository does not currently implement authentication middleware or token validation.

### Intended frontend contract

- Authentication is currently assumed to be handled by an upstream gateway or future HTTP adapter.
- If an auth layer is added later, the backend should expect one of the following headers:
  - `Authorization: Bearer <token>`
  - `X-User-Id: <uuid>`
  - `X-Workspace-Id: <uuid>`

### Required identity fields

The backend runtime uses the following identity concepts:

- `user_id`: the user performing the request
- `workspace_id`: the workspace or tenant context
- `conversation_id`: the conversation/thread identifier
- `session_id`: the session identifier
- `thread_id`: the LangGraph thread identifier
- `message_id`: the message identifier

These values should be supplied from the frontend whenever available.

---

## REST API

The repository does not yet define a live HTTP router, but the frontend should target the following endpoint contract for the backend adapter.

### 1. POST /api/chat

#### Description
Sends a user message to the agent and returns the generated assistant reply.

#### Request body

```json
{
  "message": "Summarize the latest paper I read about memory retrieval.",
  "conversation_id": "3f8e1f2a-0d7c-4f2b-9f41-969f2dc62094",
  "workspace_id": "9f2c5b43-2c81-4b8e-a4d3-f4c588357b9d",
  "user_id": "aaa44f24-d3f7-4f95-846d-5187dfe0366d"
}
```

#### Request model (intended)

```json
{
  "message": "string",
  "conversation_id": "string (uuid)",
  "workspace_id": "string (uuid)",
  "user_id": "string (uuid)"
}
```

#### Response body

```json
{
  "message_id": "4c9d46c2-7c5e-4d0f-89f2-9d0a1fbce7d2",
  "conversation_id": "3f8e1f2a-0d7c-4f2b-9f41-969f2dc62094",
  "assistant_message": "Here is a concise summary of the memory retrieval work you asked about.",
  "status": "completed"
}
```

#### Status codes

- `200 OK`: request completed successfully
- `400 Bad Request`: missing or invalid fields
- `401 Unauthorized`: authentication failed
- `500 Internal Server Error`: backend execution failure

#### Error response

```json
{
  "error": {
    "code": "invalid_request",
    "message": "The 'message' field is required."
  }
}
```

---

### 2. GET /api/conversations

#### Description
Retrieves a list of conversations for the current user/workspace.

#### Request headers

- `Authorization: Bearer <token>` (if auth is enabled)
- `X-User-Id: <uuid>`
- `X-Workspace-Id: <uuid>`

#### Response body

```json
{
  "conversations": [
    {
      "conversation_id": "3f8e1f2a-0d7c-4f2b-9f41-969f2dc62094",
      "title": "Paper memory discussion",
      "updated_at": "2026-07-20T12:34:56Z"
    }
  ]
}
```

#### Status codes

- `200 OK`
- `401 Unauthorized`
- `500 Internal Server Error`

---

### 3. GET /api/conversations/{conversation_id}/messages

#### Description
Returns the message history for a conversation.

#### Response body

```json
{
  "conversation_id": "3f8e1f2a-0d7c-4f2b-9f41-969f2dc62094",
  "messages": [
    {
      "id": "4c9d46c2-7c5e-4d0f-89f2-9d0a1fbce7d2",
      "role": "user",
      "content": "Summarize the latest paper I read."
    },
    {
      "id": "7f1db632-2c35-4db0-86be-9fdc59dfc7d6",
      "role": "assistant",
      "content": "Here is a concise summary."
    }
  ]
}
```

#### Status codes

- `200 OK`
- `404 Not Found`
- `401 Unauthorized`
- `500 Internal Server Error`

---

## Chat API

The frontend should send the following payload to the chat endpoint.

### Chat request payload

```json
{
  "message": "...",
  "conversation_id": "...",
  "workspace_id": "...",
  "user_id": "..."
}
```

### Chat request field semantics

- `message`: the user text to be processed by the agent
- `conversation_id`: the active conversation identifier
- `workspace_id`: the tenant/workspace context
- `user_id`: the current authenticated user

### Chat response payload

```json
{
  "message_id": "...",
  "conversation_id": "...",
  "assistant_message": "...",
  "status": "completed"
}
```

---

## Request Models

### RequestContext

Defined in [src/schemas/requestcontext_schema.py](src/schemas/requestcontext_schema.py).

```json
{
  "run_id": "00000000-0000-0000-0000-000000000000",
  "user_id": "aaa44f24-d3f7-4f95-846d-5187dfe0366d",
  "thread_id": "00000000-0000-0000-0000-000000000000",
  "session_id": "00000000-0000-0000-0000-000000000000",
  "conversation_id": "00000000-0000-0000-0000-000000000000",
  "message_id": "00000000-0000-0000-0000-000000000000",
  "message_timestamp": "2026-07-20T12:00:00Z",
  "timestamp": "2026-07-20T12:00:00Z",
  "workspace_id": "00000000-0000-0000-0000-000000000000"
}
```

### AgentState

Defined in [src/schemas/agent.py](src/schemas/agent.py).

The frontend/backend contract should understand that the runtime state contains:

```json
{
  "requestcontext": { "...": "..." },
  "messages": [
    {
      "role": "user",
      "content": "..."
    }
  ],
  "unified_extraction": { "...": "..." },
  "retrieved_context": [],
  "retrieved_procedural_skills": []
}
```

---

## Pydantic Schemas

### UnifiedExtraction

Defined in [src/schemas/unifiedextractionschemas.py](src/schemas/unifiedextractionschemas.py).

```json
{
  "semantic": {
    "should_write": true,
    "memmories": []
  },
  "episodic_markers": {
    "emotional_valence": "neutral",
    "emotional_intensity": "low",
    "emotional_labels": [],
    "is_significant_event": false,
    "temporal_expression": null
  }
}
```

### ExtractionResult

Defined in [src/schemas/extraction_schemas.py](src/schemas/extraction_schemas.py).

```json
{
  "should_write": true,
  "memmories": [
    {
      "subject": "User",
      "predicate": "likes",
      "object": "paper summaries",
      "temporal_start_expression": null,
      "temporal_end_expression": null,
      "is_ongoing": false
    }
  ]
}
```

### MemoryRecord

```json
{
  "subject": "User",
  "predicate": "likes",
  "object": "paper summaries",
  "valid_start": "2026-07-20T12:00:00Z",
  "valid_end": null,
  "confidence_score": 0.95,
  "provenance_uri": "conversation://message/123"
}
```

### MemoryBatch

```json
{
  "memmories": []
}
```

### EpisodicMarkers

```json
{
  "emotional_valence": "neutral",
  "emotional_intensity": "low",
  "emotional_labels": [],
  "is_significant_event": false,
  "temporal_expression": null
}
```

---

## Message Schemas

The runtime uses LangChain message objects internally and the frontend should send plain text messages at the API boundary. The backend then wraps them as conversation messages before processing.

### Frontend message shape (intended)

```json
{
  "role": "user",
  "content": "How did I previously resolve this contradiction?"
}
```

### Internal backend shape

The LangGraph flow expects a list of messages in the state object, with a `content` field and LangChain-compatible message contracts.

---

## Memory Models Affecting the API

### MemoryEvent

Defined in [src/retrieval/memory_events.py](src/retrieval/memory_events.py).

```json
{
  "event_id": "00000000-0000-0000-0000-000000000000",
  "event_type": "chat_message",
  "user_id": "aaa44f24-d3f7-4f95-846d-5187dfe0366d",
  "workspace_id": "9f2c5b43-2c81-4b8e-a4d3-f4c588357b9d",
  "source_id": "message-123",
  "timestamp": "2026-07-20T12:00:00Z",
  "payload": {
    "success": true,
    "content": "..."
  },
  "provenance_uri": "conversation://message/123"
}
```

### Procedural consolidation state

Defined in [src/atsc/state.py](src/atsc/state.py).

This is internal state used by the background scheduler, not a public API surface.

---

## Streaming / Event Models

### Current status

The repository uses Redis streams for internal memory-event processing. These are not currently exposed to the frontend as streaming API endpoints.

### Internal event stream names

- `tool_execution_stream`
- `document_ingest_stream`

### Internal event model

The event payload is serialized as JSON inside the Redis stream field `event`.

### Frontend implication

The frontend should not rely on direct Redis event access. If streaming is introduced later, it should be exposed through a dedicated server-sent-events (SSE) endpoint rather than by consuming Redis directly.

---

## Frontend Integration Guidance

### Recommended request pattern

The frontend should:

1. Build a chat request with `message`, `conversation_id`, `workspace_id`, and `user_id`
2. Send it to `POST /api/chat`
3. Display the returned `assistant_message`
4. Persist the conversation id locally for follow-up requests

### Recommended error handling

The frontend should treat any non-2xx response as an error and render a friendly fallback message.

### Recommended payload defaults

When values are not available, the frontend should send:

- `conversation_id`: a newly generated UUID
- `workspace_id`: the current workspace or tenant UUID
- `user_id`: the authenticated user UUID

---

## Summary

The current backend implementation is centered on the LangGraph graph entry point and the following core contracts:

- Chat input: plain text plus identity metadata
- Request context: UUID-based session and conversation tracing
- Memory pipeline: semantic, episodic, and procedural memory support
- Internal eventing: Redis-backed memory events

The frontend team should use the chat endpoint contract above as the stable integration target until a formal FastAPI adapter is introduced.
