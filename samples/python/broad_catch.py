def safe_divide(numerator: int, denominator: int) -> float:
    try:
        return numerator / denominator
    except Exception:
        return 0.0
