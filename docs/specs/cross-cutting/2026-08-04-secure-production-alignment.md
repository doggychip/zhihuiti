# Secure Production Alignment

## Goal

Make the public Zhihuiti deployment safe, observable, and consistent with the
current Python runtime while keeping all autonomous execution and trading off.

## Scope

- Require an operator bearer token for every state-changing API request and for
  reading individual goal results.
- Restrict browser CORS to the configured public frontend origin.
- Reject oversized or malformed request bodies without invoking a handler.
- Add shallow `/healthz` and dependency-aware `/readyz` JSON endpoints that
  report the deployed commit without exposing secrets.
- Keep the public Evolution response aggregate-only.
- Make AlphaArena fail closed when no URL is explicitly configured.
- Remove tracked virtual environments and runtime databases from the repository.
- Update the Lovable UI so it exposes read-only status and clearly separates
  live data from deterministic demonstrations.
- Deploy the exact merged commits and perform one minimal DeepSeek readiness
  probe. Do not run agents, evaluations, evolution, canaries, or trades.

## Out of Scope

- Enabling autonomous evolution or trading.
- Running the shadow evaluation suite or promoting a candidate.
- Rewriting Git history to remove old artifacts.
- Adding a new authentication provider or dependency.

## Acceptance Criteria

1. An unauthenticated POST to an existing API route returns `401`; the same
   request with the configured bearer token reaches normal validation.
2. If no operator token is configured, protected requests fail closed with
   `503`.
3. Browser CORS permits `https://zhihuiti.lovable.app` by default and does not
   grant access to an unrelated origin.
4. Requests over the configured body limit return `413`, and malformed JSON
   returns `400`.
5. `/healthz` and `/readyz` return JSON; `/readyz` reports LLM and operator-token
   configuration and the deployed commit without making an external model call.
6. Unknown `/api/*` routes return JSON `404`.
7. `/api/evolution` exposes counts and running state but not goal text or output.
8. The public frontend contains no goal-run or collision execution control and
   the Evolution page labels live status separately from any simulation.
9. `.venv` and SQLite runtime databases are no longer tracked, while existing
   local copies are preserved.
10. Focused tests and the full test suite pass; the merged backend and frontend
    commits match the commits verified in production.

## Safety Constraints

- `tools_enabled` remains false.
- `ZHIHUITI_AUTO_EVOLVE` and AlphaArena auto-trading remain disabled.
- API keys and operator tokens never enter frontend code or logs.
- Error responses are generic for unexpected server failures.
