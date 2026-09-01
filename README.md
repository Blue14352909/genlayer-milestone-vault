# MilestoneVault

Deterministic buyer-controlled milestone escrow on GenLayer.

## Problem

Escrow systems need safe allocation: buyers must not be able to over-commit funds across multiple milestones, approved payments must not reopen spent escrow, and the same milestone must never be paid twice. Most on-chain escrow either trusts a single party or relies on complex oracle mechanisms.

## Solution

MilestoneVault lets a buyer escrow GEN for a provider's work. The buyer creates specific milestones with fixed payout amounts. The provider submits evidence URLs. Only the buyer manually approves or rejects each milestone. Approval releases that milestone's escrowed funds to the provider once. Rejection keeps the funds reserved in the vault.

This is a deterministic escrow contract. It does **not** use AI, LLMs, web retrieval, nondeterministic execution, or automated evaluation. All approval decisions are made explicitly by the human buyer.

## User Flow

1. **Buyer** creates a project and specifies the provider's wallet address
2. **Buyer** deposits GEN into the escrow
3. **Buyer** reserves milestones with descriptions, acceptance criteria, and fixed amounts
4. **Provider** submits 1–5 HTTPS evidence URLs (GitHub repos, deployments, docs)
5. **Buyer** reviews the evidence and approves or rejects each milestone
6. **Approval** transfers the milestone amount to the stored provider address
7. **Rejection** keeps funds reserved; buyer provides a reason

## Security Properties

- **Reserved escrow**: milestone amounts are reserved at creation, preventing over-allocation
- **Buyer-only approval**: only the buyer can approve or reject milestones
- **Provider cannot self-pay**: payout uses the address stored at project creation, not any caller-supplied address
- **No double payout**: each milestone can be paid exactly once
- **Rejected milestones stay reserved**: funds cannot be silently reused for new milestones
- **No arbitrary withdrawal**: no admin backdoor or hidden withdrawal function
- **Checks-effects-interactions**: accounting is updated before the GEN transfer

## Accounting Invariant

```
total_released + total_reserved ≤ total_funded
```

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
python -m pytest tests/direct/ -v
```

**Note:** On Windows, the GenLayer test framework may be blocked by a temporary-file permission issue (WinError 32). This is a known platform limitation, not a contract defect. CI runs on Ubuntu/Python 3.12.

## Deployment

**Contract Address:** [`0x5cb455CDEC12CF788BA3D780bda96598B9D8e10c`](https://explorer-studio.genlayer.com/address/0x5cb455CDEC12CF788BA3D780bda96598B9D8e10c)

### On-Chain Evidence

| Case | Transaction | Explorer |
|---|---|---|
| Deployment | `0xfc2f79...` | [View](https://explorer-studio.genlayer.com/tx/0xfc2f79c066d7d75dc6a3071967e836ef76fe60f5d14e5f4993779ad61142fd28) |
| **APPROVED** (payout) | `0xae3c72...` | [View](https://explorer-studio.genlayer.com/tx/0xae3c729fcf7e53e3fbe8fef0936fa3a5c5841e2d66c0e022dee9a69fc4119d93) |

### How to deploy

1. Open [GenLayer Studio](https://studio.genlayer.com/)
2. Import `contracts/milestone_vault.py`
3. Deploy
4. Run the full lifecycle: create project → fund → create milestone → submit evidence → approve

## Security

Key invariants:
- No double payout (paid flag + state machine)
- Solvency: released + reserved ≤ funded
- HTTPS evidence URL input validation
- Native Address storage for payout (no caller-supplied addresses)
- Authorization enforced: only buyer funds/creates/approves/rejects, only provider submits evidence

## Known Limitations

- Human buyer makes the approval decision; evidence is informational, not automatically verified
- No cancellation/refund flow; rejected and pending milestones remain reserved
- One provider per project
- Milestone listing scans all milestones (efficient for small scale)
- Acceptance criteria truncated to 2,000 characters
