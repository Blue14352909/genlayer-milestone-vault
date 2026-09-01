"""Tests for MilestoneVault deterministic escrow contract.

Account roles:
  direct_alice  = buyer (creates project, funds, creates milestones, approves/rejects)
  direct_bob    = provider (submits evidence)
  direct_charlie = attacker (should be blocked from all restricted actions)
"""
import pytest
from tests.direct.conftest import to_hex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _create_project(contract, vm, buyer, provider):
    """Create a project as buyer."""
    vm.sender = buyer
    return contract.create_project(provider, "Test project")


def _fund_project(contract, vm, buyer, project_id, amount_wei):
    """Fund a project as buyer."""
    vm.sender = buyer
    vm.value = amount_wei
    contract.fund_project(project_id)
    vm.value = 0


def _create_milestone(contract, vm, buyer, project_id, amount_wei,
                      criteria="Criterion 1"):
    """Create a milestone as buyer."""
    vm.sender = buyer
    return contract.create_milestone(project_id, "Milestone desc", criteria,
                                     amount_wei)


def _submit_evidence(contract, vm, sender, milestone_id):
    """Submit evidence as sender."""
    vm.sender = sender
    contract.submit_evidence(milestone_id, "https://example.com/proof")


def _approve(contract, vm, buyer, milestone_id):
    """Approve milestone as buyer."""
    vm.sender = buyer
    return contract.approve_milestone(milestone_id)


def _reject(contract, vm, buyer, milestone_id, reason):
    """Reject milestone as buyer."""
    vm.sender = buyer
    return contract.reject_milestone(milestone_id, reason)


def _setup_project_with_milestone(contract, vm, alice, bob, amount=100,
                                  ms_amount=50):
    """Create project (alice=buyer, bob=provider), fund, create milestone.
    Returns (project_id, milestone_id)."""
    pid = _create_project(contract, vm, alice, bob)
    _fund_project(contract, vm, alice, pid, amount)
    mid = _create_milestone(contract, vm, alice, pid, ms_amount)
    return pid, mid


# ===========================================================================
# 1. PROJECT CREATION
# ===========================================================================

def test_create_project_stores_correct_data(direct_deploy, direct_vm,
                                            direct_alice, direct_bob):
    """Project stores buyer, provider, status=CREATED correctly."""
    contract = direct_deploy("contracts/milestone_vault.py")
    direct_vm.sender = direct_alice

    pid = contract.create_project(direct_bob, "Build website")
    p = contract.get_project(pid)

    assert p["buyer"] == to_hex(direct_alice)
    assert p["provider"] == to_hex(direct_bob)
    assert p["status"] == "CREATED"
    assert p["description"] == "Build website"
    assert p["total_funded"] == "0"
    assert p["total_reserved"] == "0"
    assert p["total_released"] == "0"
    assert p["milestone_count"] == "0"
    assert pid == "p-1"


def test_create_project_empty_description(direct_deploy, direct_vm,
                                          direct_alice, direct_bob):
    """Empty/whitespace description raises error."""
    contract = direct_deploy("contracts/milestone_vault.py")
    direct_vm.sender = direct_alice

    with pytest.raises(Exception, match="Description required"):
        contract.create_project(direct_bob, "")

    with pytest.raises(Exception, match="Description required"):
        contract.create_project(direct_bob, "   ")


def test_create_project_zero_address(direct_deploy, direct_vm, direct_alice):
    """Zero address provider is rejected."""
    contract = direct_deploy("contracts/milestone_vault.py")
    direct_vm.sender = direct_alice

    with pytest.raises(Exception, match="Provider address required"):
        contract.create_project(
            "0x0000000000000000000000000000000000000000",
            "Test project")


# ===========================================================================
# 2. FUNDING
# ===========================================================================

def test_fund_project_only_buyer(direct_deploy, direct_vm, direct_alice,
                                 direct_bob, direct_charlie):
    """Non-buyer cannot fund the project."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)

    # Bob (provider, not buyer) tries to fund
    direct_vm.sender = direct_bob
    direct_vm.value = 50
    with pytest.raises(Exception, match="Only buyer can fund"):
        contract.fund_project(pid)
    direct_vm.value = 0

    # Charlie (attacker) tries to fund
    direct_vm.sender = direct_charlie
    direct_vm.value = 50
    with pytest.raises(Exception, match="Only buyer can fund"):
        contract.fund_project(pid)
    direct_vm.value = 0


def test_fund_project_zero_value(direct_deploy, direct_vm, direct_alice,
                                 direct_bob):
    """Zero GEN funding is rejected."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    direct_vm.value = 0
    with pytest.raises(Exception):
        contract.fund_project(pid)


