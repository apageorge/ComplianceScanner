"""
pipeline.py
-----------
The EU AI Act compliance agent.

Architecture: sequential ReAct pipeline
  Step 1 – Classify risk tier                (LLM call)
  Step 2 – Generate obligations + signal map (LLM call)
  Step 3 – Gather evidence                   (tool calls → LLM per obligation)
  Step 4 – Generate report                   (LLM call)

Each step yields StepEvent dicts that the SSE router streams to the frontend.

LLM backend: OpenAI 
"""

import json
import os
import asyncio
import yaml
from pathlib import Path

from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.tools.github_tool import (
    parse_repo,
    get_repo_meta,
    get_readme,
    get_file_tree,
    get_file_content,
    search_code,
)
from app.models.schemas import (
    Obligation,
    ObligationEvidence,
    SignalEvidence,
    ComplianceFinding,
    ComplianceReport,
)


    
_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4o" 

RISK_TIERS = ["unacceptable", "high", "limited", "minimal"]

SYSTEM_PROMPT = """You are an expert EU AI Act compliance analyst. You analyse GitHub
repositories and assess how well the code, documentation, and structure demonstrates
compliance with EU AI Act obligations.

You are precise, honest about uncertainty, and always distinguish between what can
be verified from source code versus what requires external evidence. When confidence
is limited, you say so explicitly and explain why.

Always respond in the JSON format requested by each prompt. No markdown fences, no
preamble — raw JSON only."""


# ── helpers ──────────────────────────────────────────────────────────────────

def _event(step: str, status: str, payload: dict) -> dict:
    return {"step": step, "status": status, "payload": payload}


async def _llm(prompt: str, max_tokens: int = 2048) -> str:
    """Single-turn LLM call. Returns text content.
    """
    response = await _client.chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
    )
    return response.choices[0].message.content


def _parse_json(text: str) -> dict | list:
    """Strip accidental markdown fences then parse."""
    cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(cleaned)


# ── Step 1: Classify ─────────────────────────────────────────────────────────

async def _classify(
    owner: str, repo: str, meta: dict, readme: str, tree: list[str]
) -> dict:
    """Ask Claude to classify the risk tier and explain why."""

    tree_sample = "\n".join(tree[:120])  # first 120 paths to keep tokens low

    prompt = f"""Analyse this GitHub repository and classify it under the EU AI Act risk framework.

## Repository metadata
{json.dumps(meta, indent=2)}

## README (first 8 KB)
{readme or "(no README found)"}

## File tree (first 120 entries)
{tree_sample}

Classify the system into exactly one of: unacceptable | high | limited | minimal

Use these definitions:
- unacceptable: prohibited by Art. 5 (social scoring, real-time biometric surveillance, subliminal manipulation, etc.)
- high: Annex III systems (credit scoring, CV screening, medical diagnosis, law enforcement, critical infrastructure, etc.)
- limited: systems with transparency obligations (chatbots, deepfake generators, emotion recognition disclosed to users)
- minimal: all other AI systems with no specific obligations

Respond ONLY with this JSON:
{{
  "risk_tier": "<one of the four values>",
  "reasoning": "<2-4 sentences explaining the classification>",
  "system_description": "<1-2 sentences describing what this AI system does>"
}}"""

    raw = await _llm(prompt, max_tokens=512)
    return _parse_json(raw)


# ── Step 2: Generate obligations + signal mapping ─────────────────────────────

async def _generate_obligations(risk_tier: str, system_description: str) -> list[dict]:
    path = Path(__file__).parent.parent / "data" / "obligations.yaml"
    with open(path) as f:
        data = yaml.safe_load(f)
    base = data["obligations"]  # always all 5, tier context goes to the LLM

    prompt = f"""You are adapting a fixed EU AI Act obligation schema for a specific repository.


System description: {system_description}
Risk tier: {risk_tier}

Below are the base obligations with their fixed signals. You may add at most ONE additional
signal per obligation if the system description makes it clearly relevant.
Do NOT remove or rephrase existing signals. Do NOT change ids, tenets, articles,
not_checkable_in_code, or confidence_ceiling values.

Base obligations:
{json.dumps(base, indent=2)}

Respond ONLY with the obligations JSON array, with your additions (if any) merged in."""

    raw = await _llm(prompt, max_tokens=2048)
    adapted = _parse_json(raw)

    if not isinstance(adapted, list) or len(adapted) != len(base):
        return base
    return adapted


