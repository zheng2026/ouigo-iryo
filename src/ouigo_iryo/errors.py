# Error payloads and exit codes follow luisgonzaleznf/renfe-cli ("Output and errors"):
# stderr gets {"error": {"code": ..., ...}}; exit 1 internal, 2 usage, 5 blocked/upstream, 7 site changed.
EXIT_CODES = {
    "unknown_station": 2, "bad_dates": 2, "bad_input": 2,
    "blocked": 5, "timeout": 5,
    "api_changed": 7,
    "browser_unavailable": 1,
}


class OuigoError(Exception):
    """Carries a machine-readable error payload: {"error": {"code": code, ...}}."""

    def __init__(self, code: str, **extra):
        super().__init__(code)
        self.code = code
        self.extra = extra

    @property
    def exit_code(self) -> int:
        return EXIT_CODES.get(self.code, 1)

    def payload(self) -> dict:
        return {"error": {"code": self.code, **self.extra}}
