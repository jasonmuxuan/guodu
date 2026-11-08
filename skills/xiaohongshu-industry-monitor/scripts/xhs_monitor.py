#!/usr/bin/env python3
"""Verified Xiaohongshu monitoring helper built around OpenCLI."""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

LOGIN_WALL = ("登录后推荐更懂你的笔记", "手机号登录", "扫码登录", "登录/注册")


def run(cmd, timeout=180):
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
    return {"ok": p.returncode == 0, "code": p.returncode,
            "stdout": p.stdout.strip(), "stderr": p.stderr.strip(), "cmd": cmd}


def parse_json(text):
    try:
        return json.loads(text)
    except Exception:
        # OpenCLI may print update notices around a JSON envelope.
        starts = [m.start() for m in re.finditer(r"[\[{]", text)]
        for start in starts:
            try:
                return json.JSONDecoder().raw_decode(text[start:])[0]
            except Exception:
                pass
        return None


def payload(obj):
    if isinstance(obj, dict) and "data" in obj:
        return obj["data"]
    return obj


def as_items(obj):
    obj = payload(obj)
    if isinstance(obj, list): return obj
    if isinstance(obj, dict):
        for key in ("items", "notes", "results", "feeds", "list"):
            if isinstance(obj.get(key), list): return obj[key]
        return [obj]
    return []


def first(d, names, default=None):
    if not isinstance(d, dict): return default
    for name in names:
        if name in d and d[name] not in (None, ""): return d[name]
    for v in d.values():
        if isinstance(v, dict):
            got = first(v, names)
            if got not in (None, ""): return got
    return default


def number(v):
    if isinstance(v, (int, float)): return int(v)
    if v is None: return None
    s = str(v).strip().replace(",", "")
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([万千wWkK]?)", s)
    if not m: return None
    n = float(m.group(1)); unit = m.group(2).lower()
    if unit in ("万", "w"): n *= 10000
    elif unit in ("千", "k"): n *= 1000
    return int(n)


def canonical(url):
    if not url: return ""
    try:
        p = urlsplit(str(url)); return urlunsplit((p.scheme, p.netloc, p.path.rstrip("/"), p.query, ""))
    except Exception: return str(url)


def normalize(item, query=None):
    author = first(item, ("author", "nickname", "user_name", "username"), "")
    if isinstance(author, dict): author = first(author, ("nickname", "name", "username"), "")
    return {
        "query": query or item.get("query", "") if isinstance(item, dict) else query,
        "note_id": str(first(item, ("note_id", "noteId", "id", "note_id_str"), "")),
        "title": str(first(item, ("title", "display_title", "desc", "description"), "")).strip(),
        "author": str(author).strip(),
        "url": canonical(first(item, ("url", "note_url", "share_url", "link"), "")),
        "likes": number(first(item, ("likes", "liked_count", "like_count", "likedCount"))),
        "saves": number(first(item, ("saves", "collected_count", "collect_count", "collectedCount", "收藏"))),
        "comments": number(first(item, ("comments", "comment_count", "commentCount"))),
        "type": first(item, ("type", "note_type", "noteType"), ""),
        "published_at": first(item, ("published_at", "publish_time", "time", "date"), ""),
        "raw": item,
    }


def write(obj, path=None):
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True); Path(path).write_text(text, encoding="utf-8")
    print(text)


def preflight(args):
    if not shutil.which("opencli"):
        write({"ready": False, "gate": "tool", "error": "opencli not found"}); return 2
    doctor = run(["opencli", "doctor"], 90)
    who = run(["opencli", "xiaohongshu", "whoami", "--window", "background", "--site-session", "persistent", "-f", "json"], 120)
    run(["opencli", "browser", "--session", args.session, "--window", "background", "open", "https://www.xiaohongshu.com"], 90)
    state = run(["opencli", "browser", "--session", args.session, "state"], 90)
    who_obj = parse_json(who["stdout"])
    logged = bool(first(payload(who_obj), ("logged_in", "loggedIn", "authenticated"), False)) if who_obj is not None else False
    combined = state["stdout"] + "\n" + state["stderr"]
    wall = [x for x in LOGIN_WALL if x in combined]
    ready = doctor["ok"] and who["ok"] and logged and state["ok"] and not wall
    result = {"ready": ready, "transport_ok": doctor["ok"], "whoami_ok": who["ok"],
              "logged_in": logged, "browser_state_ok": state["ok"], "login_wall_signals": wall,
              "account": payload(who_obj), "session": args.session,
              "errors": [x for x in (doctor["stderr"], who["stderr"], state["stderr"]) if x]}
    write(result, args.output)
    return 0 if ready else 3


