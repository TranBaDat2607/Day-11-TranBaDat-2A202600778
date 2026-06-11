"""
Lab 11 — Part 4: Human-in-the-Loop Design
  TODO 12: Confidence Router
  TODO 13: Design 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# TODO 12: Implement ConfidenceRouter
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        # Risk gate first: irreversible / high-impact actions (money transfer,
        # account closure, password change) ALWAYS go to a human, no matter how
        # confident the model is. Confidence cannot buy its way past this.
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        # HIGH confidence -> safe to auto-send with no human in the path.
        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )

        # MEDIUM confidence -> let it be drafted but queue for human review.
        if confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )

        # LOW confidence -> escalate to a human immediately.
        return RoutingDecision(
            action="escalate",
            confidence=confidence,
            reason="Low confidence — escalating",
            priority="high",
            requires_human=True,
        )


# ============================================================
# TODO 13: Design 3 HITL decision points
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "High-value / irreversible transaction approval",
        "trigger": (
            "Any money movement above a threshold (e.g. > 50,000,000 VND), a new "
            "payee, or an irreversible action (account closure, beneficiary change)."
        ),
        # Human-in-the-loop: the action is BLOCKED until a person approves it,
        # because a wrong transfer cannot be undone.
        "hitl_model": "human-in-the-loop (blocking approval before execution)",
        "context_needed": (
            "Customer ID & KYC status, source/destination account, amount, payee "
            "history (new vs known), fraud-risk score, and the original chat transcript."
        ),
        "example": (
            "Customer asks to transfer 200,000,000 VND to a brand-new overseas "
            "beneficiary. The agent prepares the transfer but a human approves "
            "it before the money leaves the account."
        ),
    },
    {
        "id": 2,
        "name": "Low-confidence or guardrail-flagged response",
        "trigger": (
            "The confidence router returns < 0.7, the LLM-as-Judge fails the "
            "response, or output guardrails redact sensitive content."
        ),
        # Human-as-tiebreaker: automation is uncertain, so a human decides whether
        # the drafted answer is correct before it reaches the customer.
        "hitl_model": "human-as-tiebreaker (review the drafted answer before send)",
        "context_needed": (
            "The user question, the model's draft answer, the confidence score, "
            "which guardrail fired, and links to the relevant policy/FAQ source."
        ),
        "example": (
            "Customer asks a nuanced question about early loan-settlement penalties. "
            "The model is only 0.55 confident; the draft is queued for an agent to "
            "verify against policy before sending."
        ),
    },
    {
        "id": 3,
        "name": "Repeated attack / abuse session monitoring",
        "trigger": (
            "A single user trips the input guardrails multiple times in one session "
            "(e.g. 3+ injection-like messages) or hits the rate limiter repeatedly."
        ),
        # Human-on-the-loop: the system keeps auto-blocking in real time, but a
        # security analyst is alerted to monitor and intervene if needed.
        "hitl_model": "human-on-the-loop (real-time monitoring & override)",
        "context_needed": (
            "User/session ID, the sequence of flagged messages, which patterns "
            "matched, request frequency, and the account's recent activity."
        ),
        "example": (
            "An account sends 5 jailbreak attempts plus rapid-fire requests in 60s. "
            "The pipeline auto-blocks each one and raises a security alert; an analyst "
            "reviews the session and can suspend the account if it looks malicious."
        ),
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