def test_fund_project_transitions_to_funded(direct_deploy, direct_vm,
                                            direct_alice, direct_bob):
    """Funding transitions CREATED -> FUNDED and updates total_funded."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)

    _fund_project(contract, direct_vm, direct_alice, pid, 100)
    p = contract.get_project(pid)

    assert p["status"] == "FUNDED"
    assert p["total_funded"] == "100"
    assert contract.get_balance() == "100"


# ===========================================================================
# 3. MILESTONE CREATION
# ===========================================================================

def test_create_milestone_only_buyer(direct_deploy, direct_vm, direct_alice,
                                     direct_bob, direct_charlie):
    """Non-buyer cannot create milestones."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    # Bob (provider, not buyer)
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Only buyer can create milestones"):
        contract.create_milestone(pid, "Desc", "Criteria", 50)

    # Charlie (attacker)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="Only buyer can create milestones"):
        contract.create_milestone(pid, "Desc", "Criteria", 50)


def test_create_milestone_zero_amount(direct_deploy, direct_vm, direct_alice,
                                      direct_bob):
    """Zero-amount milestone is rejected."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Amount must be positive"):
        contract.create_milestone(pid, "Desc", "Criteria", 0)


def test_create_milestone_empty_criteria(direct_deploy, direct_vm,
                                         direct_alice, direct_bob):
    """Empty criteria is rejected."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Acceptance criteria required"):
        contract.create_milestone(pid, "Desc", "", 50)

    with pytest.raises(Exception, match="Acceptance criteria required"):
        contract.create_milestone(pid, "Desc", "   ", 50)


def test_over_allocation_blocked(direct_deploy, direct_vm, direct_alice,
                                direct_bob):
    """Cannot create milestone exceeding available escrow."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    _create_milestone(contract, direct_vm, direct_alice, pid, 60)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="exceeds available escrow"):
        contract.create_milestone(pid, "Desc2", "Criteria2", 60)

    p = contract.get_project(pid)
    assert p["total_reserved"] == "60"
    assert p["milestone_count"] == "1"


def test_exact_allocation_allowed(direct_deploy, direct_vm, direct_alice,
                                  direct_bob):
    """Can create milestones that exactly exhaust available escrow."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    mid1 = _create_milestone(contract, direct_vm, direct_alice, pid, 60)
    mid2 = _create_milestone(contract, direct_vm, direct_alice, pid, 40)

    assert mid1 == "m-1"
    assert mid2 == "m-2"

    p = contract.get_project(pid)
    assert p["total_reserved"] == "100"
    assert p["milestone_count"] == "2"
    assert contract.get_available_escrow(pid) == "0"


# ===========================================================================
# 4. EVIDENCE SUBMISSION
# ===========================================================================

def test_submit_evidence_only_provider(direct_deploy, direct_vm, direct_alice,
                                       direct_bob, direct_charlie):
    """Non-provider cannot submit evidence."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)

    # Alice (buyer, not provider)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Only provider can submit evidence"):
        contract.submit_evidence(mid, "https://example.com/proof")

    # Charlie (attacker)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="Only provider can submit evidence"):
        contract.submit_evidence(mid, "https://example.com/proof")


def test_submit_evidence_empty(direct_deploy, direct_vm, direct_alice,
                               direct_bob):
    """Empty evidence URL string is rejected."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)

    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Evidence URLs required"):
        contract.submit_evidence(mid, "")

    with pytest.raises(Exception, match="Evidence URLs required"):
        contract.submit_evidence(mid, "   ")


