from random import randint
from string import ascii_letters, digits
from typing import Final

from pytest_moto_fixtures.utils import randstr


class TestRandStr:
    DEFAULT_CHARS: Final = ascii_letters + digits
    DEFAULT_LENGTH: Final = 10

    def test_default_args(self) -> None:
        returned = randstr()

        assert len(returned) == self.DEFAULT_LENGTH
        for char in returned:
            assert char in self.DEFAULT_CHARS

    def test_chars(self) -> None:
        returned = randstr(chars=digits)

        assert len(returned) == self.DEFAULT_LENGTH
        for char in returned:
            assert char in digits

    def test_length(self) -> None:
        length = randint(3, 12)

        returned = randstr(length=length)

        assert len(returned) == length
        for char in returned:
            assert char in self.DEFAULT_CHARS
