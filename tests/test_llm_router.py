from sdlc.llm.client import ModelRouter
from sdlc.llm.models import CompletionRequest, Message, Role


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
