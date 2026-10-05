"""Export the Claude Code conversation(s) for this project to readable Markdown.

Claude Code already saves every session automatically as JSONL in
~/.claude/projects/-home-d7-Desktop-MUDARASA/<session-id>.jsonl (survives restarts; resume with `claude --continue`).
This script turns each session into prep/conversation/<date>_<session-id>.md:
user messages and assistant replies in full, tool calls as one-line summaries, no hidden reasoning, no images.

Run any time: python3 prep/conversation/export_conversation.py   (overwrites the .md files with the latest state)
"""
import json
import pathlib
import re

SRC = pathlib.Path.home() / ".claude/projects/-home-d7-Desktop-MUDARASA"
OUT = pathlib.Path(__file__).resolve().parent


def clean_user(text: str) -> str:
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<pasted_content id=\"?\w+\"?>", "> [pasted]\n", text)
    text = re.sub(r"</pasted_content[^>]*>", "", text)
    return text.strip()


def tool_line(b: dict) -> str:
    inp = b.get("input", {})
    hint = inp.get("description") or inp.get("file_path") or inp.get("url") or inp.get("query") or inp.get("prompt", "")[:80]
    return f"- `{b.get('name')}`: {str(hint)[:160]}"


def export(jsonl: pathlib.Path):
    parts, tools, first_ts = [], [], None
    for line in jsonl.open(encoding="utf-8"):
        d = json.loads(line)
        if d.get("type") not in ("user", "assistant"):
            continue
        first_ts = first_ts or d.get("timestamp")
        msg = d.get("message", {})
        content = msg.get("content")
        if d["type"] == "user":
            texts = [content] if isinstance(content, str) else [b.get("text", "") for b in content or [] if b.get("type") == "text"]
            if any(b.get("type") == "image" for b in (content if isinstance(content, list) else [])):
                texts.append("[image attached]")
            text = clean_user("\n".join(t for t in texts if t))
            if not text or text.startswith("[SYSTEM NOTIFICATION") or "<task-notification>" in text:
                continue
            if tools:
                parts.append("<details><summary>Tool calls</summary>\n\n" + "\n".join(tools) + "\n</details>\n")
                tools = []
            parts.append(f"## 🧑 User ({d.get('timestamp', '')[:16].replace('T', ' ')})\n\n{text}\n")
        else:
            for b in content or []:
                if b.get("type") == "text" and b.get("text", "").strip():
                    if tools:
                        parts.append("<details><summary>Tool calls</summary>\n\n" + "\n".join(tools) + "\n</details>\n")
                        tools = []
                    parts.append(f"### 🤖 Claude\n\n{b['text'].strip()}\n")
                elif b.get("type") == "tool_use":
                    tools.append(tool_line(b))
    if tools:
        parts.append("<details><summary>Tool calls</summary>\n\n" + "\n".join(tools) + "\n</details>\n")
    date = (first_ts or "")[:10]
    out = OUT / f"{date}_{jsonl.stem[:8]}.md"
    out.write_text(f"# Mudarasa conversation, session {jsonl.stem}\n\nExported from Claude Code's automatic transcript.\n\n" + "\n".join(parts), encoding="utf-8")
    return out


if __name__ == "__main__":
    for f in sorted(SRC.glob("*.jsonl")):
        print("wrote", export(f))
