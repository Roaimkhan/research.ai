from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.clients.qwen_client import qwen_client
from src.logging import get_logger
from src.prompts import MAIN_SYSTEM_PROMPT
from src.schemas import AgentState

logger = get_logger(__name__)

def main_llm_node(state: Dict[str, Any]) -> Dict[str, Any]:
    # 1. Pull the messages out of your graph state
    messages = state.get("messages", [])
    if not messages:
        raise ValueError("No messages found in the graph state.")

    logger.info("LLM node processing", extra={"message_count": len(messages)})

    # 2. Call Qwen directly using your custom client method
    response = qwen_client.call_qwen(messages=messages)
    # 3. Extract the raw string text using the native SDK path
    ai_text = response.choices[0].message.content
    print(f"AI: {ai_text}")
    logger.info("LLM response generated", extra={"response_length": len(ai_text)})

    # 4. Append the response message back to the graph's message history
    # We construct a simple message dict so LangGraph updates state cleanly
    new_message = {"role": "assistant", "content": ai_text}
    
    return {
        "messages": messages + [new_message]
    }