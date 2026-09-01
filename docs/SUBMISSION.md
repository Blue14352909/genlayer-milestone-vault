# MilestoneVault — Submission

## Project Name
MilestoneVault

## One-liner
Deterministic buyer-controlled milestone escrow: buyer locks GEN, provider submits evidence, buyer approves or rejects, approval pays provider once.

## Short Description
MilestoneVault lets a buyer escrow GEN for a provider's work. The buyer creates milestones with fixed amounts. The provider submits HTTPS evidence URLs. Only the buyer manually approves or rejects. Approval releases escrowed funds to the provider exactly once. Rejection keeps funds reserved. The contract enforces: total released + total reserved ≤ total funded.

## User Path / Demo Flow
1. Buyer creates a project (`create_project`) specifying the provider's wallet address
2. Buyer deposits GEN (`fund_project`)
3. Buyer reserves a milestone with description, acceptance criteria, and amount (`create_milestone`) — amount is immediately reserved from available escrow
4. Provider submits 1–5 HTTPS evidence URLs (`submit_evidence`)
5. Buyer reviews the evidence and approves (`approve_milestone`) or rejects (`reject_milestone`)
6. Approval transfers the milestone amount to the stored provider address and marks the milestone as paid
7. Rejection keeps funds reserved; buyer can reject with a reason

## Proof Checklist

- [x] Contract code implements 6 write methods + 5 view methods (11 total)
- [x] Accounting invariant enforced: `released + reserved ≤ funded`
- [x] Provider address stored natively at project creation
- [x] Payout uses only the stored native address
- [x] No double payout possible
- [x] Rejected milestones remain reserved
- [x] Direct VM tests cover all 33 specified scenarios
- [x] All direct tests pass with pinned SDK
- [x] Lint passes for the contract
- [x] CI workflow exists and runs on Ubuntu/Python 3.12
- [x] On-chain lifecycle: create → fund → milestone → evidence → approve → payout

## Test Command and Result
```
python -m pytest tests/direct/ -v
```
Result: **33 passed**

## Lint Command and Result
```
genvm-lint contracts/milestone_vault.py
```
Result: **Lint passed (3 checks)**

## GitHub Repository
https://github.com/Blue14352909/genlayer-milestone-vault

## Final Commit
https://github.com/Blue14352909/genlayer-milestone-vault/commit/5a1643a

## Studio Contract Address
[`0x5cb455CDEC12CF788BA3D780bda96598B9D8e10c`](https://explorer-studio.genlayer.com/address/0x5cb455CDEC12CF788BA3D780bda96598B9D8e10c)

## Deployment Transaction
[`0xfc2f79c066d7d75dc6a3071967e836ef76fe60f5d14e5f4993779ad61142fd28`](https://explorer-studio.genlayer.com/tx/0xfc2f79c066d7d75dc6a3071967e836ef76fe60f5d14e5f4993779ad61142fd28)

## Successful Approval/Payout Transaction
[`0xae3c729fcf7e53e3fbe8fef0936fa3a5c5841e2d66c0e022dee9a69fc4119d93`](https://explorer-studio.genlayer.com/tx/0xae3c729fcf7e53e3fbe8fef0936fa3a5c5841e2d66c0e022dee9a69fc4119d93)

## Known Limitations
- Human buyer makes the approval decision; evidence is informational, not automatically verified
- No cancellation/refund flow; rejected and pending milestones remain reserved
- One provider per project
- No dispute resolution mechanism

## Evidence Links
- Repository: https://github.com/Blue14352909/genlayer-milestone-vault
- Contract on Explorer: https://explorer-studio.genlayer.com/address/0x5cb455CDEC12CF788BA3D780bda96598B9D8e10c
- Deployment: https://explorer-studio.genlayer.com/tx/0xfc2f79c066d7d75dc6a3071967e836ef76fe60f5d14e5f4993779ad61142fd28
- Approval/payout: https://explorer-studio.genlayer.com/tx/0xae3c729fcf7e53e3fbe8fef0936fa3a5c5841e2d66c0e022dee9a69fc4119d93
