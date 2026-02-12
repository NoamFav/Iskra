"""
Stats tracking. How many succeeded, how many were clean, etc.
"""


class ProcessingStats:
    """Counters for repo processing. Success, clean, dirty."""

    success_count: int = 0
    clean_count: int = 0
    dirty_count: int = 0
