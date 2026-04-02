"""
Memory age utilities.

Calculate and format memory age for staleness warnings.
"""


def memory_age_days(mtime_ms: float) -> int:
    """
    Days elapsed since mtime. Floor-rounded — 0 for today, 1 for
    yesterday, 2+ for older. Negative inputs (future mtime, clock skew)
    clamp to 0.
    """
    import time
    now_ms = time.time() * 1000
    days = (now_ms - mtime_ms) / 86_400_000  # milliseconds per day
    return max(0, int(days))


def memory_age(mtime_ms: float) -> str:
    """
    Human-readable age string. Models are poor at date arithmetic —
    a raw ISO timestamp doesn't trigger staleness reasoning the way
    "47 days ago" does.
    """
    d = memory_age_days(mtime_ms)
    if d == 0:
        return 'today'
    if d == 1:
        return 'yesterday'
    return f'{d} days ago'


def memory_freshness_text(mtime_ms: float) -> str:
    """
    Plain-text staleness caveat for memories >1 day old. Returns ''
    for fresh (today/yesterday) memories — warning there is noise.
    
    Use this when the consumer already provides its own wrapping
    (e.g. FileReadTool output → wrap in system reminder).
    
    Motivated by user reports of stale code-state memories (file:line
    citations to code that has since changed) being asserted as fact —
    the citation makes the stale claim sound more authoritative, not less.
    """
    d = memory_age_days(mtime_ms)
    if d <= 1:
        return ''
    return (
        f"This memory is {d} days old. "
        f"Memories are point-in-time observations, not live state — "
        f"claims about code behavior or file:line citations may be outdated. "
        f"Verify against current code before asserting as fact."
    )


def memory_freshness_note(mtime_ms: float) -> str:
    """
    Per-memory staleness note wrapped in <system-reminder> tags.
    Returns '' for memories ≤ 1 day old. Use this for callers that
    don't add their own system-reminder wrapper (e.g. FileReadTool output).
    """
    text = memory_freshness_text(mtime_ms)
    if not text:
        return ''
    return f'<system-reminder>{text}</system-reminder>\n'
