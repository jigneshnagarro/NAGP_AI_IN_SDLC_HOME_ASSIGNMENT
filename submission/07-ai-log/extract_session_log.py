"""Build machine-readable logs from Claude Code session transcripts.

Claude Code writes every session to ~/.claude/projects/<project>/<session>.jsonl,
with sub-agent transcripts next to it in <session>/subagents/. This script reads
those files and writes:

  tool-calls.jsonl     one line per tool call (time, tool, target, permission, error)
  session-turns.jsonl  one line per human prompt, with the tools, sub-agents and
                       files that turn touched
  subagents.jsonl      one line per sub-agent run (type, model, task, tools, status)

Absolute paths, the home folder and e-mail addresses are replaced with
placeholders, and system reminders are stripped from the prompts.

Usage:
  python extract_session_log.py <session.jsonl> --repo <repo root> --out <dir>
"""
import argparse
import collections
import json
import re
from pathlib import Path

REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
PASTE_TAG = re.compile(r"</?pasted_content[^>]*>")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")


class Scrubber:
    def __init__(self, repo: Path):
        pairs = []
        for path, label in [(repo, "<repo>"), (repo.parent, "<workspace>"), (Path.home(), "~")]:
            raw = str(path)
            for form in {raw, raw.replace("\\", "/"), raw.replace("\\", "\\\\")}:
                pairs.append((form, label))
        pairs.sort(key=lambda pair: -len(pair[0]))
        self.pairs = [(re.compile(re.escape(old), re.I), new) for old, new in pairs]
        # Anything still naming the user: /c/Users/<name>, 8.3 short names, encoded project folders.
        self.user = re.compile(rf"{re.escape(Path.home().name)}|\b\w{{1,6}}~\d\b", re.I)

    def __call__(self, text: str) -> str:
        for pattern, label in self.pairs:
            text = pattern.sub(lambda _: label, text)
        text = self.user.sub("<user>", text)
        return EMAIL.sub("<email>", text)


def load(path: Path):
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def blocks(message):
    content = message.get("content", [])
    return [{"type": "text", "text": content}] if isinstance(content, str) else content


def human_prompt(record):
    if record.get("type") != "user" or record.get("turnOrigin") != "human":
        return None
    if record.get("isMeta") or record.get("isCompactSummary"):
        return None
    text = "\n".join(b.get("text", "") for b in blocks(record["message"]) if b.get("type") == "text")
    text = PASTE_TAG.sub("", REMINDER.sub("", text)).strip()
    return text or None


def target_of(name, tool_input, scrub):
    for key in ("file_path", "notebook_path", "path", "url"):
        if key in tool_input:
            return scrub(str(tool_input[key]))
    if name in ("Bash", "PowerShell"):
        return scrub(tool_input.get("command", ""))[:240]
    if name == "Agent":
        return tool_input.get("description", "")
    if name in ("Grep", "Glob"):
        return tool_input.get("pattern", "")
    if name == "Skill":
        return tool_input.get("skill", "")
    return ""


def collect_calls(records, scrub, session_label):
    calls, by_id = [], {}
    for rec in records:
        if rec.get("type") == "assistant":
            model = rec["message"].get("model")
            for b in blocks(rec["message"]):
                if b.get("type") != "tool_use":
                    continue
                parts = b["name"].split("__")
                call = {
                    "timestamp": rec.get("timestamp"),
                    "session": session_label,
                    "model": model,
                    "tool": b["name"],
                    "kind": "mcp" if b["name"].startswith("mcp__") else "builtin",
                    "mcp_server": parts[1] if b["name"].startswith("mcp__") else None,
                    "target": target_of(b["name"], b.get("input", {}), scrub),
                    "permission": None,
                    "error": False,
                }
                if b["name"] == "Agent":
                    call["subagent_type"] = b["input"].get("subagent_type", "general-purpose")
                    call["subagent_model"] = b["input"].get("model")
                calls.append(call)
                by_id[b["id"]] = call
        elif rec.get("type") == "user":
            decision = rec.get("permissionDecision") or {}
            for b in blocks(rec.get("message", {})):
                if b.get("type") == "tool_result" and b.get("tool_use_id") in by_id:
                    call = by_id[b["tool_use_id"]]
                    call["error"] = bool(b.get("is_error"))
                    if decision:
                        call["permission"] = f'{decision.get("decision")}:{decision.get("reasonType")}'
                    if rec.get("toolDenialKind"):
                        call["permission"] = f'denied:{rec["toolDenialKind"]}'
    return calls


