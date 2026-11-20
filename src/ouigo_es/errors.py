class OuigoError(Exception):
    """Carries a machine-readable error payload: {"error": code, ...}."""

    def __init__(self, code: str, **extra):
        super().__init__(code)
        self.code = code
        self.extra = extra

    def payload(self) -> dict:
        return {"error": self.code, **self.extra}
