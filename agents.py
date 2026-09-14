import os
import json
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pitch-agents")

# GCP Project configuration
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-03-58f8a6ff95cf")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# Initialize client
def get_genai_client():
    # Supports ADC or Vertex AI or GEMINI_API_KEY
    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

client = get_genai_client()

UNIVERSAL_DIRECTIVE_BLOCK = """
GROUNDING RULES (apply to every claim you make):
1. You may only state a specific number, statistic, company name, funding
   amount, or market-size figure if it appears in one of these two places:
   (a) the User-Provided Input given to you in this prompt, or
   (b) the Retrieved Grounding Data given to you in this prompt.
2. If a claim would require a number or fact that is NOT present in (a) or
   (b), check if it can be resolved as a benchmark_estimate based on
   real comparable companies. If not, output that field as:
   "INSUFFICIENT_DATA: <what specific information is missing>"
3. Every factual claim you output must carry a "source" tag with one of
   these exact values: "user_input", "retrieved", "benchmark_estimate",
   or "insufficient_data". A claim with no source tag is treated as a failure.
4. Do not invent named competitors, customer names, dates, or dollar
   figures under any circumstance, including for "illustration" or
   "placeholder" purposes. If asked to show what a field would look like
   without real data, use the literal string "[NEEDS REAL DATA]" — never
   a realistic-sounding fake value.
5. This rule outranks instructions elsewhere in this prompt that ask you
   to "make it sound impressive" or "fill in reasonable numbers." Fluency
   is never a substitute for a real source.
"""

