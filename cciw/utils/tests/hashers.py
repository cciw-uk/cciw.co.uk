from collections import OrderedDict

from django.contrib.auth.hashers import BasePasswordHasher, mask_hash


class PlainPasswordHasher(BasePasswordHasher):
    "Plain password hashing algorithm for tests (DO NOT USE in production)."

    algorithm = "plain"

    def salt(self):
        """Return empty string (dummy salt generation).
        >>> hasher = PlainPasswordHasher()
        >>> hasher.salt()
        ''
        """
        return ""

    def encode(self, password: str, salt: str) -> str:
        """Return ``password`` encoded with noop algorithm; whatever ``salt``.
        >>> hasher = PlainPasswordHasher()
        >>> hasher.encode('secret', 'fake salt')
        u'plain$$secret'
        """
        return f"{self.algorithm}$${password}"

    def verify(self, password: str, encoded: str) -> bool:
        """Return ``True`` if ``password`` matches ``encoded``.
        >>> hasher = PlainPasswordHasher()
        >>> hasher.verify('right', 'plain$$right')
        True
        >>> hasher.verify('wrong', 'plain$$right')
        False
        Raises ``AssertionError`` if ``encoded``'s algorithm does is not
        :py:attr:`algorithm`.
        >>> hasher.verify('secret', 'md5$$not a plain password')
        ... # Doctest: +ELLIPSIS
        Traceback (most recent call last):
           ...
        AssertionError
        """
        algorithm, hash = encoded.split("$$", 1)
        assert algorithm == self.algorithm
        return password == hash

    def safe_summary(self, encoded):
        """Returns a summary of safe values.
        The result is an :py:class:``~collections.OrderedDict`` and will be
        used where the password field must be displayed to construct a safe
        representation of the password.
        >>> hasher = PlainPasswordHasher()
        >>> hasher.safe_summary(hasher.encode('secret', 'salt'))
        OrderedDict([('algorithm', 'plain'), ('hash', u'sec***')])
        """
        algorithm, salt, hash = encoded.split("$", 2)
        assert algorithm == self.algorithm
        return OrderedDict(
            [
                ("algorithm", self.algorithm),
                ("hash", mask_hash(hash, show=3)),
            ]
        )
