UNIFIED_EXTRACTION_PROMPT = """
You are performing TWO SEPARATE, INDEPENDENT extraction tasks on the same user 
message. Do not let one task influence the other — they populate different output 
fields and follow different rules. Read both task definitions fully before producing 
output.

=====================================================================
TASK 1: SEMANTIC MEMORY EXTRACTION  →  populates `memories`
=====================================================================

Extract long-term, factual memories from the user's latest message.

Extract only information that is:
- Stable
- Factual
- Likely to remain useful across future conversations.

Do NOT extract:
- Temporary plans
- One-time requests
- Questions
- Speculation
- Assistant responses
- The user's emotional state — emotions are NEVER a semantic fact. Emotional content 
  is handled entirely in TASK 2 below. Do not create a memory like 
  "subject=User, predicate=feels, object=frustrated" — that belongs in 
  episodic_markers, not here.

Each extracted memory must represent exactly one atomic fact.

You will also be provided with lists of existing subjects and existing predicates.

Rules:
- Prefer an existing subject whenever it represents the same entity.
- Prefer an existing predicate whenever it expresses the same relationship.
- Only create a new subject or predicate if no existing one accurately represents 
  the fact.
- Do not invent facts or infer unstated information.
- Keep subjects and predicates concise and consistent.

## TEMPORAL EXTRACTION (semantic facts) — DO NOT COMPUTE DATES
- If the user's text contains a phrase indicating WHEN the fact became or becomes 
  true, extract that phrase VERBATIM into `temporal_expression`.
  Examples: "last month", "in 2021", "since college", "yesterday", "starting next week".
- You must NEVER convert this phrase into an actual date yourself. That calculation 
  happens downstream, not by you. Extract the phrase as-is, unmodified.
- If no such phrase exists in the text, set `temporal_expression = null` and 
  `temporal_precision = "unknown"`.
- Set `temporal_precision` based on what the phrase implies, one of:
  - "instant" -> phrase implies this exact moment ("just started", "right now")
  - "day"     -> phrase resolves to a specific day ("yesterday", "on Monday", "July 3rd")
  - "month"   -> phrase resolves to a month or range ("last month", "in June")
  - "year"    -> phrase resolves to a year only ("in 2021", "last year")
  - "unknown" -> no temporal phrase present in the text

## TERMINATION DETECTION (semantic facts only)
- Set `is_terminating = true` ONLY when the fact explicitly describes the END of a 
  previously ongoing state — quitting, breaking up, moving away, no longer liking 
  something, stopping a habit.
  Example: "I quit my job at Google" -> subject=User, predicate=works_at, 
  object=Google, is_terminating=true.
- All new, current, or ongoing facts default to is_terminating=false.
- Do not infer termination unless the text explicitly states an ending.
- This field does not exist in TASK 2 — do not apply termination logic to 
  episodic_markers.

Existing Subjects:
{subjects}

Existing Predicates:
{predicates}

=====================================================================
TASK 2: EPISODIC MARKER TAGGING  →  populates `episodic_markers`
=====================================================================

Tag this same message with lightweight episodic signals. This is NOT 
summarization — do not synthesize or compress the message. You are only detecting 
signals that a separate downstream process will use later to decide what's worth 
remembering as an event.

This task is where ALL emotional content goes. TASK 1 above must never contain 
emotional facts — if the message has emotional content, it is captured HERE, not 
as a semantic memory.

1. EMOTIONAL VALENCE & INTENSITY
   - Detect the user's emotional tone in THIS message only, not the conversation 
     history.
   - valence: positive / negative / neutral / mixed
   - intensity: low / moderate / high — how strongly is it expressed, not how 
     important the topic is.
   - emotional_labels: short words only (frustration, excitement, relief, anxiety, 
     etc). Empty list if the message is emotionally flat.

2. SIGNIFICANCE FLAG
   - is_significant_event = true if this message reflects something worth 
     recalling in a future session: a decision made, a problem hit, a preference 
     stated or changed, a strong reaction, a milestone.
   - is_significant_event = false for routine turns: acknowledgments, small talk, 
     simple factual questions with no emotional or decisional weight.
   - When uncertain, default to false. Over-flagging defeats the purpose of this 
     field — it exists to filter noise, not capture everything.

3. TEMPORAL EXPRESSION (episodic — separate from TASK 1's temporal_expression)
   - If the user's message contains a phrase indicating WHEN this event happened 
     (e.g. "earlier today", "just now", "last week"), extract it VERBATIM into 
     this field.
   - Do NOT resolve it to a date yourself. Extract the phrase only.
   - Null if no such phrase exists — this is the default for most messages.
   - Note: this may be the SAME phrase as TASK 1's temporal_expression, or 
     different, or one may be present while the other is null — they describe 
     different things (when a FACT became true vs. when an EVENT happened) and 
     must be extracted independently. Do not copy one into the other by default.

## Rules for TASK 2:
- Do not infer emotion the user didn't express. A frustrated tone about an 
  external topic (e.g. a paper's methodology) still counts as the user's 
  expressed emotion — tag what's on the page, not what you assume they "really" 
  feel.
- Do not pad emotional_labels with weak/uncertain guesses. If unsure, leave it 
  empty rather than force a label.
- This runs on every message, including trivial ones — be fast and decisive, not 
  deliberative. Most ordinary messages should resolve to valence=neutral, 
  intensity=low, is_significant_event=false.

=====================================================================
OUTPUT
=====================================================================
Produce exactly one structured output containing both `memories` (TASK 1 results, 
plus `should_write`) and `episodic_markers` (TASK 2 results). Both tasks run on 
the same message. Neither task's output should reference or duplicate the other's 
fields.
"""