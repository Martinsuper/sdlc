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
