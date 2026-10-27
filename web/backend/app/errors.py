class ConsoleError(Exception):
    def __init__(self, message: str, status: int = 400, *, code: str | None = None, params: dict | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code or ('SERVICE_UNAVAILABLE' if status == 503 else 'REQUEST_REJECTED')
        self.params = params or {}

    def payload(self, redact=lambda s:s):
        return {'detail':redact(str(self)), 'code':self.code, 'params':self.params,
                'fallback_message':redact(str(self))}


class WorkspaceError(ConsoleError):
    pass


class CodexUnavailable(ConsoleError):
    def __init__(self, message: str) -> None:
        super().__init__(message, 503)
