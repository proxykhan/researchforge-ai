"""Tests for LLM data models."""

from researchforge.llm.models import LLMConfig, LLMResponse, Message, TokenUsage


class TestMessage:
    def test_creation(self):
        msg = Message(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_frozen(self):
        msg = Message(role="user", content="hello")
        try:
            msg.role = "assistant"  # type: ignore[misc]
            raise AssertionError("Should have raised")
        except AttributeError:
            pass


class TestTokenUsage:
    def test_total_tokens(self):
        usage = TokenUsage(input_tokens=100, output_tokens=50)
        assert usage.total_tokens == 150

    def test_frozen(self):
        usage = TokenUsage(input_tokens=10, output_tokens=20)
        try:
            usage.input_tokens = 99  # type: ignore[misc]
            raise AssertionError("Should have raised")
        except AttributeError:
            pass


class TestLLMResponse:
    def test_creation(self):
        usage = TokenUsage(input_tokens=10, output_tokens=20)
        resp = LLMResponse(content="answer", model="claude-sonnet-5", usage=usage)
        assert resp.content == "answer"
        assert resp.model == "claude-sonnet-5"
        assert resp.stop_reason is None

    def test_with_stop_reason(self):
        usage = TokenUsage(input_tokens=10, output_tokens=20)
        resp = LLMResponse(content="done", model="test", usage=usage, stop_reason="end_turn")
        assert resp.stop_reason == "end_turn"


class TestLLMConfig:
    def test_defaults(self):
        config = LLMConfig()
        assert config.model == "claude-sonnet-5"
        assert config.max_tokens == 4096
        assert config.temperature == 0.3
        assert config.system is None
        assert config.stop_sequences == []

    def test_custom(self):
        config = LLMConfig(model="custom-model", max_tokens=1024, system="be helpful")
        assert config.model == "custom-model"
        assert config.max_tokens == 1024
        assert config.system == "be helpful"
