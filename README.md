# MilestoneVault

Trustless milestone escrow with GenLayer consensus-based adjudication.

## Problem

Smart contracts can verify that money was deposited, but they cannot natively determine whether a website, software feature, document, API, or other real-world deliverable actually satisfies human-written requirements. Escrow systems traditionally rely on either party clicking "approve" — which reintroduces the trust problem that blockchain was meant to solve.

## Solution

MilestoneVault uses GenLayer Intelligent Contracts to independently evaluate whether submitted evidence satisfies acceptance criteria. A buyer locks funds, a provider submits evidence (GitHub repository, live deployment, documentation), and GenLayer validators fetch that evidence, extract structured facts, and reach consensus on whether the milestone criteria are met.

- **APPROVED** → funds released to provider
- **REJECTED** → funds remain locked, dispute available
- **INCONCLUSIVE** → funds remain locked, no payout

GenLayer is essential because the evaluation requires:
1. Fetching external web content (nondeterministic)
2. Semantic judgment against natural-language criteria (LLM)
3. Independent validator verification (consensus)

Without GenLayer, this application cannot function.

## Architecture

```
Frontend (HTML/JS)
    ↓ wallet + contract calls
Intelligent Contract (milestone_vault.py)
    ↓
Evidence retrieval (gl.nondet.web.render)
    ↓
Structured fact extraction (gl.nondet.exec_prompt)
    ↓
Validator re-evaluation (run_nondet_unsafe)
    ↓
Consensus (verdict + criterion status comparison)
    ↓
Deterministic settlement (escrow release or lock)
```

## User Flow

1. **Buyer** creates a project and defines milestones with acceptance criteria
2. **Buyer** funds the escrow (GEN deposited into contract)
3. **Provider** submits evidence URLs (GitHub, deployment, docs)
4. **Anyone** triggers evaluation → GenLayer consensus runs
5. **Consensus** produces structured verdict with per-criterion results
6. **Settlement**: APPROVED releases funds, others keep locked
7. **Dispute**: if REJECTED, provider can submit additional evidence for re-evaluation

## Installation

```bash
git clone https://github.com/Blue14352909/genlayer-milestone-vault.git
cd genlayer-milestone-vault
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

## Linting

```bash
genvm-lint contracts/milestone_vault.py
```

## Testing

```bash
cd tests/direct
python -m pytest -v
```

**Note:** On Windows, the GenLayer test framework may be blocked by a temporary-file permission issue (WinError 32). This is a known platform limitation, not a contract defect. Tests have been verified to pass on Linux/macOS environments.

## Deployment

**Contract Address:** [`0x39066b8BB10d7beCDb776b64e25183A8EBC69acA`](https://explorer-studio.genlayer.com/address/0x39066b8BB10d7beCDb776b64e25183A8EBC69acA)

**Frontend:** [Live App](https://blue14352909.github.io/genlayer-milestone-vault/)

### On-Chain Evidence

| Case | Transaction | Explorer |
|---|---|---|
| Deployment | `0xe9eb54...` | [View](https://explorer-studio.genlayer.com/tx/0xe9eb54343e8df435ea27cd34a3b8875fef352fc6cfd0737418b035a7c35ddcc0) |
| **APPROVED** | `0x291bc4...` | [View](https://explorer-studio.genlayer.com/tx/0x291bc451f9b568afc915bc7f96dec1af531efcda1a139f5c0525be355fd9d841) |
| **REJECTED** | `0x5b91c9...` | [View](https://explorer-studio.genlayer.com/tx/0x5b91c9a5c1c4981bf0bb611bb1ceb3a0e13af3bace68e6fe5f20a438dd9f7a77) |
| **INCONCLUSIVE** | `0x0871ef...` | [View](https://explorer-studio.genlayer.com/tx/0x0871efd29c56d18eae97dc378d524ba5cf0020ae5836ab94d152e29331737d16) |

### How to deploy yourself

1. Open [GenLayer Studio](https://studio.genlayer.com/)
2. Import `contracts/milestone_vault.py`
3. Deploy
4. Update `CONTRACT_ADDRESS` in `frontend/app.js`
5. Open `frontend/index.html` in a browser

## Frontend

The frontend provides:
- Wallet connection (MetaMask)
- Project creation with full transaction lifecycle
- Escrow funding
- Milestone creation with acceptance criteria
- Evidence submission (multiple HTTPS URLs)
- Evaluation trigger with live consensus status
- Per-criterion result display
- Dispute filing and resolution

## Security

See [SECURITY.md](docs/SECURITY.md) for the full threat model.

Key invariants:
- Empty criteria → INCONCLUSIVE → never APPROVED
- Fetch failure → INCONCLUSIVE → never APPROVED
- Malformed evaluator response → INCONCLUSIVE → never APPROVED
- Validator disagreement → INCONCLUSIVE → never APPROVED
- No double payout (paid flag + state machine)
- Solvency: released + locked ≤ deposited
- HTTPS-only evidence URLs (SSRF protection)
- Untrusted evidence isolation (prompt injection defense)

## License

MIT
