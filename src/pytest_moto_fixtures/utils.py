"""Utils functions."""

from random import choice
from string import ascii_letters, digits


def randstr(*, chars: str = ascii_letters + digits, length: int = 10) -> str:
    """Generate a random string.

    Args:
        chars: Characters that can be used to generate the string.
        length: Length of generated string.

    Returns:
        Generated string.
    """
    return ''.join(choice(chars) for _ in range(length))