def clean_json_response(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

# -------------------------------------------------------------
# Agent 1 — Intake Agent
# -------------------------------------------------------------
INTAKE_SYSTEM_PROMPT = f"""{UNIVERSAL_DIRECTIVE_BLOCK}

You are the intake agent for a startup-pitch pressure-testing system. You
will receive one raw business concept from a founder, written in their own
words, of any length or quality.

Your only job: generate exactly 2-3 follow-up questions that are SPECIFIC
to this concept — not generic startup-interview questions. Each question
should target one of these three gaps, whichever are weakest in the
founder's original input:

1. Founder-earned insight: what specific experience, observation, or
   failure convinced them this problem is real? (Generic answers like
   "I researched the market" do not count — push for a specific moment
   or data point.)
2. Defensibility: what would stop a well-funded competitor from copying
   this in 6 months? If the founder's input only says "we use AI," this
   is the question to ask.
3. Evidence of demand: what's the most concrete signal they have that
   someone wants this — a conversation, a waitlist signup, a letter of
   intent? (Not "I think people would want this.")

Do not ask a question if the founder's original input already answers it
concretely. Do not ask more than 3 questions total.

OUTPUT (JSON):
{{
  "questions": [
    {{"targets_gap": "founder_insight | defensibility | demand_evidence",
     "question": "<specific question text>"}}
  ]
}}
"""

def run_intake_agent(raw_concept: str) -> Dict[str, Any]:
    prompt = f"Founder Raw Business Concept:\n\"\"\"\n{raw_concept}\n\"\"\"\n\nGenerate exactly 2-3 specific follow-up questions targeting the weakest gaps."
    res = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=INTAKE_SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    data = json.loads(clean_json_response(res.text))
    return data

# -------------------------------------------------------------
# Agent 2 — Draft Agent
# -------------------------------------------------------------
DRAFT_SYSTEM_PROMPT = f"""{UNIVERSAL_DIRECTIVE_BLOCK}

You are the draft agent. You will receive:
- The founder's original business concept (User-Provided Input)
- Their answers to the intake questions (User-Provided Input)
- Any Retrieved Grounding Data passed to you (may be empty)

Produce a 10-slide pitch draft using EXACTLY this slide schema. For each
slide, populate the "content" field and the "source" field for every
factual sub-claim within it.

SLIDE SCHEMA:
1. hook_problem — concrete problem framing
2. solution — direct mapping to the stated problem
3. why_now — a named shift (technical, regulatory, behavioral) in roughly
   the last 6-12 months; if the founder didn't supply this and no
   grounding data supports one, mark INSUFFICIENT_DATA — do not invent a
   trend
4. market_bottom_up — customer count × contract value, built only from
   numbers present in user input or retrieved data
5. product — what exists today per the founder's own description; do not
   describe features the founder didn't mention
6. moat — must name something other than "uses AI"; if the founder's
   defensibility answer was generic, mark INSUFFICIENT_DATA rather than
   inventing a moat for them
7. traction — must match the stage implied by the founder's own evidence;
   if they gave no evidence, this slide is INSUFFICIENT_DATA, not a
   generated placeholder metric
8. competition — name real alternative approaches, including "do
   nothing"; only name specific competitor companies if they were
   supplied in user input or retrieved data — otherwise describe the
   category of alternative generically
9. business_model_economics — pricing plus CAC/LTV/burn multiple; these
   are almost always INSUFFICIENT_DATA at intake unless the founder
   supplied numbers — do not synthesize a plausible SaaS benchmark and
   present it as this founder's numbers
10. team_ask — the founder's specific earned insight from the intake
    step must appear here verbatim or near-verbatim; plus a funding ask
    only if one was stated

OUTPUT (JSON): a slides array, each item containing:
{{
  "slides": [
    {{
      "slide_number": 1,
      "title": "hook_problem",
      "content": "<slide narrative content>",
      "claims": [
        {{"text": "<factual claim>", "source": "user_input | retrieved | insufficient_data"}}
      ]
    }}
  ]
}}
"""

def run_draft_agent(raw_concept: str, intake_qa: List[Dict[str, str]], retrieved_data: str = "") -> Dict[str, Any]:
    intake_text = "\n".join([f"Q ({item.get('targets_gap', 'gap')}): {item.get('question')}\nA: {item.get('answer', '')}" for item in intake_qa])
    prompt = f"""
USER-PROVIDED INPUT:
Original Business Concept:
{raw_concept}

Intake Q&A:
{intake_text}

RETRIEVED GROUNDING DATA:
{retrieved_data if retrieved_data else "None"}
"""
    res = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=DRAFT_SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    data = json.loads(clean_json_response(res.text))
    return data

# -------------------------------------------------------------
# Agent 3 — Grounding Agent
# -------------------------------------------------------------
GROUNDING_SYSTEM_PROMPT = f"""{UNIVERSAL_DIRECTIVE_BLOCK}

You are the grounding agent. You receive the draft slide set from Agent 2.
For every claim tagged "insufficient_data" on slides 4 (market) and 8
(competition) ONLY, check if the missing data is objectively searchable
(market-size figures, named companies in a category, recent funding rounds).
Do not search for anything about the founder's own internal traction or internal metrics.

If you find relevant search data provided below, upgrade the claim from "insufficient_data"
to "retrieved" and attach the source URL.
If no direct search data exists or if the search did not directly support the concept,
leave the claim as "insufficient_data".

OUTPUT (JSON):
{{
  "slides": [
    {{
      "slide_number": 1,
      "title": "...",
      "content": "...",
      "claims": [
        {{
          "text": "...",
          "source": "user_input | retrieved | insufficient_data",
          "retrieved_url": "url or null"
        }}
      ]
    }}
  ]
}}
"""

def run_grounding_agent(slides: List[Dict[str, Any]], concept_summary: str) -> tuple[List[Dict[str, Any]], List[str]]:
    searches_run = []
    
    # Check if slide 4 or slide 8 has insufficient_data
    needs_grounding = False
    search_queries = []
    
    for slide in slides:
        num = slide.get("slide_number")
        if num in [4, 8]:
            for claim in slide.get("claims", []):
                if claim.get("source") == "insufficient_data":
                    needs_grounding = True
                    if num == 4:
                        search_queries.append(f"market size bottom up {concept_summary} 2024 2025 2026")
                    elif num == 8:
                        search_queries.append(f"top competitors startups companies in {concept_summary}")

    grounding_context = []
    
    if needs_grounding:
        # Run Google Search Grounding for each query
        for q in set(search_queries[:2]):
            searches_run.append(q)
            try:
                search_res = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=f"Find specific factual market size numbers, companies, or pricing for: {q}",
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.1
                    )
                )
                chunk_urls = []
                if search_res.candidates and search_res.candidates[0].grounding_metadata:
                    gm = search_res.candidates[0].grounding_metadata
                    if gm.grounding_chunks:
                        for chunk in gm.grounding_chunks:
                            if hasattr(chunk, "web") and chunk.web and chunk.web.uri:
                                chunk_urls.append(chunk.web.uri)
                
                grounding_context.append({
                    "query": q,
                    "summary": search_res.text,
                    "urls": list(set(chunk_urls))[:3]
                })
            except Exception as e:
                logger.warning(f"Search grounding query failed: {e}")

    # Now let the Grounding Agent process the slides with the search results
    prompt = f"""
DRAFT SLIDES:
{json.dumps(slides, indent=2)}

RETRIEVED SEARCH RESULTS (from Google Search):
{json.dumps(grounding_context, indent=2)}

Apply Grounding rules. Only upgrade claims on slide 4 and 8 if directly supported by the search results. Attach retrieved_url when source is 'retrieved'.
"""
    res = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=GROUNDING_SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    data = json.loads(clean_json_response(res.text))
    return data.get("slides", slides), searches_run

