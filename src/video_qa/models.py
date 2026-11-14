from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

PASS, FAIL, WARN, SKIP = "pass", "fail", "warn", "skip"


@dataclass
class CheckResult:
    name: str
    status: str
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Report:
    episode: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def failed(self) -> list[CheckResult]:
        return [r for r in self.results if r.status == FAIL]

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode": self.episode,
            "ok": self.ok,
            "summary": {
                s: sum(1 for r in self.results if r.status == s) for s in (PASS, FAIL, WARN, SKIP)
            },
            "results": [r.to_dict() for r in self.results],
        }
