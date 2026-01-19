from argon2 import PasswordHasher

ph = PasswordHasher()

def hash_string(input_string: str) -> str:
    """
    Hash a string using Argon2 and return the hash.

    :param input_string: The string to hash.
    :return: The Argon2 hash of the input string.
    """
    return ph.hash(input_string)

def verify_hash(input_string: str, hashed_string: str) -> bool:
    """
    Verify a string against a given Argon2 hash.

    :param input_string: The string to verify.
    :param hashed_string: The Argon2 hash to verify against.
    :return: True if the string matches the hash, False otherwise.
    """
    try:
        ph.verify(hashed_string, input_string)
        return True
    except Exception:
        return False
