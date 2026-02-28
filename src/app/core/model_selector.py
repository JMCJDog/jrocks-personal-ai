"""Model Selector — Intelligent automatic model routing.

Analyzes incoming messages and selects the optimal model based on:
- Task complexity (coding, reasoning, analysis → qwen2.5:14b)
- Content type (opinions, controversy, casual chat → dolphin3)
- Conversation context
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ── Model definitions ──────────────────────────────────────────────────────────

SMART_MODEL = "qwen2.5:14b"      # Complex reasoning, coding, analysis
UNCENSORED_MODEL = "dolphin3"    # Unfiltered opinions, casual chat
FAST_MODEL = "llama3.2"          # Quick factual fallback


# ── Keyword patterns per routing category ─────────────────────────────────────

# Triggers for SMART_MODEL (qwen2.5:14b)
_SMART_PATTERNS = [
    # Code & engineering
    r"\b(code|debug|function|class|algorithm|api|sql|query|regex|script|deploy|docker|git)\b",
    r"\b(python|javascript|typescript|rust|golang|java|c\+\+|bash|powershell)\b",
    r"\b(architecture|design pattern|microservice|database|schema|refactor)\b",
    # Deep reasoning
    r"\b(explain|analyze|compare|summarize|research|investigate|pros and cons)\b",
    r"\b(how does|why does|what is the difference|walk me through|step by step)\b",
    r"\b(business plan|strategy|financial|market analysis|valuation|investment|fintech|portfolio management)\b",
    r"\b(irr|npv|moic|cap table|waterfall|tokenized|secondary market|private equity|venture capital|alternative investments)\b",
    r"\b(sec rule|reg d|finra|accredited investor|qualified purchaser|aml|kyc)\b",
    r"\b(math|calculate|equation|formula|proof|statistics|probability)\b",
    # Long-form tasks
    r"\b(write a report|create a document|draft a|generate a plan|outline)\b",
]

# Triggers for UNCENSORED_MODEL (dolphin3)
_UNCENSORED_PATTERNS = [
    # Opinion & controversy
    r"\b(what do you think|your opinion|your take|do you like|do you hate)\b",
    r"\b(trump|biden|musk|politics|political|democrat|republican|liberal|conservative)\b",
    r"\b(controversial|unpopular opinion|hot take|debate|argue)\b",
    r"\b(rant|roast|trash talk|call out|honest thoughts)\b",
    # Casual / personal
    r"\b(what's up|how are you|hey|yo|dude|bro|man)\b",
    r"\b(funny|joke|meme|sarcastic|sarcasm|dark humor)\b",
    r"\b(feel|feeling|emotion|mood|vibe|energy)\b",
    # Unfiltered / edgy
    r"\b(no filter|unfiltered|raw|honest|blunt|brutal|real talk)\b",
]

# Compile for performance
_SMART_RE = re.compile("|".join(_SMART_PATTERNS), re.IGNORECASE)
_UNCENSORED_RE = re.compile("|".join(_UNCENSORED_PATTERNS), re.IGNORECASE)


class ModelSelector:
    """Selects the optimal model for a given message.

    Routing logic (in priority order):
    1. Explicit model override in request → use that
    2. Strong technical/reasoning signals → qwen2.5:14b
    3. Opinion/casual/controversial signals → dolphin3
    4. Message length heuristic (>200 chars) → qwen2.5:14b (complex)
    5. Default → qwen2.5:14b (best general purpose)
    """

    def select(
        self,
        message: str,
        model_override: Optional[str] = None,
        conversation_history: Optional[list] = None,
    ) -> str:
        """Select the best model for the given message.

        Args:
            message: The user's message.
            model_override: Explicit model name from the request (takes priority).
            conversation_history: Optional list of prior messages for context.

        Returns:
            str: The Ollama model name to use.
        """
        # 1. Explicit override always wins
        if model_override:
            logger.debug(f"[ModelSelector] Using explicit override: {model_override}")
            return model_override

        # 2. Score the message
        smart_score = len(_SMART_RE.findall(message))
        uncensored_score = len(_UNCENSORED_RE.findall(message))

        # 3. Length bonus — longer messages tend to be complex tasks
        if len(message) > 200:
            smart_score += 2

        # 4. If conversation history is mostly opinion/personal, lean uncensored
        if conversation_history:
            recent = " ".join(
                m.get("content", "") for m in conversation_history[-4:]
                if m.get("role") == "user"
            )
            if _UNCENSORED_RE.search(recent):
                uncensored_score += 1

        # 5. Decision
        if smart_score > uncensored_score:
            selected = SMART_MODEL
            reason = f"technical/reasoning (smart={smart_score}, uncensored={uncensored_score})"
        elif uncensored_score > smart_score:
            selected = UNCENSORED_MODEL
            reason = f"opinion/casual (uncensored={uncensored_score}, smart={smart_score})"
        else:
            # Tie → default to smart for best general quality
            selected = SMART_MODEL
            reason = f"default (tied at {smart_score})"

        logger.info(f"[ModelSelector] '{selected}' — {reason} | msg='{message[:60]}...' ")
        return selected

    def explain(self, message: str) -> dict:
        """Return a debug breakdown of the selection decision."""
        smart_matches = _SMART_RE.findall(message)
        uncensored_matches = _UNCENSORED_RE.findall(message)
        selected = self.select(message)
        return {
            "selected_model": selected,
            "smart_matches": smart_matches,
            "uncensored_matches": uncensored_matches,
            "message_length": len(message),
        }


# Global singleton
model_selector = ModelSelector()