# -------------------------------------------------------------
# Agent 4 — Critique Agent
# -------------------------------------------------------------
CRITIQUE_SYSTEM_PROMPT = f"""{UNIVERSAL_DIRECTIVE_BLOCK}

You are the critique agent. You receive the grounded slide set. You do
NOT rewrite content. You output a verdict per slide, chosen from exactly
three states:

- "pass" — the slide's claims are all properly source-tagged and the
  content satisfies the checklist below.
- "revise" — a structural issue exists, OR the slide relies on a
  benchmark_estimate with no direct user_input or retrieved claims yet.
- "insufficient_input" — the slide makes a claim that cannot be
  credibly supported by anything in user input, retrieved data, or real
  comparable benchmarks, and only a real answer from the founder would
  fix it (Rung 5 of the Resolution Ladder).

UPDATED CHECKLIST (apply to every slide):
[ ] Every claim has a source tag ("user_input", "retrieved",
    "benchmark_estimate", or "insufficient_data") — an untagged claim
    is an automatic FAIL, treat as insufficient_input.
[ ] A claim tagged "benchmark_estimate" is legitimate and does NOT
    trigger insufficient_input by itself — it triggers "revise" if the
    slide has no user_input or retrieved claims at all, "pass" if it's
    supported alongside at least one directly-sourced claim.
[ ] insufficient_input is reserved for rung-5 gaps only: the moat
    mechanism (slide 6), or a founder-specific fact with no
    benchmarkable analog. Before assigning insufficient_input, confirm
    the Benchmark Research Agent was actually attempted and returned
    resolved=false — an unattempted benchmark is not the same as an
    exhausted one.
[ ] Never let a benchmark_estimate silently upgrade to user_input or
    retrieved just because it sounds confident — the tag only changes
    when the founder actually confirms it or real data replaces it.
[ ] Market sizing (slide 4) is bottom-up, not a bare top-down figure
[ ] Moat (slide 6) names something other than "uses AI"
[ ] "Why now" (slide 3) is present and specific
[ ] Competition (slide 8) never states "no competitors"

OUTPUT (JSON):
{{
  "verdicts": [
    {{
      "slide_number": 1,
      "verdict": "pass | revise | insufficient_input",
      "reason": "<concise explanation of verdict>",
      "follow_up_question": "<specific question to founder if insufficient_input, else null>"
    }}
  ]
}}
"""

def run_critique_agent(slides: List[Dict[str, Any]], raw_concept: str, intake_qa: List[Dict[str, str]]) -> Dict[str, Any]:
    prompt = f"""
RAW CONCEPT & FOUNDER INPUT:
{raw_concept}

INTAKE ANSWERS:
{json.dumps(intake_qa, indent=2)}

GROUNDED SLIDES TO EVALUATE:
{json.dumps(slides, indent=2)}
"""
    res = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=CRITIQUE_SYSTEM_PROMPT,
            temperature=0.1,
            response_mime_type="application/json"
        )
    )
    data = json.loads(clean_json_response(res.text))
    return data

