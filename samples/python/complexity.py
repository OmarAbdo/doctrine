def grade(score: int) -> str:
    if score > 90:
        return "a"
    if score > 80:
        return "b"
    if score > 70:
        return "c"
    if score > 60:
        return "d"
    if score > 50:
        return "e"
    if score > 40:
        return "f"
    if score > 30:
        return "g"
    if score > 20:
        return "h"
    return "i"
