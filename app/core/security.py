"""Security placeholder for the Centinela API.

Week 1 scope note
-----------------
Access control for Centinela is enforced at the **Azure** layer: RBAC on the
Storage account and Key Vault, network rules, and managed identities. It is
*not* enforced at the API layer this week. Therefore this module intentionally
ships no authentication or authorization logic yet.

It exists as the agreed home for future API-level concerns (e.g. API keys,
JWT validation, request signing) so they land in a predictable place when they
are introduced. Do NOT add real security logic here during Week 1.
"""

from __future__ import annotations

__all__: list[str] = []
