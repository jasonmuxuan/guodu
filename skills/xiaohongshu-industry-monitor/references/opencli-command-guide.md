# OpenCLI Command Guide

## Preflight

```bash
opencli doctor
opencli xiaohongshu whoami --window background --site-session persistent -f json
opencli browser --session xhscheck --window background open https://www.xiaohongshu.com
opencli browser --session xhscheck state
```

Transport health and login are separate. Login-wall signals include `登录后推荐更懂你的笔记`, `手机号登录`, `扫码登录`, and `AUTH_REQUIRED`.

## Search

```bash
opencli xiaohongshu search '智能题库' \
  --limit 20 --sort comprehensive \
  --window background --site-session persistent \
  --keep-tab true --trace retain-on-failure -f json
```

Useful sorts: `latest`, `most-liked`, `most-commented`, `most-collected`.

## Detail verification

The note command expects a full Xiaohongshu note URL with `xsec_token`:

```bash
opencli xiaohongshu note '<full-signed-url>' \
  --window background --site-session persistent \
  --trace retain-on-failure -f json
```

## Browser fallback after 300012

Do not loop adapter search. Keep the same browser session:

```bash
opencli browser --session xhscheck state
opencli browser --session xhscheck get url
opencli browser --session xhscheck eval '<javascript>'
```

Navigate using visible search controls or a search URL in the authenticated page. Extract `a[href*="/explore/"]` links and preserve their query strings. Open each candidate and read its current URL or canonical link. Then run note verification.

Example DOM inspection:

```javascript
JSON.stringify(Array.from(document.querySelectorAll('a[href*="/explore/"]')).map(a => ({
  title: (a.innerText || a.getAttribute('aria-label') || '').trim(),
  url: new URL(a.href, location.href).href
})).filter(x => x.url))
```

## Error interpretation

- `AUTH_REQUIRED`: fix login state; query changes will not help.
- `300012`: network-risk on search route; switch to authenticated browser-page search.
- `note now requires a full signed URL`: obtain the real URL from the live page; do not pass a bare ID.
- Missing saves: reject from a likes+saves threshold list instead of guessing.

## Completion evidence

A successful collection has all of:
1. transport check;
2. authenticated account evidence;
3. browser state without login wall;
4. real candidate URLs;
5. successful detail payloads;
6. verified threshold metrics;
7. deduplication counts.
