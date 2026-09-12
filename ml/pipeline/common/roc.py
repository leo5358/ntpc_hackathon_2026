"""ROC (民國) calendar helpers."""
ROC_OFFSET = 1911


def academic_year(date: str) -> int:
    """'2024/07/12' -> 112. 學年度 N runs from August of N+1911 to July of N+1912."""
    year, month, _ = (int(part) for part in date.split("/"))
    return year - ROC_OFFSET if month >= 8 else year - ROC_OFFSET - 1
