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

- [ ] Contract code implements 6 write methods + 5 view methods (11 total)
- [ ] Accounting invariant enforced: `released + reserved ≤ funded`
- [ ] Provider address stored natively at project creation
- [ ] Payout uses only the stored native address
- [ ] No double payout possible
- [ ] Rejected milestones remain reserved
- [ ] Direct VM tests cover all 31 specified scenarios
- [ ] All direct tests pass with pinned SDK
- [ ] Lint passes for the contract
- [ ] CI workflow exists and runs on Ubuntu/Python 3.12

## Test Command and Result
```
python -m pytest tests/direct/ -v
```
_RESULT: PENDING — to be filled after running tests_

## Lint Command and Result
```
genvm-lint contracts/milestone_vault.py
```
_RESULT: PENDING — to be filled after running lint_

## GitHub Repository
_URL: PLACEHOLDER — to be filled after push_

## Studio Contract Address
_ADDRESS: PLACEHOLDER — to be filled after deployment_

## Deployment Transaction
_HASH: PLACEHOLDER — to be filled after deployment_

## Successful Approval/Payout Transaction
_HASH: PLACEHOLDER — to be filled after running approval on-chain_

## Known Limitations
- Human buyer makes the approval decision; evidence is informational, not automatically verified
- No cancellation/refund flow; rejected and pending milestones remain reserved
- One provider per project
- No dispute resolution mechanism

## Suggested Evidence Links
- Repository: _PLACEHOLDER_
- Contract on Explorer: _PLACEHOLDER_
- Approval/payout transaction: _PLACEHOLDER_