def summarise(calls):
    return {
        "tool_counts": dict(collections.Counter(c["tool"] for c in calls).most_common()),
        "files_written": sorted({c["target"] for c in calls if c["tool"] in WRITE_TOOLS and c["target"]}),
        "mcp_tools": sorted({f'{c["mcp_server"]}/{c["tool"].split("__")[-1]}' for c in calls if c["kind"] == "mcp"}),
        "skills": sorted({c["target"] for c in calls if c["tool"] == "Skill"}),
        "subagents_started": [
            {"task": c["target"], "type": c.get("subagent_type"), "model": c.get("subagent_model")}
            for c in calls if c["tool"] == "Agent"
        ],
        "errors": sum(c["error"] for c in calls),
        "denied": [c["target"] for c in calls if (c["permission"] or "").startswith("denied")],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    scrub = Scrubber(args.repo.resolve())
    args.out.mkdir(parents=True, exist_ok=True)

    records = list(load(args.session))
    session_id = args.session.stem
    calls = collect_calls(records, scrub, "main")

    # One turn per human prompt; tool calls belong to the turn they fall in.
    turns = []
    for rec in records:
        prompt = human_prompt(rec)
        if prompt:
            turns.append({"start": rec["timestamp"], "prompt": scrub(prompt),
                          "permission_mode": rec.get("permissionMode"), "app": rec.get("entrypoint"),
                          "cli_version": rec.get("version")})
    for i, turn in enumerate(turns):
        end = turns[i + 1]["start"] if i + 1 < len(turns) else "9999"
        turn_calls = [c for c in calls if turn["start"] <= (c["timestamp"] or "") < end]
        turn["end"] = turn_calls[-1]["timestamp"] if turn_calls else turn["start"]
        turn["models"] = sorted({c["model"] for c in turn_calls if c["model"]})
        turn.update(summarise(turn_calls))
        turn["id"] = f"turn-{i + 1:02d}"
        turn["session_id"] = session_id

    subagents, sub_dir = [], args.session.with_suffix("") / "subagents"
    for path in sorted(sub_dir.glob("agent-*.jsonl")):
        meta_path = path.with_name(path.stem + ".meta.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        sub_records = list(load(path))
        sub_calls = collect_calls(sub_records, scrub, path.stem)
        calls.extend(sub_calls)
        stamps = [r["timestamp"] for r in sub_records if r.get("timestamp")]
        models = sorted({r["message"].get("model") for r in sub_records
                         if r.get("type") == "assistant" and r["message"].get("model")})
        subagents.append({
            "id": path.stem,
            "task": meta.get("description"),
            "agent_type": meta.get("agentType"),
            "model": models or [meta.get("model")],
            "start": stamps[0] if stamps else None,
            "end": stamps[-1] if stamps else None,
            "status": "completed" if meta.get("finished") else "unknown",
            "tool_counts": dict(collections.Counter(c["tool"] for c in sub_calls)),
            "errors": sum(c["error"] for c in sub_calls),
        })
    subagents.sort(key=lambda s: s["start"] or "")

    calls.sort(key=lambda c: c["timestamp"] or "")
    for name, rows in [("tool-calls.jsonl", calls), ("session-turns.jsonl", turns), ("subagents.jsonl", subagents)]:
        with open(args.out / name, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{len(turns)} turns, {len(calls)} tool calls, {len(subagents)} sub-agents -> {args.out}")


if __name__ == "__main__":
    main()
