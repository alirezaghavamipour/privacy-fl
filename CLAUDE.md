# Privacy-Preserving Federated Learning — Project Guide

## Architecture

Three-party system using TenSEAL CKKS homomorphic encryption on vantage6 v4.15.1:

```
Researcher
    │
    ├─► KDS node  → generates CKKS key pair
    │              → encrypts secret key per CP using RSA+AES hybrid
    │              → returns encrypted_cp_contexts + as_context
    │
    └─► Worker central node (KDS org)
            │
            ├─► CP1 node  → RSA-decrypts CKKS context → encrypts local value
            ├─► CP2 node  → RSA-decrypts CKKS context → encrypts local value
            ├─► AS node   → homomorphic aggregation (no secret key)
            ├─► CP1 node  → decrypts aggregated result
            └─► CP2 node  → decrypts aggregated result
```

**Privacy guarantee:** The CKKS secret key is generated on the KDS node and never transmitted in plaintext. Each CP receives its own RSA-encrypted package. The AS performs addition on ciphertexts without ever accessing the secret key.

## Docker Images

Built automatically by GitHub Actions on every push → published to GitHub Container Registry:

| Image | Registry |
|-------|----------|
| KDS algorithm | `ghcr.io/alirezaghavamipour/privacy-fl/privacy-fl-kds:main` |
| Worker (CP + AS + central) | `ghcr.io/alirezaghavamipour/privacy-fl/privacy-fl-worker:main` |

Both images are **public**. No authentication needed to pull.

## Code Structure

```
privacy-fl/
├── privacy-fl-kds/
│   ├── kds_pkg/
│   │   ├── __init__.py        # exports kds_partial
│   │   └── kds.py             # CKKS key gen + RSA+AES hybrid encryption
│   ├── setup.py
│   └── Dockerfile
├── privacy-fl-worker/
│   ├── worker_pkg/
│   │   ├── __init__.py        # exports central, cp_*, as_*
│   │   ├── central.py         # @algorithm_client orchestrator
│   │   ├── cp.py              # cp_encrypt_partial, cp_decrypt_partial
│   │   └── as_.py             # as_aggregate_partial
│   ├── setup.py
│   └── Dockerfile
└── .github/workflows/build.yml   # matrix build → ghcr.io
```

`wrap_algorithm()` reads `PKG_NAME` env var (set in Dockerfile) to discover and route to functions. This is why each image needs `setup.py` + `__init__.py`.

## Server (SURF Research Cloud)

```
Host:  aghavamipo@145.38.195.178
venv:  /home/aghavamipo/venv/
```

Always activate the venv before running Python or v6 commands:
```bash
source /home/aghavamipo/venv/bin/activate
```

**Write files locally, then scp — never use heredocs over SSH** (they mangle Python indentation).

## vantage6 Stack on the Server

### Organizations & Nodes

| Org  | Org ID | Node ID | Node API Key                           |
|------|--------|---------|----------------------------------------|
| KDS  | 2      | 2       | `861d7dd1-be7a-4c7e-881d-29ffddd4d6d5` |
| CP1  | 3      | 3       | `de61a1b0-453f-4bbc-bf88-b74c0f8ab8dc` |
| CP2  | 4      | 4       | `fc719ab4-6b0c-44fe-a04e-5bcabd19fb1e` |
| AS   | 5      | 5       | `6e073bed-da43-4fcd-92f5-0eebb48955e9` |

- Collaboration ID: `1`, name: `privacy-fl-collab`
- Server credentials: `root` / `root`
- Researcher user: `researcher` / `Research@123` (org=KDS, role=Collaboration Admin)

### Key File Locations

| File/Dir | Purpose |
|----------|---------|
| `/home/aghavamipo/.config/vantage6/server/test.yaml` | Server config |
| `/home/aghavamipo/.config/vantage6/node/{kds,cp1,cp2,as}.yaml` | Node configs |
| `/home/aghavamipo/.local/share/vantage6/server/test/test.sqlite` | Database |
| `/home/aghavamipo/fl-keys/cp{1,2}_{private,public}.pem` | RSA key pairs |
| `/home/aghavamipo/e2e_test.py` | End-to-end test script |

### Node Config Notes

- All nodes use `node_extra_hosts: {v6server: host-gateway}` and `server_url: http://v6server` so Docker containers can reach the host-bound server
- CP1 and CP2 nodes have `algorithm_env: {CP_RSA_PRIVATE_KEY: "..."}` — this passes the private key into algorithm containers at runtime

## Starting the Stack

After a server reboot, run in order:

```bash
source /home/aghavamipo/venv/bin/activate

# 1. Start server
v6 server start -n test --user

# 2. Wait ~10 seconds, then start nodes
v6 node start -n kds --user --keep
v6 node start -n cp1 --user --keep
v6 node start -n cp2 --user --keep
v6 node start -n as  --user --keep

# 3. Verify all 5 containers are up
docker ps --filter name=vantage6 --format '{{.Names}}\t{{.Status}}'
```

Expected output:
```
vantage6-as-user      Up ...
vantage6-cp2-user     Up ...
vantage6-cp1-user     Up ...
vantage6-kds-user     Up ...
vantage6-test-user-ServerType.V6SERVER  Up ...
```

## Running the End-to-End Test

```bash
source /home/aghavamipo/venv/bin/activate
python3 /home/aghavamipo/e2e_test.py
```

Expected output:
```
=== RESULTS ===
  Iteration 1: result=10.0000
  Iteration 2: result=30.0000
  Final result: 30.0000

End-to-end test PASSED!
```

The small floating-point deviation from exact integers (e.g. `29.9999...`) is normal CKKS noise.

## Submitting Tasks Programmatically

```python
from vantage6.client import UserClient

c = UserClient('http://localhost', 5000, '/api')
c.authenticate('researcher', 'Research@123')

# KDS task (runs on KDS node, org_id=2)
task = c.task.create(
    collaboration=1,
    organizations=[2],
    name='kds-key-gen',
    image='ghcr.io/alirezaghavamipour/privacy-fl/privacy-fl-kds:main',
    description='...',
    input_={'method': 'kds_partial', 'kwargs': {'cp_public_keys': {...}}},
)

# Worker central task (also runs on KDS org node, spawns subtasks to CP1/CP2/AS)
task = c.task.create(
    collaboration=1,
    organizations=[2],
    name='fl-central',
    image='ghcr.io/alirezaghavamipour/privacy-fl/privacy-fl-worker:main',
    description='...',
    input_={'method': 'central', 'kwargs': {
        'cp_org_ids': [3, 4],
        'as_org_id': 5,
        'encrypted_cp_contexts': {...},  # from KDS result
        'as_context': '...',             # from KDS result
        'num_iterations': 2,
    }},
)
```

## Updating the Algorithm Code

1. Edit code in `privacy-fl-kds/` or `privacy-fl-worker/`
2. `git push` to main branch
3. GitHub Actions automatically rebuilds both images → pushes to `ghcr.io/.../...:main`
4. Next time a task runs, nodes pull the new image automatically (vantage6 always calls `docker pull` before running)

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Node exits immediately after start | Check `docker logs vantage6-<name>-user` — likely wrong API key |
| `CP_RSA_PRIVATE_KEY` not set error | Check `algorithm_env` in node config YAML |
| SQLite import didn't persist | Server holds the DB lock — use Python client API to create orgs/nodes instead |
| Nodes can't reach server | Verify `node_extra_hosts: {v6server: host-gateway}` in node config |
| `input` keyword error in task.create | Use `input_` (with underscore) — vantage6 v4 API |