# ── Step 3: Evidence gathering (ReAct inner loop) ─────────────────────────────

# Tool definitions exposed to the LLM in the ReAct loop.
# The LLM picks which tools to call and with what arguments.
# We execute them and feed results back. Max 2 rounds to control cost.

_TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the full content of a specific file in the repository. "
                "Use this when you need to examine what a file actually contains — "
                "e.g. a model card, governance doc, CI config, or source file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Exact file path as it appears in the file tree (e.g. 'docs/model_card.md')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": (
                "Search for a keyword or phrase across all files in the repository. "
                "Use this to find where concepts like 'human review', 'bias', "
                "'logging', or 'disclosure' appear in code or config."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Short keyword or phrase to search for (e.g. 'human_override', 'fairness metric')",
                    }
                },
                "required": ["query"],
            },
        },
    },
]


async def _execute_tool(
    tool_name: str,
    tool_args: dict,
    owner: str,
    repo: str,
    tree: list[str],
) -> str:
    """Execute a tool call requested by the LLM and return a string result."""
    if tool_name == "read_file":
        path = tool_args.get("path", "")
        # Validate path exists in tree before fetching
        if path not in tree and not any(f.startswith(path.rstrip("/") + "/") for f in tree):
            return f"File not found in repository: {path}"
        content = await get_file_content(owner, repo, path)
        if not content:
            return f"File exists but appears empty or binary: {path}"
        return f"=== {path} ===\n{content}"

    elif tool_name == "search_code":
        query = tool_args.get("query", "")
        try:
            results = await search_code(owner, repo, query)
            if not results:
                return f"No results found for query: '{query}'"
            lines = [f"- {r['path']}" for r in results[:5]]
            return f"Files matching '{query}':\n" + "\n".join(lines)
        except Exception as e:
            return f"Search unavailable: {e}"

    return f"Unknown tool: {tool_name}"


