import os
import json
import re

from .. import ifc_engine
from ..rules.door_width import check_door_width, HK_RULE
from ..rules.clash import detect_clashes

# Tool definitions (mirrors prompts/tools.json)
TOOLS = [
    {
        "name": "check_exit_door_width",
        "description": "Check exit door width compliance",
        "parameters": {"type": "object", "properties": {"min_width": {"type": "number"}}}
    },
    {
        "name": "detect_clashes",
        "description": "Detect clashes",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_summary",
        "description": "Get summary",
        "parameters": {"type": "object", "properties": {"min_width": {"type": "number"}}}
    },
    {
        "name": "get_ifc_elements",
        "description": "List elements",
        "parameters": {"type": "object", "properties": {"type": {"type": "string"}, "limit": {"type": "integer"}}}
    },
    {
        "name": "get_element_properties",
        "description": "Get element psets",
        "parameters": {"type": "object", "properties": {"guid": {"type": "string"}}}
    }
]

def call_tool(name: str, args: dict = None):
    args = args or {}
    model = ifc_engine.get_current_model()
    if name == "check_exit_door_width":
        min_w = float(args.get("min_width", 750))
        res = check_door_width(model, min_w)
        return {"results": res, "rule": HK_RULE, "min_width": min_w}
    elif name == "detect_clashes":
        res = detect_clashes(model)
        return {"clashes": res, "count": len(res)}
    elif name == "get_summary":
        min_w = float(args.get("min_width", 750))
        doors = check_door_width(model, min_w)
        clashes = detect_clashes(model)
        passed = sum(1 for d in doors if d["status"]=="pass")
        failed = sum(1 for d in doors if d["status"]=="fail")
        total = len(doors)
        score = 100
        if total>0:
            score = int(100 * passed / total) if clashes==[] else int(100 * passed / total * 0.7)
            score = max(0, score - len(clashes)*10)
        return {
            "min_width": min_w,
            "doors": {"total": total, "passed": passed, "failed": failed},
            "clashes": {"count": len(clashes)},
            "score": score,
            "rule": HK_RULE
        }
    elif name == "get_ifc_elements":
        t = args.get("type")
        lim = int(args.get("limit", 50))
        els = ifc_engine.list_elements(t, lim)
        return {"elements": [ifc_engine.get_element_info(e) for e in els], "count": len(els)}
    elif name == "get_element_properties":
        guid = args.get("guid")
        if not guid:
            return {"error": "guid required"}
        return {"guid": guid, "psets": ifc_engine.get_psets(guid)}
    else:
        return {"error": f"unknown tool {name}"}

# --- Simple router for rule-based mock (no API key) ---

