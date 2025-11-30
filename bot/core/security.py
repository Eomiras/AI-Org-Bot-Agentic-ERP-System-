import os
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from bot.core.config import settings

# This module implements the "PII Vault" described in Section 7.3.
# It ensures personally identifiable information is never stored in plain text.

def _derive_user_key(user_id: int) -> bytes:
    """
    Derives a unique encryption key for a specific user using the Master Key and their User ID as salt.
    This ensures that even if the DB is compromised, data cannot be decrypted without the Master Key (RAM/Env).
    """
    # Master key from environment (hex string to bytes)
    master_key_bytes = bytes.fromhex(settings.MASTER_KEY)

    # Use User ID as salt (must be bytes)
    salt = str(user_id).encode('utf-8')

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32, # AES-256 requires 32 bytes
        salt=salt,
        iterations=100000,
    )

    return kdf.derive(master_key_bytes)

def encrypt_pii(user_id: int, plaintext: str) -> str:
    """
    Encrypts a string using AES-GCM with a user-specific key.
    Returns a base64 encoded string containing the nonce and ciphertext.
    """
    key = _derive_user_key(user_id)
    nonce = os.urandom(12) # GCM standard nonce size

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()

    ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()

    # Store nonce + tag + ciphertext
    # We need the tag for authentication (included in finalize for GCM usually? No, GCM tag is separate)
    # Wait, cryptography.io generic GCM mode:
    # encryptor.tag is available after finalize.

    combined = nonce + encryptor.tag + ciphertext
    return base64.b64encode(combined).decode('utf-8')

def decrypt_pii(user_id: int, encrypted_blob: str) -> str:
    """
    Decrypts a base64 encoded PII blob.
    """
    data = base64.b64decode(encrypted_blob)

    # Extract parts
    nonce = data[:12]
    tag = data[12:28] # GCM tag is usually 16 bytes
    ciphertext = data[28:]

    key = _derive_user_key(user_id)

    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
    decryptor = cipher.decryptor()

    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    return plaintext.decode('utf-8')
