def find(rows: list[list[list[int]]]) -> int:
    for row in rows:
        for column in row:
            for cell in column:
                if cell > 0:
                    return cell
    return 0
