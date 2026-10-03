import os
import binascii
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from django.conf import settings


def _get_encryption_key() -> bytes:
    # Check Django settings first; only fall back to env if settings attribute is missing entirely
    raw_key = getattr(settings, 'ENCRYPTION_KEY', None)
    if raw_key is None:
        raw_key = os.getenv('ENCRYPTION_KEY', '')
    if not raw_key:
        raise ValueError("ENCRYPTION_KEY is not configured in environment settings.")
    try:
        key_bytes = binascii.unhexlify(raw_key.strip())
        if len(key_bytes) != 32:
            raise ValueError(f"ENCRYPTION_KEY must decode to exactly 32 bytes, got {len(key_bytes)}.")
        return key_bytes
    except binascii.Error as e:
        raise ValueError(f"Invalid hex string in ENCRYPTION_KEY: {e}")


def encrypt_text(plaintext: str) -> str:
    """
    Encrypts UTF-8 plaintext using AES-256-CBC with PKCS7 padding.
    Output format: 32 hex chars IV + hex ciphertext (matching original encryption.ts).
    """
    if not plaintext:
        return ""
    key = _get_encryption_key()
    iv = os.urandom(16)
    
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()
    
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()
    
    return binascii.hexlify(iv).decode('ascii') + binascii.hexlify(ciphertext).decode('ascii')


def decrypt_text(payload: str) -> str:
    """
    Decrypts AES-256-CBC hex payload (or legacy gc:v1: AES-GCM).
    """
    if not payload:
        return ""
    key = _get_encryption_key()
    cleaned = payload.strip()

    # Legacy AES-GCM check (prefix gc:v1:<iv>:<tag>:<ciphertext>)
    if cleaned.startswith("gc:v1:"):
        parts = cleaned.split(":")
        # Format: gc:v1:<iv_hex>:<tag_hex>:<ciphertext_hex> → 5 parts
        if len(parts) == 5:
            iv = binascii.unhexlify(parts[2])
            tag = binascii.unhexlify(parts[3])
            ct = binascii.unhexlify(parts[4])
            cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            return (decryptor.update(ct) + decryptor.finalize()).decode('utf-8')

    # Standard AES-256-CBC (iv: 16 bytes = 32 hex chars, rest ciphertext)
    if len(cleaned) < 34:
        raise ValueError("Ciphertext payload is too short or malformed.")

    try:
        iv = binascii.unhexlify(cleaned[:32])
        ciphertext = binascii.unhexlify(cleaned[32:])
    except binascii.Error as e:
        raise ValueError(f"Malformed hex string: {e}")

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    plaintext = unpadder.update(padded_plaintext) + unpadder.finalize()
    return plaintext.decode('utf-8')