def test_submit_evidence_http_rejected(direct_deploy, direct_vm, direct_alice,
                                       direct_bob):
    """HTTP and unsafe URLs are rejected."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)

    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Invalid URL"):
        contract.submit_evidence(mid, "http://example.com/proof")

    with pytest.raises(Exception, match="Invalid URL"):
        contract.submit_evidence(mid, "file:///etc/passwd")

    with pytest.raises(Exception, match="Invalid URL"):
        contract.submit_evidence(mid, "https://localhost/proof")


def test_submit_evidence_max_urls(direct_deploy, direct_vm, direct_alice,
                                  direct_bob):
    """More than 5 URLs are rejected."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)

    urls = ",".join([f"https://example.com/{i}" for i in range(6)])
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Maximum 5"):
        contract.submit_evidence(mid, urls)


def test_submit_evidence_transitions_state(direct_deploy, direct_vm,
                                           direct_alice, direct_bob):
    """Evidence submission transitions PENDING -> SUBMITTED."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)

    _submit_evidence(contract, direct_vm, direct_bob, mid)

    m = contract.get_milestone(mid)
    assert m["status"] == "SUBMITTED"
    assert m["evidence_urls"] == "https://example.com/proof"


# ===========================================================================
# 5. APPROVAL
# ===========================================================================

def test_approve_only_buyer(direct_deploy, direct_vm, direct_alice, direct_bob,
                            direct_charlie):
    """Non-buyer cannot approve milestone."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)
    _submit_evidence(contract, direct_vm, direct_bob, mid)

    # Bob (provider, not buyer)
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Only buyer can approve"):
        contract.approve_milestone(mid)

    # Charlie (attacker)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="Only buyer can approve"):
        contract.approve_milestone(mid)


def test_approve_before_evidence_rejected(direct_deploy, direct_vm,
                                          direct_alice, direct_bob):
    """Cannot approve a PENDING milestone (evidence not submitted)."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Cannot approve in state PENDING"):
        _approve(contract, direct_vm, direct_alice, mid)


def test_approve_transfers_exact_amount(direct_deploy, direct_vm,
                                        direct_alice, direct_bob):
    """Approval transfers exactly the milestone amount to provider."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob,
                                             ms_amount=50)
    _submit_evidence(contract, direct_vm, direct_bob, mid)

    result = _approve(contract, direct_vm, direct_alice, mid)

    assert result == "APPROVED"

    m = contract.get_milestone(mid)
    assert m["status"] == "APPROVED"
    assert m["paid"] == "true"

    p = contract.get_project(pid)
    assert p["total_released"] == "50"
    assert p["total_reserved"] == "0"
    assert contract.get_balance() == "50"


def test_double_release_prevented(direct_deploy, direct_vm, direct_alice,
                                  direct_bob):
    """Cannot approve an already-approved milestone."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob,
                                             ms_amount=50)
    _submit_evidence(contract, direct_vm, direct_bob, mid)

    _approve(contract, direct_vm, direct_alice, mid)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Cannot approve in state APPROVED"):
        _approve(contract, direct_vm, direct_alice, mid)

    p = contract.get_project(pid)
    assert p["total_released"] == "50"


# ===========================================================================
# 6. REJECTION
# ===========================================================================

def test_reject_only_buyer(direct_deploy, direct_vm, direct_alice, direct_bob,
                           direct_charlie):
    """Non-buyer cannot reject milestone."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)
    _submit_evidence(contract, direct_vm, direct_bob, mid)

    # Bob (provider, not buyer)
    direct_vm.sender = direct_bob
    with pytest.raises(Exception, match="Only buyer can reject"):
        contract.reject_milestone(mid, "Bad work")

    # Charlie (attacker)
    direct_vm.sender = direct_charlie
    with pytest.raises(Exception, match="Only buyer can reject"):
        contract.reject_milestone(mid, "Bad work")


def test_rejected_milestone_no_payout(direct_deploy, direct_vm, direct_alice,
                                      direct_bob):
    """Rejected milestone does not release funds."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob,
                                             ms_amount=50)
    _submit_evidence(contract, direct_vm, direct_bob, mid)

    result = _reject(contract, direct_vm, direct_alice, mid, "Not satisfied")
    assert result == "REJECTED"

    m = contract.get_milestone(mid)
    assert m["status"] == "REJECTED"
    assert m["paid"] == "false"

    p = contract.get_project(pid)
    assert p["total_released"] == "0"
    assert contract.get_balance() == "100"


def test_reject_milestone_empty_reason(direct_deploy, direct_vm, direct_alice,
                                       direct_bob):
    """Rejecting without a reason is rejected."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob)
    _submit_evidence(contract, direct_vm, direct_bob, mid)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="Rejection reason required"):
        contract.reject_milestone(mid, "")

    with pytest.raises(Exception, match="Rejection reason required"):
        contract.reject_milestone(mid, "   ")


