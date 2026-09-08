# Guarded Core operator endpoints

These endpoints are **disabled by default**. Deployment and enabling
`ZHIHUITI_CONTROLLED_OPERATIONS=1` require operator approval. They use the
already-initialized runtime; they never construct another Orchestrator.
All endpoints below require the existing operator Bearer credential.
Never place that credential in source, request bodies, logs, or saved examples.

## Contract

1. `POST /api/operations/readiness` with
   `{"request_id":"core-probe-unique-id"}`.
   Makes at most one primary DeepSeek / deepseek-chat request, with three output
   tokens, no retries, no credential/provider fallback, and a 30-second HTTP
   inactivity timeout. Success requires exactly `OK`.
   Updates the persisted population `llm_gate` and probe timestamp without
   rotation, spawning, culling, task execution, or quota reset.
2. `POST /api/tasks/controlled` with
   `{"request_id":"core-task-unique-id","agent_id":"existing-agent-id"}`.
   Requires a successful probe from this process within ten minutes and no
   intervening model call. Reuses an alive, active, sufficiently funded analyst,
   researcher, or auditor. Builds a fixed assignment from server-side telemetry;
   no caller-supplied prompts, roles, model overrides, tools, or delegation.
   Charges the existing five simulated budget-unit task fee once. Makes at most
   one primary model request with a maximum 1,536 output tokens.
3. `GET /api/operations/controlled/:request_id` retrieves the durable request
   result. The ID must be 8–80 ASCII letters, numbers, underscores, or hyphens.

Duplicate IDs replay the saved result, including failures. Reusing an ID for a
different operation/agent returns 409. In-flight or interrupted records return
202 and **must not be replaced with a fresh ID to retry paid work**.

Daily limits: 24 probe attempts with at least one minute between starts, and six
task attempts with at least four hours between starts. Failed/ambiguous attempts
count. A persisted single-flight reservation blocks overlapping controlled work
and legacy operator POSTs. Running/pending tasks, active goals/rotation,
autonomous evolution, tools-enabled runtime, more than 30 alive agents, or
unsupported/fallback provider state block new requests.

## Results and boundaries

Task state is persisted before the model request and after completion.
`work_status=validated` means the existing deterministic JSON/evidence-field
checks passed. It is **not** independent fact-checking, an inspection score, a
promotion, or human approval. Invalid output is marked rejected, without a
repair call. Outputs remain private to the operator request/task store; they
are not added to the public research feed. No agent scores, genes, or
autonomous evolution settings are promoted or changed.

Existing legacy endpoints are not otherwise redesigned by this patch.
Operators must keep external collectors/CLI jobs and recurring work paused for
the manual trial. Run a single initialized server process per database; the
legacy runtime has in-memory agents/goals and is not a multi-worker coordinator.
The HTTP timeout bounds inactivity, not total wall-clock time. A client timeout
does not cancel the server call: query the original request ID before acting.

## Interrupted-request recovery

An interrupted reservation deliberately stays active across restarts. There
is no automatic lease expiry or reset endpoint. An operator must reconcile
the saved request ID, task row, provider outcome, budget fee, and all active
collectors before authorizing a targeted repair. Do not delete the record,
forge a readiness result, or launch a replacement while the outcome is unknown.
Storage uses namespaced entries in the existing `economy_state` table; no
schema migration or destructive cleanup is required.

## Verification before deployment

Run the controlled-operation, Oracle HTTP, population, research-validation,
agent, and LLM regression tests with mocked providers. Confirm production
credentials are stable and other collectors are paused. Deploy this change
only after approval, enable the opt-in switch, then verify the deployed commit,
authenticated probe result, and one persisted task result. Keep autonomous
evolution off and do not resume recurring work based only on a local test.
