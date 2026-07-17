# IDE & IM integration (M-C5)

> Status: sdlc-side contract shipped; the editor/IM plugins themselves are thin
> external shells (they call the CLI / server API and are maintained as separate
> repos or marketplace entries). This doc defines the stable contract they use.

## Principle

Integrations are **thin shells over the existing CLI/server** — they add no
core logic (per roadmap §6.2). Everything an IDE or IM plugin needs is already
exposed:

- **Machine-readable run output**: `sdlc run "<input>" --stages cr --format json`
  emits `{pipeline_id, status, cost_usd, error, stages:[{id,status,error}]}`.
- **State & approvals over HTTP** (when a server is running, M-B2):
  `GET /pipelines`, `GET /waiting`, `POST /approve`.
- **Local approval/answer** (no server): `sdlc approve|reject|answer`.

## VS Code (thin shell)

A minimal extension:
1. Command "sdlc: review selection" → runs `sdlc run <selection> --stages cr
   --format json`, parses the JSON, renders findings in a panel.
2. "sdlc: pipelines" → polls `GET /pipelines` (or local `sdlc status`) for a
   tree view.
3. Approve/reject buttons → `POST /approve` or shell out to `sdlc approve`.

No sdlc core change is required; the extension lives in its own repo and can be
published as a marketplace entry.

## IM slash commands (Feishu / Slack)

Reuses the M-B4 notification path in reverse:
- A slash command (`/sdlc review ...`) posts to the server, which runs the
  stage and replies with a card.
- Card Approve/Reject buttons call back into `POST /approve` → M-B1
  `resolve_waiting` → resume. No new approval logic.

## Verification boundary

The CLI JSON contract and server endpoints are unit-tested in-repo. The actual
VS Code extension and IM apps require their respective runtimes (editor host,
Feishu/Slack workspaces) and are verified out-of-band.
