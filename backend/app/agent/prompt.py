import os

def load_system_prompt():
    # Try prompts/system.md relative to project root
    candidates = [
        os.path.join(os.path.dirname(__file__), "../../../prompts/system.md"),
        os.path.join(os.path.dirname(__file__), "../../prompts/system.md"),
        "prompts/system.md",
        "../prompts/system.md"
    ]
    for p in candidates:
        ap = os.path.abspath(p)
        if os.path.exists(ap):
            with open(ap, "r", encoding="utf-8") as f:
                return f.read()
    # fallback
    return "You are BIMGuard, an IFC compliance assistant. Use tools to get evidence, never hallucinate measurements."
