class SdlcError(Exception):
    def __init__(self, message: str, details: dict[str, object] | None = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)

    def __str__(self) -> str:
        return self.message


class ConfigError(SdlcError):
    pass


class EntryDetectionError(SdlcError):
    pass


class PipelineBuildError(SdlcError):
    pass


class StageExecutionError(SdlcError):
    pass


class LLMError(SdlcError):
    pass


class AdapterNotFoundError(SdlcError):
    pass


class KBWriteConflictError(SdlcError):
    pass


class ResumeExpiredError(SdlcError):
    pass


class RuleViolationError(SdlcError):
    pass


class ClarificationNeeded(SdlcError):  # noqa: N818 — control-flow signal, not an error condition
    """Raised when a subagent's ask_user needs a human answer.

    Propagates out of the tool-loop so the coordinator can suspend the pipeline
    (WAITING_CLARIFICATION) rather than returning a fabricated answer. Carries
    the question, options, and a stable question id for the resume round-trip.
    """

    def __init__(
        self,
        question: str,
        options: list[str] | None = None,
        question_id: str = "",
        agent_id: str = "",
    ) -> None:
        super().__init__(question)
        self.question = question
        self.options = options or []
        self.question_id = question_id
        self.agent_id = agent_id
