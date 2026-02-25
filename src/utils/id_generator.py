import secrets
import string


def generate_unique_code(length: int = 11) -> str:
    """Генерирует уникальный буквенно-цифровой код (например для unique_code продукции)."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