# ===========================================================================
# 7. ACCOUNTING
# ===========================================================================

def test_approval_updates_accounting(direct_deploy, direct_vm, direct_alice,
                                     direct_bob):
    """Approval correctly updates all accounting fields."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    mid1 = _create_milestone(contract, direct_vm, direct_alice, pid, 30)
    mid2 = _create_milestone(contract, direct_vm, direct_alice, pid, 70)

    p = contract.get_project(pid)
    assert p["total_reserved"] == "100"
    assert p["total_released"] == "0"
    assert contract.get_available_escrow(pid) == "0"

    # Approve mid1
    _submit_evidence(contract, direct_vm, direct_bob, mid1)
    _approve(contract, direct_vm, direct_alice, mid1)

    p = contract.get_project(pid)
    assert p["total_reserved"] == "70"
    assert p["total_released"] == "30"
    # released + reserved = 30 + 70 = 100 = funded → available = 0
    assert contract.get_available_escrow(pid) == "0"
    assert contract.get_balance() == "70"

    # Approve mid2
    _submit_evidence(contract, direct_vm, direct_bob, mid2)
    _approve(contract, direct_vm, direct_alice, mid2)

    p = contract.get_project(pid)
    assert p["total_reserved"] == "0"
    assert p["total_released"] == "100"
    # released + reserved = 100 + 0 = 100 = funded → available = 0
    assert contract.get_available_escrow(pid) == "0"
    assert contract.get_balance() == "0"


def test_rejected_milestone_still_reserved(direct_deploy, direct_vm,
                                           direct_alice, direct_bob):
    """Rejected milestone stays reserved — does not become available."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    mid1 = _create_milestone(contract, direct_vm, direct_alice, pid, 60)
    mid2 = _create_milestone(contract, direct_vm, direct_alice, pid, 40)

    _submit_evidence(contract, direct_vm, direct_bob, mid1)
    _reject(contract, direct_vm, direct_alice, mid1, "Bad work")

    p = contract.get_project(pid)
    assert p["total_reserved"] == "100"
    assert contract.get_available_escrow(pid) == "0"

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="exceeds available escrow"):
        contract.create_milestone(pid, "New", "New criteria", 60)


def test_cannot_use_reserved_funds(direct_deploy, direct_vm, direct_alice,
                                   direct_bob):
    """Buyer cannot create milestone using reserved funds."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    _create_milestone(contract, direct_vm, direct_alice, pid, 100)

    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="exceeds available escrow"):
        contract.create_milestone(pid, "Extra", "Extra criteria", 1)

    p = contract.get_project(pid)
    assert p["total_reserved"] == "100"
    assert contract.get_available_escrow(pid) == "0"


def test_multiple_approvals_within_funded(direct_deploy, direct_vm,
                                          direct_alice, direct_bob):
    """Multiple approvals never exceed the funded amount."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    mid1 = _create_milestone(contract, direct_vm, direct_alice, pid, 30)
    mid2 = _create_milestone(contract, direct_vm, direct_alice, pid, 30)
    mid3 = _create_milestone(contract, direct_vm, direct_alice, pid, 40)

    for mid in [mid1, mid2, mid3]:
        _submit_evidence(contract, direct_vm, direct_bob, mid)
        _approve(contract, direct_vm, direct_alice, mid)

    p = contract.get_project(pid)
    assert p["total_released"] == "100"
    assert p["total_reserved"] == "0"
    assert contract.get_balance() == "0"


