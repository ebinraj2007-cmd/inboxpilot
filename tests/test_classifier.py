import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from unittest.mock import patch, MagicMock

from inboxpilot.classifier import classify_email, _rule_based_classify, CATEGORIES


def test_urgent_support_detected():
    result = _rule_based_classify(
        "URGENT: Production API is down",
        "Customers are affected right now, please fix this ASAP, it's critical.",
        "sarah@acmecorp.com",
    )
    assert result.category == "urgent_support"
    assert result.priority >= 4
    assert result.engine == "rules"


def test_sales_lead_detected():
    result = _rule_based_classify(
        "Interested in enterprise pricing",
        "Could you send over a quote and set up a demo? We have budget approved.",
        "mike@company.com",
    )
    assert result.category == "sales_lead"


def test_spam_detected():
    result = _rule_based_classify(
        "YOU HAVE WON!!!",
        "Click here now, 100% free, risk-free, wire transfer required!!!",
        "prize@scam.net",
    )
    assert result.category == "spam"
    assert result.priority == 1


def test_newsletter_detected():
    result = _rule_based_classify(
        "Weekly Digest",
        "Here is your weekly newsletter. Unsubscribe anytime.",
        "digest@noreply-updates.com",
    )
    assert result.category == "newsletter"
    assert result.priority == 1


def test_general_fallback():
    result = _rule_based_classify(
        "Question about docs",
        "Could you clarify the rate limits on the free tier?",
        "student@school.edu",
    )
    assert result.category == "general"


def test_negation_does_not_trigger_urgent():
    """Regression test: 'not urgent' should NOT be classified as urgent_support."""
    result = _rule_based_classify(
        "Feedback on dashboard",
        "Just some feedback, not urgent, no rush at all, whenever you get a chance.",
        "tom@smallbiz.co",
    )
    assert result.category != "urgent_support"


def test_all_categories_are_valid():
    for cat in CATEGORIES:
        assert isinstance(cat, str)


def test_llm_path_used_when_key_present_and_call_succeeds():
    """classify_email should prefer the LLM engine when ANTHROPIC_API_KEY is set
    and the call succeeds — mocked here so no real network/API key is needed."""
    fake_response = MagicMock()
    fake_block = MagicMock()
    fake_block.type = "text"
    fake_block.text = (
        '{"category": "urgent_support", "priority": 5, "confidence": 0.95, '
        '"reasoning": "Production outage", "suggested_reply": "Looking into it now."}'
    )
    fake_response.content = [fake_block]

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key-for-test"}):
        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = fake_response
            mock_client_cls.return_value = mock_client

            result = classify_email("Server down", "It's broken", "a@b.com")

    assert result.engine == "llm"
    assert result.category == "urgent_support"
    assert result.priority == 5


def test_falls_back_to_rules_when_llm_call_fails():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key-for-test"}):
        with patch("anthropic.Anthropic") as mock_client_cls:
            mock_client_cls.return_value.messages.create.side_effect = Exception("network error")
            result = classify_email("URGENT issue", "Something is broken and urgent", "a@b.com")

    assert result.engine == "rules"
    assert result.category == "urgent_support"


def test_no_api_key_uses_rules():
    with patch.dict("os.environ", {}, clear=True):
        result = classify_email("Hello", "Just checking in", "a@b.com")
    assert result.engine == "rules"
