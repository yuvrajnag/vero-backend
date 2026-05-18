import re

def validate_password_strength(password: str) -> bool:
    """
    Validate that password is at least 8 characters long,
    contains at least one uppercase, one lowercase, and one digit.
    """
    if len(password) < 8:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[0-9]", password):
        return False
    return True