# -------------------------------------------------------------
# Agent 5 — Refine Agent
# -------------------------------------------------------------
REFINE_SYSTEM_PROMPT = f"""{UNIVERSAL_DIRECTIVE_BLOCK}

You receive the slide set plus the critique agent's verdicts.

For every slide marked "revise": rewrite using ONLY information already
present in user input or retrieved data — the same grounding rules apply
here as everywhere else. Do not treat "revise" as permission to add new
unsourced content to make the fix easier.

For every slide marked "insufficient_input": do NOT rewrite it. Leave it
exactly as flagged. The system will surface the critique agent's follow-up
question to the founder instead of proceeding.

You are the last agent before rendering. If a slide is still marked
"insufficient_input" after this pass, the final output must show that
slide's status as "needs founder input" — never silently render a filled-
in version of it.

OUTPUT (JSON):
{{
  "slides": [
    {{
      "slide_number": 1,
      "title": "...",
      "content": "...",
      "claims": [
        {{
          "text": "...",
          "source": "user_input | retrieved | insufficient_data",
          "retrieved_url": "url or null"
        }}
      ],
      "verdict": "pass | revise | insufficient_input",
      "follow_up_question": "string or null"
    }}
  ]
}}
"""

def run_refine_agent(slides: List[Dict[str, Any]], verdicts: List[Dict[str, Any]], raw_concept: str) -> List[Dict[str, Any]]:
    # Merge verdicts into slides before sending to refine
    verdict_map = {v["slide_number"]: v for v in verdicts}
    for slide in slides:
        v = verdict_map.get(slide["slide_number"], {})
        slide["verdict"] = v.get("verdict", "insufficient_input")
        slide["follow_up_question"] = v.get("follow_up_question")
        slide["reason"] = v.get("reason", "")

    prompt = f"""
FOUNDER CONTEXT:
{raw_concept}

SLIDES WITH VERDICTS:
{json.dumps(slides, indent=2)}
"""
    res = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=REFINE_SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    data = json.loads(clean_json_response(res.text))
    return data.get("slides", slides)

# -------------------------------------------------------------
# Full Pipeline Execution with Evaluator-Optimizer Loop
# -------------------------------------------------------------
def execute_full_pipeline(raw_concept: str, intake_qa: List[Dict[str, str]]) -> Dict[str, Any]:
    trace = {
        "intake_questions_asked": [item.get("question") for item in intake_qa],
        "grounding_searches_run": [],
        "critique_passes": 0,
        "slides_needing_founder_input": []
    }
    
    # 1. Agent 2: Draft
    logger.info("Executing Agent 2: Draft Agent")
    draft_result = run_draft_agent(raw_concept, intake_qa)
    current_slides = draft_result.get("slides", [])
    
    # 2. Agent 3: Grounding
    logger.info("Executing Agent 3: Grounding Agent")
    grounded_slides, searches_run = run_grounding_agent(current_slides, raw_concept[:100])
    trace["grounding_searches_run"].extend(searches_run)
    current_slides = grounded_slides

    # 3. Evaluator-Optimizer Loop (Critique -> Refine, capped at 2 passes)
    critique_passes = 0
    max_passes = 2
    
    while critique_passes < max_passes:
        critique_passes += 1
        logger.info(f"Executing Agent 4: Critique Agent (Pass {critique_passes})")
        critique_result = run_critique_agent(current_slides, raw_concept, intake_qa)
        verdicts = critique_result.get("verdicts", [])
        
        # Check if any slide needs revision
        needs_revise = any(v.get("verdict") == "revise" for v in verdicts)
        
        # Update current slides with verdicts
        verdict_map = {v["slide_number"]: v for v in verdicts}
        for s in current_slides:
            v = verdict_map.get(s["slide_number"], {})
            s["verdict"] = v.get("verdict", "insufficient_input")
            s["follow_up_question"] = v.get("follow_up_question")
            if "reason" in v:
                s["critique_reason"] = v["reason"]
        
        if not needs_revise or critique_passes >= max_passes:
            # Done looping
            break
            
        logger.info(f"Executing Agent 5: Refine Agent (Pass {critique_passes})")
        refined_slides = run_refine_agent(current_slides, verdicts, raw_concept)
        current_slides = refined_slides

    trace["critique_passes"] = critique_passes
    trace["slides_needing_founder_input"] = [
        s["slide_number"] for s in current_slides if s.get("verdict") == "insufficient_input"
    ]
    
    # Ensure all claims have source tag and retrieved_url
    for s in current_slides:
        for c in s.get("claims", []):
            if "source" not in c or not c["source"]:
                c["source"] = "insufficient_data"
            if "retrieved_url" not in c:
                c["retrieved_url"] = None

    return {
        "slides": current_slides,
        "pipeline_trace": trace
    }
