"""Optional self-hosted server package (M-B2/B3/B4/B6).

Currently ships the lightweight permission model (M-B6, auth.py). The HTTP
server, web console, and notification integrations land in later increments;
the CLI never depends on this package (server is always optional).
"""

from sdlc.server.auth import Role, RoleRegistry, can_approve, parse_role
from sdlc.server.backend import RemoteStateBackend, StateBackend

__all__ = [
    "RemoteStateBackend",
    "Role",
    "RoleRegistry",
    "StateBackend",
    "can_approve",
    "parse_role",
]
