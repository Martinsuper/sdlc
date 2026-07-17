"""Plugin marketplace (M-C2): discover, install, and publish sdlc extensions.

The distribution side of the ecosystem — a static-registry-first marketplace so
"one team's Adapter, a thousand teams use it". Installs land in the user
extension dir where the 4-layer loader already picks them up.
"""

from sdlc.market.installer import ext_dir, install_package
from sdlc.market.registry_client import Registry, RegistryClient, RegistryEntry
from sdlc.market.trust import TrustError, compute_checksum, verify_checksum

__all__ = [
    "Registry",
    "RegistryClient",
    "RegistryEntry",
    "TrustError",
    "compute_checksum",
    "ext_dir",
    "install_package",
    "verify_checksum",
]
