import tenseal as ts
import base64
from vantage6.algorithm.tools.util import info

def as_aggregate_partial(as_context_b64: str, ciphertexts_b64: list):
    context = ts.context_from(base64.b64decode(as_context_b64))
    encrypted_vectors = [
        ts.ckks_vector_from(context, base64.b64decode(ct))
        for ct in ciphertexts_b64
    ]
    total = encrypted_vectors[0]
    for vec in encrypted_vectors[1:]:
        total = total + vec
    aggregated_b64 = base64.b64encode(total.serialize()).decode()
    info(f'AS: aggregated {len(ciphertexts_b64)} ciphertexts (no secret key used)')
    return {'aggregated': aggregated_b64}
