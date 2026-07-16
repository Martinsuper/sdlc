from sdlc.llm.client import ModelRouter
from sdlc.llm.models import CompletionRequest, Message, Role

# --- Legacy tests (default anthropic behavior) ---


def test_route_default_returns_sonnet():
    router = ModelRouter()
    req = CompletionRequest()
    assert router.route(req) == "claude-sonnet-4-20250514"


def test_route_high_returns_opus():
    router = ModelRouter()
    req = CompletionRequest(metadata={"tier": "high"})
    assert router.route(req) == "claude-opus-4-20250514"


def test_route_low_returns_haiku():
    router = ModelRouter()
    req = CompletionRequest(metadata={"tier": "low"})
    assert router.route(req) == "claude-haiku-4-5-20251001"


def test_route_medium_returns_sonnet():
    router = ModelRouter()
    req = CompletionRequest(metadata={"tier": "medium"})
    assert router.route(req) == "claude-sonnet-4-20250514"


def test_route_unknown_tier_returns_sonnet():
    router = ModelRouter()
    req = CompletionRequest(metadata={"tier": "unknown"})
    assert router.route(req) == "claude-sonnet-4-20250514"


def test_route_sets_req_model():
    router = ModelRouter()
    req = CompletionRequest(metadata={"tier": "high"})
    model = router.route(req)
    req.model = model
    assert req.model == "claude-opus-4-20250514"


def test_route_no_metadata_returns_sonnet():
    router = ModelRouter()
    req = CompletionRequest(messages=[Message(role=Role.USER, content="hello")])
    assert router.route(req) == "claude-sonnet-4-20250514"


# --- New tests with provider_type ---


def test_route_anthropic_provider_high():
    router = ModelRouter(provider_type="anthropic")
    req = CompletionRequest(metadata={"tier": "high"})
    assert router.route(req) == "claude-opus-4-20250514"


def test_route_anthropic_provider_medium():
    router = ModelRouter(provider_type="anthropic")
    req = CompletionRequest(metadata={"tier": "medium"})
    assert router.route(req) == "claude-sonnet-4-20250514"


def test_route_anthropic_provider_low():
    router = ModelRouter(provider_type="anthropic")
    req = CompletionRequest(metadata={"tier": "low"})
    assert router.route(req) == "claude-haiku-4-5-20251001"


def test_route_openai_provider_high():
    router = ModelRouter(provider_type="openai")
    req = CompletionRequest(metadata={"tier": "high"})
    assert router.route(req) == "o1"


def test_route_openai_provider_medium():
    router = ModelRouter(provider_type="openai")
    req = CompletionRequest(metadata={"tier": "medium"})
    assert router.route(req) == "gpt-4o"


def test_route_openai_provider_low():
    router = ModelRouter(provider_type="openai")
    req = CompletionRequest(metadata={"tier": "low"})
    assert router.route(req) == "gpt-4o-mini"


def test_route_unknown_provider_uses_default_model():
    router = ModelRouter(provider_type="deepseek", default_model="deepseek-chat")
    req = CompletionRequest(metadata={"tier": "medium"})
    # deepseek is not in RULES, so it falls through to default_model
    assert router.route(req) == "deepseek-chat"


def test_route_unknown_provider_no_default_returns_sonnet():
    router = ModelRouter(provider_type="deepseek")
    req = CompletionRequest(metadata={"tier": "medium"})
    # deepseek is not in RULES, default_model is empty -> falls to hardcoded default
    assert router.route(req) == "claude-sonnet-4-20250514"


def test_route_custom_default_model():
    router = ModelRouter(provider_type="custom", default_model="my-custom-model")
    req = CompletionRequest()
    assert router.route(req) == "my-custom-model"


def test_route_anthropic_provider_with_custom_default():
    router = ModelRouter(provider_type="anthropic", default_model="claude-sonnet-4-20250514")
    req = CompletionRequest(metadata={"tier": "high"})
    # anthropic IS in RULES, so it uses the rule, not default
    assert router.route(req) == "claude-opus-4-20250514"
