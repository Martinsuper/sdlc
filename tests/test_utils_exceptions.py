from sdlc.utils.exceptions import (
    AdapterNotFoundError,
    ConfigError,
    EntryDetectionError,
    KBWriteConflictError,
    LLMError,
    PipelineBuildError,
    ResumeExpiredError,
    RuleViolationError,
    SdlcError,
    StageExecutionError,
)

ALL_CLASSES = [
    SdlcError,
    ConfigError,
    EntryDetectionError,
    PipelineBuildError,
    StageExecutionError,
    LLMError,
    AdapterNotFoundError,
    KBWriteConflictError,
    ResumeExpiredError,
    RuleViolationError,
]


def test_str_returns_message():
    for cls in ALL_CLASSES:
        e = cls("hello")
        assert str(e) == "hello"


def test_details_default_none():
    for cls in ALL_CLASSES:
        e = cls("msg")
        assert e.details is None


def test_details_stored():
    d = {"key": "value", "num": 42}
    for cls in ALL_CLASSES:
        e = cls("msg", details=d)
        assert e.details == d


def test_inheritance():
    for cls in ALL_CLASSES:
        assert issubclass(cls, SdlcError)
        assert issubclass(cls, Exception)


def test_specific_hierarchy():
    assert issubclass(ConfigError, SdlcError)
    assert issubclass(EntryDetectionError, SdlcError)
    assert issubclass(PipelineBuildError, SdlcError)
    assert issubclass(StageExecutionError, SdlcError)
    assert issubclass(LLMError, SdlcError)
    assert issubclass(AdapterNotFoundError, SdlcError)
    assert issubclass(KBWriteConflictError, SdlcError)
    assert issubclass(ResumeExpiredError, SdlcError)
    assert issubclass(RuleViolationError, SdlcError)


def test_details_isolated():
    e1 = SdlcError("a", details={"x": 1})
    e2 = SdlcError("b", details={"y": 2})
    assert e1.details == {"x": 1}
    assert e2.details == {"y": 2}
