from re import fullmatch


def parse_duration(text: str) -> int:
    """Accepts: 30s, 5m, 1h, 1h30m, 25m30s, or a bare number (seconds)."""
    if text.isdigit():
        return int(text)

    match = fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?", text)
    if not match or not any(match.groups()):
        raise ValueError(
            f"Invalid duration: {text!r}. Examples: 30s, 5m, 1h30m, 25m30s"
        )

    hours, minutes, seconds = (int(g or 0) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


def format_time(seconds: float) -> str:
    total = int(seconds)
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"
