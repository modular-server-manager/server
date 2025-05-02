import hashlib

from argon2 import PasswordHasher

ph = PasswordHasher()

def hash_string(input_string: str) -> str:
    """
    Hash a string using Argon2 and return the hash.
    
    :param input_string: The string to hash.
    :return: The Argon2 hash of the input string.
    """
    return ph.hash(input_string)
