import secrets

import bcrypt

from app.config import login_password_hash, login_password_plain


def verify_login_password(plain: str) -> bool:
    h = login_password_hash()
    if h is not None:
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), h.encode("ascii"))
        except (ValueError, OSError):
            return False
    p = login_password_plain()
    if p is None:
        return False
    if len(plain) != len(p):
        return False
    return secrets.compare_digest(plain, p)
