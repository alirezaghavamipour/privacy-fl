import os
import base64
import tenseal as ts
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from vantage6.algorithm.tools.util import info


def _hybrid_decrypt(encrypted_pkg: dict) -> bytes:
    """
    Decrypt using this node's RSA private key (from CP_RSA_PRIVATE_KEY env var).
    In production this env var is set in the vantage6 node config.
    """
    private_key_pem = os.environ.get('CP_RSA_PRIVATE_KEY')
    if not private_key_pem:
        raise RuntimeError('CP_RSA_PRIVATE_KEY environment variable is not set on this node!')

    private_key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)

    # Decrypt AES key with RSA private key
    aes_key = private_key.decrypt(
        base64.b64decode(encrypted_pkg['enc_key']),
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    # Decrypt CKKS context with AES key
    nonce = base64.b64decode(encrypted_pkg['nonce'])
    enc_ctx = base64.b64decode(encrypted_pkg['enc_ctx'])
    return AESGCM(aes_key).decrypt(nonce, enc_ctx, None)


def cp_encrypt_partial(encrypted_cp_context: dict, previous_result: float):
    """Decrypt CKKS context locally, then encrypt (5 + previous_result)."""
    cp_context_bytes = _hybrid_decrypt(encrypted_cp_context)
    context = ts.context_from(cp_context_bytes)

    local_value = 5.0 + previous_result
    encrypted = ts.ckks_vector(context, [local_value])
    ciphertext_b64 = base64.b64encode(encrypted.serialize()).decode()

    info(f'CP: locally decrypted CKKS context, encrypted (5 + {previous_result}) = {local_value}')
    return {'ciphertext': ciphertext_b64}


def cp_decrypt_partial(encrypted_cp_context: dict, aggregated_ciphertext_b64: str):
    """Decrypt CKKS context locally, then decrypt the aggregated ciphertext."""
    cp_context_bytes = _hybrid_decrypt(encrypted_cp_context)
    context = ts.context_from(cp_context_bytes)

    encrypted = ts.ckks_vector_from(context, base64.b64decode(aggregated_ciphertext_b64))
    result = encrypted.decrypt()[0]

    info(f'CP: decrypted aggregated result = {result:.6f}')
    return {'result': result}