def _mock_explain(message: str, min_width=750):
    """Deterministic mock when no LLM key set — still tool-grounded."""
    msg = message.lower()
    doors_data = call_tool("check_exit_door_width", {"min_width": min_width})
    clashes_data = call_tool("detect_clashes", {})
    summary = call_tool("get_summary", {"min_width": min_width})

    # Decide intent by keywords
    wants_doors = any(k in msg for k in ["door", "width", "exit", "750", "850", "fire", "hk"])
    wants_clash = any(k in msg for k in ["clash", "pipe", "beam", "intersect", "collision", "penetration"])
    wants_all = any(k in msg for k in ["all", "serious", "critical", "violation", "fail", "issue", "summary", "score"])

    lines = []
    if wants_all or (not wants_doors and not wants_clash):
        # full summary
        lines.append(f"**Compliance Score: {summary['score']}/100** (threshold {min_width}mm)")
        lines.append(f"- Doors: {summary['doors']['passed']} passed / {summary['doors']['failed']} failed / {summary['doors']['total']} total")
        lines.append(f"- Clashes: {summary['clashes']['count']} detected")
        lines.append("")
        # details
        fails = [d for d in doors_data["results"] if d["status"]=="fail"]
        if fails:
            lines.append("**Exit Door Failures (HK FS Code 2011 Table B2):**")
            for f in fails[:5]:
                lines.append(f"- **{f['name']}** ({f['guid'][:8]}): {f['measured_mm']}mm < {f['required_mm']}mm (Δ {f['delta_mm']}mm) — *Increase by {abs(f['delta_mm'])}mm*")
        clashes = clashes_data["clashes"]
        if clashes:
            lines.append("")
            lines.append("**Clashes:**")
            for c in clashes[:5]:
                lines.append(f"- **{c['a_name']} × {c['b_name']}** ({c['a_type']} × {c['b_type']}): {c['penetration_mm']}mm penetration, severity {c['severity']} — *Reroute or add opening*")
        if not fails and not clashes:
            lines.append("No violations found for current threshold. Model is compliant.")
        return "\n".join(lines)

    if wants_doors:
        fails = [d for d in doors_data["results"] if d["status"]=="fail"]
        if "d-102" in msg or "102" in msg:
            # specific
            for d in doors_data["results"]:
                if "102" in d["name"] or "102" in d["tag"]:
                    if d["status"]=="fail":
                        return f"Door **{d['name']}** (GUID {d['guid']}) fails HK FS Code 2011 Table B2: measured {d['measured_mm']}mm < required {d['required_mm']}mm (Δ {d['delta_mm']}mm). **Fix:** increase clear opening by {abs(d['delta_mm'])}mm."
                    else:
                        return f"Door **{d['name']}** is compliant: {d['measured_mm']}mm ≥ {d['required_mm']}mm."
        if fails:
            lines.append(f"Found {len(fails)} door(s) below {min_width}mm:")
            for f in fails:
                lines.append(f"- {f['name']} ({f['guid'][:8]}): {f['measured_mm']}mm (need +{abs(f['delta_mm'])}mm)")
            lines.append(f"\nRule: {HK_RULE}. Fix by widening openings or replacing door leaves.")
        else:
            lines.append(f"All {len(doors_data['results'])} doors pass ≥{min_width}mm.")
        return "\n".join(lines)

    if wants_clash:
        clashes = clashes_data["clashes"]
        if not clashes:
            return "No clashes detected between structural and MEP elements."
        lines.append(f"Detected {len(clashes)} clash(es):")
        for c in clashes:
            lines.append(f"- {c['a_name']} ({c['a_type']}) × {c['b_name']} ({c['b_type']}): {c['penetration_mm']}mm, {c['severity']}")
        lines.append("Recommendation: reroute MEP or provide coordinated structural opening.")
        return "\n".join(lines)

    return _mock_explain("summary", min_width)

def route_message(message: str, min_width=750, use_llm=False):
    """
    Entry point for /api/chat.
    If OPENAI_API_KEY set and use_llm True, calls OpenAI; else mock.
    """
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
    if api_key and use_llm:
        try:
            return _call_llm(message, min_width, api_key)
        except Exception as e:
            # fallback to mock on LLM failure
            return {"reply": _mock_explain(message, min_width), "tools_used": ["check_exit_door_width","detect_clashes","get_summary"], "mode": f"mock_fallback: {e}"}
    else:
        # Gather evidence anyway
        return {"reply": _mock_explain(message, min_width), "tools_used": ["check_exit_door_width","detect_clashes","get_summary"], "mode": "mock_deterministic"}

def _call_llm(message: str, min_width, api_key: str):
    # Lazy import
    try:
        from openai import OpenAI
    except:
        raise RuntimeError("openai package not installed")
    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1"
    model = os.getenv("LLM_MODEL") or "gpt-4o-mini"
    client = OpenAI(api_key=api_key, base_url=base_url)

    # Pre-gather evidence to inject
    doors = call_tool("check_exit_door_width", {"min_width": min_width})
    clashes = call_tool("detect_clashes", {})
    summary = call_tool("get_summary", {"min_width": min_width})
    evidence = json.dumps({"summary": summary, "doors": doors["results"][:10], "clashes": clashes["clashes"][:5]}, ensure_ascii=False)

    from .prompt import load_system_prompt
    sys_prompt = load_system_prompt()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_prompt + f"\n\nEvidence JSON (use this, do not invent):\n{evidence}"},
            {"role": "user", "content": message}
        ],
        temperature=0.2,
        max_tokens=800
    )
    reply = resp.choices[0].message.content
    return {"reply": reply, "tools_used": ["check_exit_door_width","detect_clashes","get_summary"], "mode": f"llm:{model}", "evidence": evidence}
