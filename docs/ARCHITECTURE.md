# Architecture

## Overview

MilestoneVault is a single GenLayer Intelligent Contract implementing deterministic buyer-controlled milestone escrow. The buyer creates projects, funds escrow, defines milestones, and manually approves or rejects each submitted milestone. Approval releases funds to the provider once. Rejection keeps funds reserved.

This contract does **not** use AI, LLMs, web retrieval, nondeterministic execution, or automated evaluation. All decisions are made explicitly by the buyer.

## System Components

```
┌─────────────────────────────────────────┐
│  Contract (milestone_vault.py)          │
│                                         │
│  ┌─────────────┐  ┌──────────────────┐  │
│  │ Escrow      │  │ Payment          │  │
│  │ State       │  │ System           │  │
│  │ Machine     │  │                  │  │
│  │             │  │ Native Address   │  │
│  │ Projects    │  │ Storage          │  │
│  │ Milestones  │  │                  │  │
│  │ Balance     │  │ EVM Transfer     │  │
│  └─────────────┘  └──────────────────┘  │
└─────────────────────────────────────────┘
```

## Contract Storage

All entities are stored as JSON strings in `TreeMap[str, str]`:

| Storage | Key | Value |
|---------|-----|-------|
| `projects` | `"p-1"` | JSON project data |
| `milestones` | `"m-1"` | JSON milestone data |

Provider addresses stored natively as `Address` in `TreeMap[str, Address]`:

| Storage | Key | Value |
|---------|-----|-------|
| `provider_addresses` | `"p-1"` | Native `Address` for payout |

Counters and balance use `u256`.

## State Machines

### Project State

```
CREATED → FUNDED
```

- `CREATED`: project exists, no funds deposited
- `FUNDED`: at least one funding transaction confirmed

### Milestone State

```
PENDING → SUBMITTED → APPROVED (funds released)
                    → REJECTED (funds reserved)
```

- `PENDING`: milestone created, evidence not yet submitted
- `SUBMITTED`: provider has submitted evidence URLs
- `APPROVED`: buyer approved, funds transferred to provider
- `REJECTED`: buyer rejected, funds stay reserved

## Data Flow

### Create + Fund + Approve

1. `create_project(provider, description)` → stores project as CREATED, saves native provider Address
2. `fund_project(project_id)` [payable] → transitions to FUNDED, updates balance
3. `create_milestone(project_id, description, criteria, amount)` → stores milestone as PENDING, reserves amount
4. `submit_evidence(milestone_id, urls)` → stores HTTPS URLs, transitions to SUBMITTED
5. `approve_milestone(milestone_id)` → buyer approves → transfers funds to stored provider Address
6. `reject_milestone(milestone_id, reason)` → buyer rejects → funds stay reserved

## Payment Flow

```
approve_milestone(milestone_id):
    1. Validate: caller is buyer, milestone is SUBMITTED, not yet paid
    2. Effects: update accounting BEFORE transfer
       - project.total_reserved -= amount
       - project.total_released += amount
       - contract.balance -= amount
       - milestone.paid = true
       - milestone.status = APPROVED
    3. Interaction: transfer to stored native provider address
       provider_addr = self.provider_addresses[project_id]
       _EoaRecipient(provider_addr).emit_transfer(value=u256(amount))
```

The provider address is stored natively as `Address` in `provider_addresses: TreeMap[str, Address]`. No string conversion or caller-supplied address is used for payout.

## Over-Allocation Prevention

When creating a milestone, the contract checks:

```
milestone.amount ≤ project.total_funded - project.total_released - project.total_reserved
```

This prevents the buyer from creating milestones that exceed the available escrow. Rejected and pending milestones remain reserved and cannot be reused. Approved (released) funds cannot be re-allocated.

## Accounting Invariant

```
total_released + total_reserved ≤ total_funded
```

This invariant holds at all times:
- Creating a milestone increases `total_reserved`
- Approving a milestone decreases `total_reserved` and increases `total_released` (net zero change to `released + reserved`)
- Rejecting a milestone does not change accounting (funds stay reserved)
- No path causes `total_released + total_reserved` to exceed `total_funded`