async def _gather_evidence_for_obligation(
    owner: str,
    repo: str,
    obligation: dict,
    tree: list[str],
    readme: str,
) -> dict:
    """
    ReAct inner loop for a single obligation.

    Round 1 — Reason:
      Agent sees the obligation + signals + file tree.
      It responds with tool calls: which files to read, what to search for.

    Round 1 — Act + Observe:
      We execute every tool call and collect results.

    Round 2 — Reason:
      Agent sees the obligation + tool results + README excerpt.
      It produces the final structured evidence assessment.

    Max 2 reasoning rounds to keep cost bounded.
    The Agent decides what to look at; we just fetch and return.
    """

    # Prioritise the tree sample: surface docs, CI, governance files first
    def _tree_priority(path: str) -> int:
        p = path.lower()
        if any(k in p for k in ["model_card", "modelcard", "governance", "fairness", "bias"]):
            return 0
        if any(k in p for k in ["readme", "changelog", "contributing", "security", "license"]):
            return 1
        if ".github/workflows" in p or "ci" in p:
            return 2
        if p.startswith("docs/"):
            return 3
        if any(p.endswith(ext) for ext in [".md", ".yml", ".yaml", ".txt"]):
            return 4
        return 5

    sorted_tree = sorted(tree, key=_tree_priority)
    tree_sample = "\n".join(sorted_tree[:150])

    # ── Round 1: ask the Agent what to look at ─────────────────────────────────
    round1_prompt = f"""You are gathering evidence for an EU AI Act compliance obligation.

OBLIGATION: {obligation['tenet']} ({obligation['article']})
APPLIES IF: {obligation['applies_if']}

SIGNALS TO CHECK:
{json.dumps(obligation['signals_to_check'], indent=2)}

README (first 2000 chars):
{readme[:2000]}

REPOSITORY FILE TREE (priority-sorted, {len(tree)} total files):
{tree_sample}

Your job: decide which files to read and what to search for in order to assess each signal.
Be targeted — pick the 3-5 most promising files/searches. Prefer reading actual content
over just noting that a file exists.

Use the available tools now."""

    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": round1_prompt},
    ]

    # First LLM call — may return tool_calls
    r1 = await _client.chat.completions.create(
        model=MODEL,
        max_tokens=1024,
        temperature=0,
        tools=_TOOL_DEFINITIONS,
        tool_choice="auto",
        messages=messages,
    )
    r1_msg = r1.choices[0].message

    # ── Execute all tool calls from Round 1 ───────────────────────────────────
    tool_results: list[str] = []

    if r1_msg.tool_calls:
        # Append assistant message with tool calls to history
        messages.append(r1_msg)

        for tc in r1_msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}

            await asyncio.sleep(0.3)  #  GitHub pacing
            result_text = await _execute_tool(tc.function.name, args, owner, repo, tree)
            tool_results.append(result_text)

            # Append each tool result to history (required by OpenAI for multi-turn tool use)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_text,
            })
    else:
        # LLM chose not to use tools — its reasoning is the observation
        tool_results.append(r1_msg.content or "(no tool calls made)")

    # ── Round 2: interpret observations → structured evidence ─────────────────
    round2_prompt = f"""You have gathered evidence from the repository. Now assess each signal.

OBLIGATION: {obligation['tenet']} ({obligation['article']})

SIGNALS TO ASSESS:
{json.dumps(obligation['signals_to_check'], indent=2)}

EVIDENCE GATHERED:
{chr(10).join(f"--- Source {i+1} ---{chr(10)}{r}" for i, r in enumerate(tool_results))}

README (first 3000 chars):
{readme[:3000]}

For each signal, assess based on what you actually found in the files and search results.
Be honest: if a file exists but its content doesn't address the signal, mark it not found.
Absence of a file after actively looking is meaningful evidence.

Respond ONLY with a JSON array matching the signals in order:
[
  {{
    "signal": "<exact signal text>",
    "found": true/false,
    "locations": ["<file path or search result that supports this>"],
    "note": "<1-2 sentences: what you found or didn't find, and why it matters>"
  }},
  ...
]"""

    messages.append({"role": "user", "content": round2_prompt})

    r2 = await _client.chat.completions.create(
        model=MODEL,
        max_tokens=1500,
        temperature=0,
        messages=messages,
    )
    raw = r2.choices[0].message.content
    interpreted = _parse_json(raw)

    return {
        "obligation_id": obligation["id"],
        "signal_results": interpreted,
        "tool_calls_made": len(r1_msg.tool_calls) if r1_msg.tool_calls else 0,
    }


# ── Step 4: Generate report ───────────────────────────────────────────────────

async def _generate_report(
    repo_url: str,
    meta: dict,
    classification: dict,
    obligations: list[dict],
    all_evidence: list[dict],
) -> dict:
    """Synthesise everything into a scored compliance report."""
    print(f"DEBUG evidence summary:")
    for e in all_evidence:
        if "error" in e:
            print(f"  ERROR {e['obligation_id']}: {e['error']}")
        else:
            found = [s for s in e.get("signal_results", []) if s.get("found")]
            print(f"  {e['obligation_id']}: {len(found)}/{len(e.get('signal_results', []))} signals found")

    prompt = f"""You are writing a final EU AI Act compliance report.

Repository: {repo_url}
System description: {classification['system_description']}
Risk tier: {classification['risk_tier']}
Risk tier reasoning: {classification['reasoning']}

For each obligation below, you have the evidence gathered. Produce a compliance finding.

Score guidelines:
- score: 0.0 (nothing found) → 1.0 (strong evidence of compliance), CAPPED at confidence_ceiling
- confidence: how certain you are in the score (0.0–1.0)
- verdict: "compliant" (score ≥ 0.7), "partial" (0.3–0.69), "non-compliant" (< 0.3),
           "not-checkable" (obligation is entirely outside code inspection)

Obligations and evidence:
{json.dumps({"obligations": obligations, "evidence": all_evidence}, indent=2)}

Respond ONLY with this JSON:
{{
  "overall_score": <float 0-1, mean of obligation scores>,
  "overall_confidence": <float 0-1>,
  "findings": [
    {{
      "obligation_id": "<id>",
      "tenet": "<tenet name>",
      "article": "<article>",
      "score": <float>,
      "confidence": <float>,
      "confidence_ceiling": <float>,
      "verdict": "<compliant|partial|non-compliant|not-checkable>",
      "summary": "<2-3 sentences>",
      "evidence_highlights": ["<up to 3 key evidence points>"],
      "not_checkable_notes": ["<items from not_checkable_in_code that apply>"]
    }},
    ...
  ]
}}"""

    raw = await _llm(prompt, max_tokens=3000)
    result = _parse_json(raw)
    result["repo_url"] = repo_url
    result["repo_name"] = meta.get("full_name", repo_url)
    result["risk_tier"] = classification["risk_tier"]
    result["risk_tier_reasoning"] = classification["reasoning"]
    return result


