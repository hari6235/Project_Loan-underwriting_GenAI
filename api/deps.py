# FILE: api/deps.py
"""Auth & role resolution dependency (Section 2.2's pipeline stage
"Auth & Role Resolution", first in the extended pipeline).

Simplification note: this is a header-based role resolver
(`X-User-Role`), not a full JWT/OAuth implementation -- the tech-stack
table suggests "JWT-based auth middleware" as the production target, but
issuing/verifying JWTs requires an identity provider this course project
doesn't have. The header-based resolver is a genuine, working
implementation of the SAME downstream contract (get_role_registry().get(role_name)
-> Role with allowed_doc_types), so swapping in real JWT verification
later only requires replacing resolve_role()'s body -- every RBAC
consumer (rbac/filter.py, rbac/validator.py, chains/*) is unaffected.

Fails closed: no header -> "junior_analyst" (least-privilege), not "credit_head".
"""
from fastapi import Header

from rbac.role_registry import get_role_registry

DEFAULT_ROLE = "junior_analyst"


def resolve_role(x_user_role: str = Header(default=DEFAULT_ROLE, alias="X-User-Role")) -> str:
    registry = get_role_registry()
    role_name = (x_user_role or DEFAULT_ROLE).strip()
    if role_name not in registry.roles:
        # Unknown role header -> fail closed to the default, not to the
        # requested (unrecognised) name, so callers can't probe for
        # privileges by sending arbitrary role strings.
        return DEFAULT_ROLE
    return role_name