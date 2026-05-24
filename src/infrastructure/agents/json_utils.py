def extract_json(text: str) -> str:
    """Best-effort extraction of a JSON document from an LLM response.

    Strips markdown fences and surrounding prose, returning the outermost JSON span.
    """
    t = (text or "").strip()
    if "```" in t:
        parts = t.split("```")
        if len(parts) >= 3:
            block = parts[1]
            if block.lower().startswith("json"):
                block = block[4:]
            t = block.strip()

    starts = [i for i in (t.find("{"), t.find("[")) if i != -1]
    if starts:
        t = t[min(starts):]
    end = max(t.rfind("}"), t.rfind("]"))
    if end != -1:
        t = t[: end + 1]
    return t.strip()