def search_one(query, limit, sort):
    r = run(["opencli", "xiaohongshu", "search", query, "--limit", str(limit), "--sort", sort,
             "--window", "background", "--site-session", "persistent", "--keep-tab", "true",
             "--trace", "retain-on-failure", "-f", "json"], 240)
    obj = parse_json(r["stdout"])
    return r, [normalize(x, query) for x in as_items(obj)] if obj is not None else []


def batch_search(args):
    all_items, runs = [], []
    for q in args.query:
        r, items = search_one(q, args.limit, args.sort)
        runs.append({"query": q, "ok": r["ok"], "count": len(items), "stderr": r["stderr"]})
        all_items.extend(items)
    out = {"queries": args.query, "candidate_count": len(all_items), "runs": runs, "items": all_items}
    write(out, args.output)
    return 0 if any(x["ok"] for x in runs) else 4


def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))


def verify(args):
    source = load(args.input); items = source.get("items", source if isinstance(source, list) else [])
    previous_keys = set()
    if args.previous:
        old = load(args.previous)
        for x in old.get("verified", old.get("items", old if isinstance(old, list) else [])):
            n = normalize(x); previous_keys |= keys(n)
    seen, verified, rejected, duplicates = set(), [], [], []
    for original in items:
        candidate = normalize(original)
        k = keys(candidate)
        if k & (seen | previous_keys):
            candidate["reason"] = "duplicate_current_or_previous"; duplicates.append(candidate); continue
        seen |= k
        target = candidate["url"] or candidate["note_id"]
        if not target:
            candidate["reason"] = "missing_url_and_note_id"; rejected.append(candidate); continue
        r = run(["opencli", "xiaohongshu", "note", target, "--window", "background",
                 "--site-session", "persistent", "--trace", "retain-on-failure", "-f", "json"], 240)
        detail_obj = parse_json(r["stdout"])
        if not r["ok"] or detail_obj is None:
            candidate["reason"] = "detail_fetch_failed"; candidate["error"] = r["stderr"] or r["stdout"][-500:]; rejected.append(candidate); continue
        detail_items = as_items(detail_obj)
        detail = normalize(detail_items[0] if detail_items else payload(detail_obj), candidate.get("query"))
        for field in ("note_id", "title", "author", "url", "likes", "saves", "comments", "type", "published_at"):
            if detail.get(field) in (None, ""): detail[field] = candidate.get(field)
        reasons = []
        if not detail["title"]: reasons.append("missing_title")
        if not detail["author"]: reasons.append("missing_author")
        if not detail["url"]: reasons.append("missing_clickable_url")
        if detail["likes"] is None: reasons.append("missing_likes")
        elif detail["likes"] < args.min_likes: reasons.append("likes_below_threshold")
        if detail["saves"] is None: reasons.append("missing_saves")
        elif detail["saves"] < args.min_saves: reasons.append("saves_below_threshold")
        if reasons: detail["reason"] = ",".join(reasons); rejected.append(detail)
        else: verified.append(detail)
    out = {"candidate_count": len(items), "verified_count": len(verified), "rejected_count": len(rejected),
           "duplicate_count": len(duplicates), "thresholds": {"likes_min_inclusive": args.min_likes, "saves_min_inclusive": args.min_saves},
           "verified": verified, "rejected": rejected, "duplicates": duplicates}
    write(out, args.output); return 0


def keys(n):
    out = set()
    if n.get("note_id"): out.add("id:" + n["note_id"])
    if n.get("url"): out.add("url:" + canonical(n["url"]).lower())
    if n.get("author") and n.get("title"):
        clean = lambda s: re.sub(r"\s+", "", str(s)).lower()
        out.add("at:" + clean(n["author"]) + "|" + clean(n["title"]))
    return out


def parser():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("preflight"); a.add_argument("--session", default="xhscheck"); a.add_argument("--output"); a.set_defaults(fn=preflight)
    for name in ("search", "batch-search"):
        a = sub.add_parser(name); a.add_argument("--query", action="append", required=True); a.add_argument("--session", default="xhscheck")
        a.add_argument("--limit", type=int, default=20); a.add_argument("--sort", default="comprehensive", choices=("comprehensive","latest","most-liked","most-commented","most-collected")); a.add_argument("--output", required=True); a.set_defaults(fn=batch_search)
    a = sub.add_parser("verify"); a.add_argument("--input", required=True); a.add_argument("--previous"); a.add_argument("--min-likes", type=int, default=21); a.add_argument("--min-saves", type=int, default=21); a.add_argument("--output", required=True); a.set_defaults(fn=verify)
    return p

if __name__ == "__main__":
    args = parser().parse_args()
    try: sys.exit(args.fn(args))
    except subprocess.TimeoutExpired as e:
        write({"ok": False, "error": "timeout", "command": e.cmd}); sys.exit(5)
