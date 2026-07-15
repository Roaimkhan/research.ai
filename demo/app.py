"""
app.py — Streamlit demo for Synapse research-assistant memory agent.

Layout:
  Main column  — standard chat interface
  Right column — live memory log (extraction, storage, retrieval per turn)
  Sidebar      — "Start New Session" button + memory browser

Run: streamlit run demo/app.py
"""

import streamlit as st
import uuid
import json
import os
import sys

# Ensure project root is on sys.path so we can import memory.py from the demo folder
sys.path.insert(0, os.path.dirname(__file__))
from memory import init_db, store_semantic, retrieve_semantic, store_episodic, retrieve_episodic, get_all_semantic, reset_db

from openai import OpenAI
from dotenv import load_dotenv

# ── Config ───────────────────────────────────────────────────────────────────
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_KEY = os.getenv("GOOGLE_API_KEY", "")
# Use Gemini via the OpenAI-compatible endpoint
client = OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
MODEL = "gemini-2.5-flash"

# ── DB Init ──────────────────────────────────────────────────────────────────
init_db()

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Synapse — Research Memory Agent",
    page_icon="🧠",
    layout="wide",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp { background-color: #0e1117; }

    /* Memory log panel */
    .memory-log {
        background: #1a1d24;
        border: 1px solid #2d3139;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
        font-size: 0.82rem;
        font-family: 'JetBrains Mono', monospace;
    }
    .memory-log .label {
        color: #7c8db5;
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.7rem;
        letter-spacing: 0.05em;
    }
    .log-extracted { border-left: 3px solid #f59e0b; }
    .log-stored    { border-left: 3px solid #10b981; }
    .log-retrieved { border-left: 3px solid #6366f1; }
    .log-car       { border-left: 3px solid #ef4444; }
    .log-none      { border-left: 3px solid #4b5563; }

    /* Session badge */
    .session-badge {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 0.75rem;
        color: #94a3b8;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ───────────────────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "working_memory" not in st.session_state:
    st.session_state.working_memory = {}
if "memory_logs" not in st.session_state:
    st.session_state.memory_logs = []


# ── LLM Helpers ──────────────────────────────────────────────────────────────

def llm_extract(user_message: str) -> dict | None:
    """
    Ask the LLM to extract a single fact from the user message.
    Returns {"concept": str, "fact_value": str} or None.
    """
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": """You are a memory extraction system. Analyze the user's message and determine if it contains a factual statement, preference, or piece of information worth remembering long-term.

If it does, respond with ONLY a JSON object:
{"concept": "short_snake_case_topic", "fact_value": "the actual fact or preference stated"}

If the message is a question, greeting, or contains no memorable fact, respond with ONLY:
null

Examples:
User: "I'm researching Mem0's token efficiency, they achieve about 6.7K tokens per query"
→ {"concept": "mem0_token_efficiency", "fact_value": "Mem0 achieves approximately 6.7K tokens per query"}

User: "What's the weather like?"
→ null

User: "I prefer using Python for data analysis"
→ {"concept": "programming_preference", "fact_value": "User prefers Python for data analysis"}

User: "Actually the number is 8K not 6.7K"
→ {"concept": "mem0_token_efficiency", "fact_value": "Mem0 token usage is actually 8K, not 6.7K"}

Respond with ONLY the JSON or null, nothing else."""},
                {"role": "user", "content": user_message}
            ],
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        if raw.lower() == "null" or raw.lower() == "none":
            return None
        return json.loads(raw)
    except Exception as e:
        st.error(f"Extraction LLM error: {e}")
        return None


def llm_generate(user_message: str, retrieved_facts: list[dict], episodic_hits: list[dict], working_memory: dict) -> str:
    """
    Generate the final response given all context.
    """
    # Build context string
    context_parts = []

    if retrieved_facts:
        facts_text = "\n".join(
            f"- **{f['concept']}** (serial {f['serial']}): {f['fact_value']}"
            for f in retrieved_facts
        )
        context_parts.append(f"## Semantic Memory (long-term facts)\n{facts_text}")

    if episodic_hits:
        episodes_text = "\n".join(
            f"- [{e['role']}] {e['content']} (session: {e['session_id']})"
            for e in episodic_hits
        )
        context_parts.append(f"## Episodic Memory (past conversations)\n{episodes_text}")

    if working_memory:
        wm_text = "\n".join(f"- {k}: {v}" for k, v in working_memory.items())
        context_parts.append(f"## Working Memory (current session context)\n{wm_text}")

    context_block = "\n\n".join(context_parts) if context_parts else "No relevant memories found."

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": f"""You are Synapse, a research assistant with persistent memory.

You have access to the following retrieved context from your memory systems:

{context_block}

Instructions:
1. Use the retrieved context to give personalized, informed answers.
2. If semantic memory contains relevant facts, reference them naturally.
3. If you recall things from past sessions (episodic memory), mention that you remember.
4. If no relevant memory exists, answer normally without mentioning memory.
5. Be concise and helpful. Do not expose raw memory internals to the user."""},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"⚠️ Generation error: {e}"


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧠 Synapse")
    st.markdown(f'<div class="session-badge">Session: <b>{st.session_state.session_id}</b></div>', unsafe_allow_html=True)
    st.markdown("")

    if st.button("🔄 Start New Session", use_container_width=True, type="primary"):
        st.session_state.session_id = str(uuid.uuid4())[:8]
        st.session_state.messages = []
        st.session_state.working_memory = {}
        st.session_state.memory_logs = []
        st.rerun()

    st.markdown("---")
    st.markdown("### 📦 All Stored Concepts")
    all_facts = get_all_semantic()
    if all_facts:
        for f in all_facts:
            with st.expander(f"`{f['concept']}` (serial {f['serial']})"):
                st.write(f"**Value:** {f['fact_value']}")
                st.caption(f"Session: {f['session_id']} | {f['timestamp'][:19]}")
    else:
        st.caption("No semantic memories stored yet.")

    st.markdown("---")
    if st.button("🗑️ Reset All Memory", use_container_width=True):
        reset_db()
        st.session_state.memory_logs = []
        st.rerun()


# ── Main Layout ──────────────────────────────────────────────────────────────
chat_col, log_col = st.columns([3, 2])

# ── Right Column: Memory Log ────────────────────────────────────────────────
with log_col:
    st.markdown("### 📊 Memory Activity Log")
    if not st.session_state.memory_logs:
        st.caption("Memory activity will appear here as you chat...")
    else:
        for log_entry in reversed(st.session_state.memory_logs):
            st.markdown(log_entry, unsafe_allow_html=True)

# ── Left Column: Chat ───────────────────────────────────────────────────────
with chat_col:
    st.markdown("### 💬 Chat")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if user_input := st.chat_input("Ask Synapse anything..."):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        turn_logs = []

        # ── Step 1: Store episodic ──
        store_episodic(user_input, st.session_state.session_id, role="user")

        # ── Step 2: Extract fact ──
        extracted = llm_extract(user_input)
        if extracted and isinstance(extracted, dict) and "concept" in extracted:
            stored = store_semantic(
                extracted["concept"],
                extracted["fact_value"],
                st.session_state.session_id
            )
            # Update working memory
            st.session_state.working_memory[extracted["concept"]] = extracted["fact_value"]

            turn_logs.append(
                f'<div class="memory-log log-extracted">'
                f'<div class="label">🔍 Extracted</div>'
                f'concept: <code>{extracted["concept"]}</code><br>'
                f'value: {extracted["fact_value"]}</div>'
            )
            turn_logs.append(
                f'<div class="memory-log log-stored">'
                f'<div class="label">💾 Stored (Semantic)</div>'
                f'concept: <code>{stored["concept"]}</code> → serial <b>{stored["serial"]}</b></div>'
            )
        else:
            turn_logs.append(
                f'<div class="memory-log log-none">'
                f'<div class="label">🔍 Extraction</div>'
                f'No memorable fact found in this message.</div>'
            )

        # ── Step 3: Retrieve ──
        semantic_hits = retrieve_semantic(user_input)
        episodic_hits = retrieve_episodic(user_input)

        if semantic_hits:
            for hit in semantic_hits:
                turn_logs.append(
                    f'<div class="memory-log log-retrieved">'
                    f'<div class="label">🧠 Retrieved (Semantic — CAR resolved)</div>'
                    f'concept: <code>{hit["concept"]}</code> → serial <b>{hit["serial"]}</b><br>'
                    f'value: {hit["fact_value"]}<br>'
                    f'<small>from session {hit["session_id"]}</small></div>'
                )

        if episodic_hits:
            for hit in episodic_hits:
                turn_logs.append(
                    f'<div class="memory-log log-retrieved">'
                    f'<div class="label">📖 Retrieved (Episodic)</div>'
                    f'[{hit["role"]}] {hit["content"][:100]}...<br>'
                    f'<small>session {hit["session_id"]}</small></div>'
                )

        if not semantic_hits and not episodic_hits:
            turn_logs.append(
                f'<div class="memory-log log-none">'
                f'<div class="label">🔎 Retrieval</div>'
                f'No relevant memories found for this query.</div>'
            )

        # ── Step 4: Generate response ──
        response = llm_generate(
            user_input,
            semantic_hits,
            episodic_hits,
            st.session_state.working_memory
        )

        # Store assistant response as episodic too
        store_episodic(response, st.session_state.session_id, role="assistant")

        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

        # Add logs for this turn
        st.session_state.memory_logs.extend(turn_logs)

        # Rerun to update the log column
        st.rerun()
