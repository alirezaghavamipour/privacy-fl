# Privacy-Preserving Federated Learning

Homomorphic encryption-based federated learning on vantage6 using TenSEAL (CKKS).

## Algorithm Images

| Image | Purpose |
|---|---|
| `privacy-fl-kds` | Key Distribution Server: generates CKKS keys, encrypts per CP using RSA hybrid encryption |
| `privacy-fl-worker` | Worker: CP encrypt/decrypt + AS homomorphic aggregation + central orchestrator |

## Security

- CKKS secret key never leaves the KDS node in plaintext
- Each CP receives its key package encrypted with its own RSA public key (hybrid RSA+AES)
- The AS only ever holds the public CKKS context and cannot decrypt
- vantage6 server only sees encrypted blobs