def test_released_never_exceeds_funded(direct_deploy, direct_vm, direct_alice,
                                       direct_bob):
    """total_released never exceeds total_funded under any sequence."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    mid1 = _create_milestone(contract, direct_vm, direct_alice, pid, 50)
    mid2 = _create_milestone(contract, direct_vm, direct_alice, pid, 50)

    for mid in [mid1, mid2]:
        _submit_evidence(contract, direct_vm, direct_bob, mid)
        _approve(contract, direct_vm, direct_alice, mid)

    p = contract.get_project(pid)
    assert int(p["total_released"]) <= int(p["total_funded"])
    assert p["total_released"] == "100"
    assert p["total_funded"] == "100"


def test_approved_payout_does_not_reopen_escrow(direct_deploy, direct_vm,
                                              direct_alice, direct_bob):
    """After approving a milestone, released funds cannot be re-allocated.
    Regression: old code used funded - reserved, which reopened spent escrow."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid, 100)

    # Create and approve a 60 GEN milestone
    mid1 = _create_milestone(contract, direct_vm, direct_alice, pid, 60)
    _submit_evidence(contract, direct_vm, direct_bob, mid1)
    _approve(contract, direct_vm, direct_alice, mid1)

    # After approval: reserved=0, released=60, available should be 40
    p = contract.get_project(pid)
    assert p["total_reserved"] == "0"
    assert p["total_released"] == "60"
    assert contract.get_available_escrow(pid) == "40"

    # 50 GEN milestone must fail (only 40 available)
    direct_vm.sender = direct_alice
    with pytest.raises(Exception, match="exceeds available escrow"):
        contract.create_milestone(pid, "Too much", "Criteria", 50)

    # 40 GEN milestone must succeed
    mid2 = _create_milestone(contract, direct_vm, direct_alice, pid, 40)
    assert mid2 == "m-2"
    assert contract.get_available_escrow(pid) == "0"


# ===========================================================================
# 8. EDGE CASES
# ===========================================================================
def test_nonexistent_project_fails(direct_deploy, direct_vm, direct_alice):
    """Accessing nonexistent project/milestone raises error."""
    contract = direct_deploy("contracts/milestone_vault.py")

    with pytest.raises(Exception):
        contract.get_project("p-999")

    with pytest.raises(Exception):
        contract.get_milestone("m-999")

    with pytest.raises(Exception):
        contract.get_available_escrow("p-999")

    with pytest.raises(Exception):
        contract.get_project_milestones("p-999")


def test_stored_provider_address_for_payout(direct_deploy, direct_vm,
                                            direct_alice, direct_bob):
    """Payout uses stored native Address, not any caller-supplied address."""
    contract = direct_deploy("contracts/milestone_vault.py")
    pid, mid = _setup_project_with_milestone(contract, direct_vm,
                                             direct_alice, direct_bob,
                                             ms_amount=50)
    _submit_evidence(contract, direct_vm, direct_bob, mid)

    # approve_milestone takes only milestone_id — no payout_address parameter
    result = _approve(contract, direct_vm, direct_alice, mid)
    assert result == "APPROVED"

    m = contract.get_milestone(mid)
    assert m["paid"] == "true"


# ===========================================================================
# 9. CROSS-PROJECT MILESTONE ISOLATION
# ===========================================================================

def test_get_project_milestones_isolation(direct_deploy, direct_vm,
                                          direct_alice, direct_bob,
                                          direct_charlie):
    """get_project_milestones filters by project_id, not global counter."""
    contract = direct_deploy("contracts/milestone_vault.py")

    # Project 1 — alice=buyer, bob=provider
    pid1 = _create_project(contract, direct_vm, direct_alice, direct_bob)
    _fund_project(contract, direct_vm, direct_alice, pid1, 100)
    mid_a = _create_milestone(contract, direct_vm, direct_alice, pid1, 40,
                              "Criteria A")

    # Project 2 — charlie=buyer, bob=provider
    pid2 = _create_project(contract, direct_vm, direct_charlie, direct_bob)
    _fund_project(contract, direct_vm, direct_charlie, pid2, 100)
    mid_b = _create_milestone(contract, direct_vm, direct_charlie, pid2, 60,
                              "Criteria B")

    # Project 1 should have only mid_a
    ms1 = contract.get_project_milestones(pid1)
    assert len(ms1) == 1
    assert ms1[0]["id"] == mid_a
    assert ms1[0]["project_id"] == pid1

    # Project 2 should have only mid_b
    ms2 = contract.get_project_milestones(pid2)
    assert len(ms2) == 1
    assert ms2[0]["id"] == mid_b
    assert ms2[0]["project_id"] == pid2
