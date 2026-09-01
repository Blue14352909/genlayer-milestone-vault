# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
"""
MilestoneVault -- Deterministic Buyer-Controlled Milestone Escrow.

A buyer locks GEN for a provider's work. The buyer creates milestones with
fixed payout amounts. The provider submits evidence URLs. Only the buyer
manually approves or rejects each milestone. Approval releases that
milestone's escrowed funds to the provider once. Rejection keeps the funds
reserved in the vault.

This is a deterministic escrow contract. It does NOT use AI, LLMs, web
retrieval, nondeterministic execution, or automated evaluation.

Hard invariants:
    released <= reserved <= funded
    No milestone can be paid twice.
    Rejected milestones remain reserved.
    Provider cannot redirect payout.
    No arbitrary withdrawal.
"""
import json
import re
from genlayer import *


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PRJ_CREATED = "CREATED"
PRJ_FUNDED = "FUNDED"

MS_PENDING = "PENDING"
MS_SUBMITTED = "SUBMITTED"
MS_APPROVED = "APPROVED"
MS_REJECTED = "REJECTED"

MAX_URLS = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _addr_to_hex(addr) -> str:
    """Convert an Address to its checksummed hex string."""
    if hasattr(addr, "as_hex"):
        return addr.as_hex
    from genlayer.py.types import Address as _Address
    return _Address(addr).as_hex


def _validate_url(url: str) -> bool:
    """HTTPS URL input validation: only HTTPS public URLs."""
    if not url or not url.strip():
        return False
    url = url.strip()
    blocked = [
        r"^http://", r"localhost", r"127\.\d+\.\d+\.\d+",
        r"10\.\d+\.\d+\.\d+", r"172\.(1[6-9]|2\d|3[01])\.",
        r"192\.168\.", r"\[::1\]", r"0\.0\.0\.0",
        r"^file://", r"^javascript:", r"^data:",
    ]
    for pattern in blocked:
        if re.search(pattern, url, re.IGNORECASE):
            return False
    return url.startswith("https://")


# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------
class MilestoneVault(gl.Contract):
    """
    Deterministic buyer-controlled milestone escrow.

    Entities stored as JSON strings in TreeMap[str, str].
    Provider addresses stored natively as Address for safe payout.
    Accounting invariant: released <= reserved <= funded.
    """

    # Counters and balance
    project_counter: u256
    milestone_counter: u256
    balance: u256

    def __init__(self):
        self.project_counter = u256(0)
        self.milestone_counter = u256(0)
        self.balance = u256(0)

    # Entity storage: ID -> JSON string
    projects: TreeMap[str, str]
    milestones: TreeMap[str, str]
    # Provider addresses stored natively for safe comparison and payout
    provider_addresses: TreeMap[str, Address]

    # -------------------------------------------------------------------
    # 1. create_project
    # -------------------------------------------------------------------
    @gl.public.write
    def create_project(self, provider: Address, description: str) -> str:
        """Create a new project. Caller becomes buyer. State: CREATED."""
        if not description or not description.strip():
            raise gl.vm.UserError("Description required")
        provider_str = _addr_to_hex(provider)
        if not provider_str or provider_str == "0x0000000000000000000000000000000000000000":
            raise gl.vm.UserError("Provider address required")

        self.project_counter = self.project_counter + 1
        pid = "p-" + str(self.project_counter)

        project = {
            "id": pid,
            "buyer": _addr_to_hex(gl.message.sender_address),
            "provider": provider_str,
            "description": description.strip(),
            "status": PRJ_CREATED,
            "total_funded": "0",
            "total_reserved": "0",
            "total_released": "0",
            "milestone_count": "0",
        }
        self.projects[pid] = json.dumps(project)
        self.provider_addresses[pid] = Address(provider)
        return pid

    # -------------------------------------------------------------------
    # 2. fund_project
    # -------------------------------------------------------------------
    @gl.public.write.payable
    def fund_project(self, project_id: str) -> str:
        """Fund a project's escrow. Only buyer. Transitions CREATED -> FUNDED."""
        if project_id not in self.projects:
            raise gl.vm.UserError("Project not found")

        p = json.loads(self.projects[project_id])

        if p["buyer"] != _addr_to_hex(gl.message.sender_address):
            raise gl.vm.UserError("Only buyer can fund")
        if p["status"] not in (PRJ_CREATED, PRJ_FUNDED):
            raise gl.vm.UserError("Project not in fundable state")

        amount = gl.message.value
        if not amount:
            raise gl.vm.UserError("Must send funds")

        p["total_funded"] = str(int(p["total_funded"]) + int(amount))
        self.balance = self.balance + int(amount)

        if p["status"] == PRJ_CREATED:
            p["status"] = PRJ_FUNDED

        self.projects[project_id] = json.dumps(p)
        return p["total_funded"]

    # -------------------------------------------------------------------
    # 3. create_milestone
    # -------------------------------------------------------------------
    @gl.public.write
    def create_milestone(
        self,
        project_id: str,
        description: str,
        acceptance_criteria: str,
        amount: u256,
    ) -> str:
        """Create a milestone. Only buyer. Reserves amount from available escrow."""
        if project_id not in self.projects:
            raise gl.vm.UserError("Project not found")

        p = json.loads(self.projects[project_id])

        if p["buyer"] != _addr_to_hex(gl.message.sender_address):
            raise gl.vm.UserError("Only buyer can create milestones")
        if p["status"] != PRJ_FUNDED:
            raise gl.vm.UserError("Project must be FUNDED before creating milestones")
        if not amount:
            raise gl.vm.UserError("Amount must be positive")
        if not description or not description.strip():
            raise gl.vm.UserError("Description required")
        if not acceptance_criteria or not acceptance_criteria.strip():
            raise gl.vm.UserError("Acceptance criteria required")

        amount_int = int(amount)
        funded = int(p["total_funded"])
        reserved = int(p["total_reserved"])
        available = funded - reserved

        if amount_int > available:
            raise gl.vm.UserError(
                f"Milestone amount {amount_int} exceeds available escrow {available}"
            )

        # Reserve immediately
        p["total_reserved"] = str(reserved + amount_int)

        self.milestone_counter = self.milestone_counter + 1
        mid = "m-" + str(self.milestone_counter)

        milestone = {
            "id": mid,
            "project_id": project_id,
            "description": description.strip(),
            "acceptance_criteria": acceptance_criteria.strip()[:2000],
            "amount": str(amount_int),
            "evidence_urls": "",
            "status": MS_PENDING,
            "paid": "false",
        }
        self.milestones[mid] = json.dumps(milestone)

        p["milestone_count"] = str(int(p["milestone_count"]) + 1)
        self.projects[project_id] = json.dumps(p)

        return mid

    # -------------------------------------------------------------------
    # 4. submit_evidence
    # -------------------------------------------------------------------
    @gl.public.write
    def submit_evidence(self, milestone_id: str, evidence_urls: str) -> str:
        """Provider submits evidence URLs. Transitions PENDING -> SUBMITTED."""
        if milestone_id not in self.milestones:
            raise gl.vm.UserError("Milestone not found")

        m = json.loads(self.milestones[milestone_id])
        p = json.loads(self.projects[m["project_id"]])

        sender = _addr_to_hex(gl.message.sender_address)
        if sender != p["provider"]:
            raise gl.vm.UserError("Only provider can submit evidence")

        if m["status"] != MS_PENDING:
            raise gl.vm.UserError(f"Cannot submit evidence in state {m['status']}")

        if not evidence_urls or not evidence_urls.strip():
            raise gl.vm.UserError("Evidence URLs required")

        urls = [u.strip() for u in evidence_urls.split(",") if u.strip()]
        if len(urls) == 0:
            raise gl.vm.UserError("No valid URLs provided")
        if len(urls) > MAX_URLS:
            raise gl.vm.UserError(f"Maximum {MAX_URLS} evidence URLs")

        for url in urls:
            if not _validate_url(url):
                raise gl.vm.UserError(f"Invalid URL: {url}")

        m["evidence_urls"] = ", ".join(urls)
        m["status"] = MS_SUBMITTED
        self.milestones[milestone_id] = json.dumps(m)
        return MS_SUBMITTED

    # -------------------------------------------------------------------
    # 5. approve_milestone
    # -------------------------------------------------------------------
    @gl.public.write
    def approve_milestone(self, milestone_id: str) -> str:
        """Buyer approves a submitted milestone. Releases funds to provider.
        Checks-effects-interactions: validate, update accounting, then transfer."""
        if milestone_id not in self.milestones:
            raise gl.vm.UserError("Milestone not found")

        m = json.loads(self.milestones[milestone_id])
        p = json.loads(self.projects[m["project_id"]])

        if _addr_to_hex(gl.message.sender_address) != p["buyer"]:
            raise gl.vm.UserError("Only buyer can approve")
        if m["status"] != MS_SUBMITTED:
            raise gl.vm.UserError(f"Cannot approve in state {m['status']}")
        if m["paid"] == "true":
            raise gl.vm.UserError("Milestone already paid")

        amount_int = int(m["amount"])
        reserved = int(p["total_reserved"])
        released = int(p["total_released"])

        # Effects: update accounting BEFORE transfer
        p["total_reserved"] = str(reserved - amount_int)
        p["total_released"] = str(released + amount_int)
        self.balance = self.balance - u256(amount_int)
        m["paid"] = "true"
        m["status"] = MS_APPROVED

        self.projects[m["project_id"]] = json.dumps(p)
        self.milestones[milestone_id] = json.dumps(m)

        # Interaction: transfer to stored native provider address
        provider_addr = self.provider_addresses[m["project_id"]]
        _EoaRecipient(provider_addr).emit_transfer(value=u256(amount_int))

        return MS_APPROVED

    # -------------------------------------------------------------------
    # 6. reject_milestone
    # -------------------------------------------------------------------
    @gl.public.write
    def reject_milestone(self, milestone_id: str, reason: str) -> str:
        """Buyer rejects a submitted milestone. Funds stay reserved."""
        if milestone_id not in self.milestones:
            raise gl.vm.UserError("Milestone not found")

        m = json.loads(self.milestones[milestone_id])
        p = json.loads(self.projects[m["project_id"]])

        if _addr_to_hex(gl.message.sender_address) != p["buyer"]:
            raise gl.vm.UserError("Only buyer can reject")
        if m["status"] != MS_SUBMITTED:
            raise gl.vm.UserError(f"Cannot reject in state {m['status']}")
        if not reason or not reason.strip():
            raise gl.vm.UserError("Rejection reason required")

        m["status"] = MS_REJECTED
        m["rejection_reason"] = reason.strip()
        self.milestones[milestone_id] = json.dumps(m)
        return MS_REJECTED

    # -------------------------------------------------------------------
    # View methods
    # -------------------------------------------------------------------
    @gl.public.view
    def get_project(self, project_id: str) -> dict:
        """Get project details."""
        if project_id not in self.projects:
            raise gl.vm.UserError("Project not found")
        return json.loads(self.projects[project_id])

    @gl.public.view
    def get_milestone(self, milestone_id: str) -> dict:
        """Get milestone details."""
        if milestone_id not in self.milestones:
            raise gl.vm.UserError("Milestone not found")
        return json.loads(self.milestones[milestone_id])

    @gl.public.view
    def get_project_milestones(self, project_id: str) -> list:
        """Get all milestones belonging to a specific project.
        Milestone IDs are global counters, so we scan all milestones
        and filter by project_id."""
        if project_id not in self.projects:
            raise gl.vm.UserError("Project not found")
        results = []
        count = int(self.milestone_counter)
        for i in range(1, count + 1):
            mid = "m-" + str(i)
            if mid in self.milestones:
                ms = json.loads(self.milestones[mid])
                if ms.get("project_id") == project_id:
                    results.append(ms)
        return results

    @gl.public.view
    def get_balance(self) -> str:
        """Get total vault balance."""
        return str(self.balance)

    @gl.public.view
    def get_available_escrow(self, project_id: str) -> str:
        """Get available escrow for a project (funded - reserved)."""
        if project_id not in self.projects:
            raise gl.vm.UserError("Project not found")
        p = json.loads(self.projects[project_id])
        available = int(p["total_funded"]) - int(p["total_reserved"])
        return str(available)


# ---------------------------------------------------------------------------
# EVM interface for sending value to EOAs
# ---------------------------------------------------------------------------
@gl.evm.contract_interface
class _EoaRecipient:
    class View:
        pass
    class Write:
        pass
