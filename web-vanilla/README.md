# web-vanilla

Static vanilla frontend for the public `/postings` catalogue.

## Run locally

```bash
cd web-vanilla
python -m http.server 4173
```

Then open:

- `http://127.0.0.1:4173`

By default the app calls `http://127.0.0.1:8000`.
You can override API base URL in the UI (persisted in local storage + URL query param).

## Deploy

This folder is static-only and can be hosted on:

- GitHub Pages
- Cloudflare Pages

## Auth roadmap (later)

For authenticated/admin flows, keep this static app and add one of:

1. Edge proxy auth (recommended)
- Use Cloudflare Pages Functions (or a tiny backend) to attach server-side auth tokens.
- Browser never stores long-lived admin secrets.

2. Browser bearer token
- Prompt user to paste/login for a short-lived token.
- Simpler but weaker security and token handling UX.

## CORS note

The API currently does not include explicit CORS middleware in this repo.
If you host this frontend on a different origin, enable CORS in the API (or use an edge proxy on same origin).
