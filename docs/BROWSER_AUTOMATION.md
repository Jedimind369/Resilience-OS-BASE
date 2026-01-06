# Browser Automation (How an agent can “drive the browser”)

## Default principle: API-first
If a task has an HTTP API or CLI, **use that**. It is:
- more reliable than UI clicking
- easier to test
- easier to keep offline-first

Examples:
- GitHub: use `gh` CLI / GitHub API instead of opening Settings pages
- Local dashboard: use `curl http://127.0.0.1:<port>/api/status` instead of scraping the DOM

## When UI automation is actually needed
Use browser automation only for:
- login flows with MFA
- pages with no stable API
- one-time human confirmations

## Recommended stack (cross-platform)
**Playwright** is the most robust choice:
- deterministic selectors
- headless mode
- network interception if needed

High-level architecture:
1) A “planner” agent decides the intent (e.g. “create release”, “set repo description”).
2) A “tooling” layer chooses the safest action:
   - if API available → use API
   - else → use Playwright to drive Chromium
3) A “verifier” step confirms success (DOM check + API check).

## macOS fallback (last resort)
You *can* use AppleScript (`osascript`) to drive Safari/Chrome, but it is brittle.
Use it only for small, local flows.

## Security rules (mandatory)
- Never store tokens in scripts.
- Never paste secrets into the browser automation input.
- Always log only **high-level** events (no sensitive values).
