"""The job-level ladder, lowest first. Levels make roles comparable: pay-gap and outlier
analytics compare people with the same title *and* level."""

JOB_LEVELS: tuple[str, ...] = ("Junior", "Mid", "Senior", "Lead", "Principal")


def level_rank(level: str) -> int:
    return JOB_LEVELS.index(level)
