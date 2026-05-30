import os
import base64
import tenseal as ts
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from vantage6.algorithm.tools.util import info


def _hybrid_encrypt(plaintext: bytes, public_key_pem: str) -> dict:
    """Encrypt large data: AES-GCM for data, RSA-OAEP for the AES key."""
    aes_key = os.urandom(32)
    nonce = os.urandom(12)

    # Encrypt the CKKS context bytes with AES-GCM
    encrypted_ctx = AESGCM(aes_key).encrypt(nonce, plaintext, None)

    # Encrypt the AES key with the CP's RSA public key
    public_key = serialization.load_pem_public_key(public_key_pem.encode())
    encrypted_aes_key = public_key.encrypt(
        aes_key,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return {
        'enc_key': base64.b64encode(encrypted_aes_key).decode(),
        'nonce':   base64.b64encode(nonce).decode(),
        'enc_ctx': base64.b64encode(encrypted_ctx).decode(),
    }


def kds_partial(cp_public_keys: dict):
    """
    cp_public_keys: {str(org_id): rsa_public_key_pem}
    Returns encrypted CKKS context per CP + plain AS context (no secret key).
    """
    context = ts.context(
        ts.SCHEME_TYPE.CKKS,
        poly_modulus_degree=8192,
        coeff_mod_bit_sizes=[60, 40, 40, 60]
    )
    context.generate_galois_keys()
    context.global_scale = 2 ** 40

    cp_context_bytes = context.serialize(save_secret_key=True)
    as_context_b64  = base64.b64encode(context.serialize(save_secret_key=False)).decode()

    encrypted_cp_contexts = {}
    for org_id, public_key_pem in cp_public_keys.items():
        encrypted_cp_contexts[str(org_id)] = _hybrid_encrypt(cp_context_bytes, public_key_pem)
        info(f'KDS: CKKS context encrypted for org {org_id}')

    info('KDS: Key generation complete — secret key never left this node in plaintext')
    return {
        'encrypted_cp_contexts': encrypted_cp_contexts,
        'as_context': as_context_b64,
    }