# ── Main pipeline entry point ─────────────────────────────────────────────────

async def run_pipeline(github_url: str) -> AsyncGenerator[dict, None]:
    """
    Run the full 4-step compliance pipeline, yielding StepEvent dicts.
    The router converts these to SSE for the frontend.
    """
    try:
        owner, repo = parse_repo(github_url)
    except ValueError as e:
        yield _event("error", "done", {"message": str(e)})
        return

    # ── Step 0: Fetch repo data  ───────────────────────────────
    yield _event("classify", "start", {"message": "Fetching repository data…"})
    try:
        meta = await get_repo_meta(owner, repo)
        readme = await get_readme(owner, repo)
        tree = await get_file_tree(owner, repo, meta.get("default_branch", "main"))
    except Exception as e:
        yield _event("error", "done", {"message": f"GitHub API error: {e}"})
        return

    yield _event("classify", "stream", {
        "message": f"Fetched repo: {meta['full_name']} ({len(tree)} files)"
    })

    # ── Step 1: Classify ──────────────────────────────────────────────────────
    try:
        classification = await _classify(owner, repo, meta, readme, tree)
    except Exception as e:
        yield _event("error", "done", {"message": f"Classification error: {e}"})
        return

    yield _event("classify", "done", classification)

    # ── Step 2: Obligations + signal map ──────────────────────────────────────
    yield _event("obligations", "start", {"message": "Generating obligation map…"})
    try:
        obligations = await _generate_obligations(
            classification["risk_tier"],
            classification["system_description"],
        )
    except Exception as e:
        yield _event("error", "done", {"message": f"Obligation generation error: {e}"})
        return

    yield _event("obligations", "done", {"obligations": obligations})

    # ── Step 3: Evidence gathering ────────────────────────────────────────────
    yield _event("evidence", "start", {"message": f"Gathering evidence for {len(obligations)} obligations…"})
    all_evidence: list[dict] = []

    for i, obs in enumerate(obligations):
        yield _event("evidence", "stream", {
            "message": f"[{i+1}/{len(obligations)}] Checking: {obs['tenet']}"
        })
        try:
            evidence = await _gather_evidence_for_obligation(owner, repo, obs, tree, readme)
            n_tools = evidence.get("tool_calls_made", 0)
            yield _event("evidence", "stream", {
                "message": f"[{i+1}/{len(obligations)}] {obs['tenet']} — {n_tools} tool call(s) made"
            })
            all_evidence.append(evidence)
        except Exception as e:
            # Don't abort — partial evidence is still useful
            all_evidence.append({
                "obligation_id": obs["id"],
                "signal_results": [],
                "error": str(e),
            })

    yield _event("evidence", "done", {"evidence_count": len(all_evidence)})

    # ── Step 4: Report generation ─────────────────────────────────────────────
    yield _event("report", "start", {"message": "Synthesising compliance report…"})
    try:
        report = await _generate_report(
            github_url, meta, classification, obligations, all_evidence
        )
    except Exception as e:
        yield _event("error", "done", {"message": f"Report generation error: {e}"})
        return

    yield _event("report", "done", report)
