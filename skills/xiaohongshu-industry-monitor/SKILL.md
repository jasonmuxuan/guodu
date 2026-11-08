---
name: xiaohongshu-industry-monitor
description: Use for verified Xiaohongshu industry monitoring.
license: MIT
metadata:
  hermes:
    tags: [xiaohongshu, opencli, chrome, monitoring, verification]
    related_skills: [xiaohongshu-browser-capture, xiaohongshu-obsidian-ingest]
---

# Xiaohongshu Industry Monitor

## Overview

Use a real logged-in Xiaohongshu browser context to build a reliable industry-content list. This packages the successful workflow separating transport health, login state, URL validity, and detail verification.

> A scheduler or command returning `ok` is not collection success. Success requires browser login evidence, a usable note URL, and verified note-detail data.

## When to Use

Use for recurring topic monitoring, product/system/workflow searches, engagement filtering, and jobs previously blocked by `300012`, `AUTH_REQUIRED`, login walls, bare note IDs, or missing metrics.

Do not use merely to download one known video.

## Bundled Tools

- `scripts/xhs_monitor.py`: preflight, search, verification, deduplication.
- `references/opencli-command-guide.md`: commands, failure signatures, browser fallback.
- `templates/report.md`: final report structure.

Required command: `opencli`.

## Workflow

### 1. Preflight the exact context

```bash
python3 scripts/xhs_monitor.py preflight --session xhscheck
```

Checks `opencli doctor`, `xiaohongshu whoami`, persistent browser state, and login-wall signals. Proceed only when JSON has `ready: true`. If false, report the failed gate; do not keep changing queries when authentication is the blocker.

### 2. Search through the persistent logged-in context

```bash
python3 scripts/xhs_monitor.py batch-search \
  --query '题库系统' --query 'AI题库' \
  --query '讲义排版' --query '教辅排版' \
  --session xhscheck --output /tmp/xhs-results.json
```

Keep the same session and Chrome profile for all steps.

### 3. Recover real note URLs

Prefer full `explore/...` URLs. When a bare ID is insufficient, navigate in the same browser session and obtain the current/canonical URL, including `xsec_token` when present. Never manufacture a token or claim a bare ID is signed.

### 4. Verify candidates at detail level

```bash
python3 scripts/xhs_monitor.py verify \
  --input /tmp/xhs-results.json \
  --min-likes 21 --min-saves 21 \
  --output /tmp/xhs-verified.json
```

Formal results require author, meaningful title/description, clickable URL, likes, saves, threshold compliance, and topic relevance. Missing metrics go to `rejected` with a reason.

### 5. Deduplicate before reporting

Order: note ID, normalized canonical URL, normalized author + title. Pass `--previous old-results.json` to exclude already reported notes.

### 6. Handle risk controls without blind retries

For `300012`: keep the same logged-in session, use page search/navigation, collect real links from visible DOM or hydrated data, and verify candidates individually. Stop only when adapter and browser routes are both blocked. Read the reference before manual fallback.

### 7. Report with evidence

Use the template. State candidate, verified, rejected, duplicate counts; login evidence; URL shape; and limitations. Never say “采集成功” merely because cron execution succeeded.

## Education Topic Pack

**Question-bank:** 题库, AI题库, 智能题库, 题库系统, 自动组卷, 试题库, 校本题库, 智慧作业

**Typesetting:** 讲义排版, 教辅排版, 试卷排版, 自动排版, AI排版, 教案排版, 教材排版

Typical filter: likes > 20 and saves > 20. Do not substitute comments for saves.

## Common Pitfalls

1. Doctor does not prove login.
2. Global Chrome login does not prove the controlled context is logged in.
3. A bare note ID may not be a usable signed URL.
4. Search-card numbers are not final until detail verification.
5. After `300012`, switch routes instead of blind retries.
6. Cron `ok` is not business success.
7. Do not archive before verification.

## Verification Checklist

- [ ] `opencli` exists and doctor completed.
- [ ] Exact persistent context is authenticated.
- [ ] Browser state has no login-wall text.
- [ ] Candidates have real note URLs.
- [ ] Formal results have verified likes and saves.
- [ ] Threshold semantics match the request.
- [ ] Current and previous results are deduplicated.
- [ ] Rejections retain machine-readable reasons.
- [ ] Report distinguishes execution from collection success.
