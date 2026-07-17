"""IM notification integrations (M-B4).

Builds interactive approval cards for Feishu and Slack. Card *construction* is
pure and unit-tested here; actual delivery posts to a webhook. A card button
routes back to the server's /approve (reusing M-B1's resolve_waiting), so no
new approval logic lives here. Notification failure never blocks a pipeline —
the suspension is already persisted; a card is just a reach mechanism.

The Notifier protocol lets the community add channels beyond the two shipped.
"""

from __future__ import annotations

from typing import Any, Protocol


class Notifier(Protocol):
    name: str

    def build_approval_card(self, pipeline_id: str, gate_id: str, reason: str) -> dict[str, Any]: ...

    async def notify_pending(
        self, pipeline_id: str, gate_id: str, reason: str
    ) -> bool: ...


class _WebhookNotifier:
    """Shared webhook POST with fail-safe delivery (never raises)."""

    name = "webhook"

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout

    def build_approval_card(self, pipeline_id: str, gate_id: str, reason: str) -> dict[str, Any]:
        raise NotImplementedError

    async def notify_pending(self, pipeline_id: str, gate_id: str, reason: str) -> bool:
        import httpx

        card = self.build_approval_card(pipeline_id, gate_id, reason)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                resp = await c.post(self.webhook_url, json=card)
                resp.raise_for_status()
                return True
        except Exception:
            return False


class FeishuNotifier(_WebhookNotifier):
    name = "feishu"

    def build_approval_card(self, pipeline_id: str, gate_id: str, reason: str) -> dict[str, Any]:
        return {
            "msg_type": "interactive",
            "card": {
                "header": {"title": {"tag": "plain_text", "content": "sdlc: approval needed"}},
                "elements": [
                    {"tag": "div", "text": {"tag": "lark_md",
                     "content": f"**Pipeline** {pipeline_id}\n**Gate** {gate_id}\n{reason}"}},
                    {"tag": "action", "actions": [
                        {"tag": "button", "text": {"tag": "plain_text", "content": "Approve"},
                         "type": "primary",
                         "value": {"action": "approve", "pipeline_id": pipeline_id, "gate_id": gate_id}},
                        {"tag": "button", "text": {"tag": "plain_text", "content": "Reject"},
                         "type": "danger",
                         "value": {"action": "reject", "pipeline_id": pipeline_id, "gate_id": gate_id}},
                    ]},
                ],
            },
        }


class SlackNotifier(_WebhookNotifier):
    name = "slack"

    def build_approval_card(self, pipeline_id: str, gate_id: str, reason: str) -> dict[str, Any]:
        return {
            "blocks": [
                {"type": "section", "text": {"type": "mrkdwn",
                 "text": f"*sdlc: approval needed*\n*Pipeline* {pipeline_id}\n*Gate* {gate_id}\n{reason}"}},
                {"type": "actions", "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "Approve"},
                     "style": "primary",
                     "value": f"approve:{pipeline_id}:{gate_id}", "action_id": "sdlc_approve"},
                    {"type": "button", "text": {"type": "plain_text", "text": "Reject"},
                     "style": "danger",
                     "value": f"reject:{pipeline_id}:{gate_id}", "action_id": "sdlc_reject"},
                ]},
            ],
        }


def get_notifier(channel: str, webhook_url: str) -> Notifier:
    """Factory: 'feishu' | 'slack'. Raises ValueError for unknown channels."""
    if channel == "feishu":
        return FeishuNotifier(webhook_url)
    if channel == "slack":
        return SlackNotifier(webhook_url)
    raise ValueError(f"Unknown notification channel: {channel}")
