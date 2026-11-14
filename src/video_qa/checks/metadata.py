from __future__ import annotations

from typing import Any

from ..models import FAIL, PASS, WARN, CheckResult


def check_metadata(meta: dict[str, Any] | None, spec: dict[str, Any]) -> list[CheckResult]:
    m = spec["metadata"]
    if not meta:
        return [CheckResult("metadata", FAIL, "V config.yaml chybí sekce 'metadata'")]

    out: list[CheckResult] = []
    title = str(meta.get("title", "")).strip()
    desc = str(meta.get("description", "")).strip()
    tags = meta.get("tags") or []

    def add(name: str, ok: bool, ok_msg: str, bad_msg: str, status_bad: str = FAIL) -> None:
        out.append(CheckResult(name, PASS if ok else status_bad, ok_msg if ok else bad_msg))

    add("title", 0 < len(title) <= m["max_title_len"] and not ({"<", ">"} & set(title)),
        f"{len(title)} znaků",
        f"Titulek prázdný, delší než {m['max_title_len']} znaků, nebo obsahuje < >")
    add("description", 0 < len(desc) <= m["max_description_len"],
        f"{len(desc)} znaků", "Popis chybí nebo je příliš dlouhý")
    tag_chars = sum(len(str(t)) for t in tags) + max(len(tags) - 1, 0)
    # require_tags: false (např. YouTube Shorts) – chybějící tagy projdou, limit délky platí vždy
    missing_ok = not m.get("require_tags", True) and not tags
    add("tags", missing_ok or 0 < tag_chars <= m["max_tags_chars"],
        f"{len(tags)} tagů, {tag_chars} znaků",
        f"Tagy chybí nebo přesahují {m['max_tags_chars']} znaků ({tag_chars})")
    add("language", bool(meta.get("language")), str(meta.get("language")), "Chybí 'language'", WARN)
    if m["require_made_for_kids"]:
        add("made_for_kids", isinstance(meta.get("made_for_kids"), bool),
            f"made_for_kids={meta.get('made_for_kids')}",
            "Chybí explicitní 'made_for_kids: true/false' (YouTube to vyžaduje)")
    return out
