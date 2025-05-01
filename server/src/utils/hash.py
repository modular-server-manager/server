import hashlib

def hash_string(input_string: str) -> str:
    """
    Hash a string using SHA-256 and return the hexadecimal representation.
    
    :param input_string: The string to hash.
    :return: The SHA-256 hash of the input string in hexadecimal format.
    """
    sha256_hash = hashlib.sha256()
    sha256_hash.update(input_string.encode('utf-8'))
    return sha256_hash.hexdigest()
