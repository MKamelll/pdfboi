def calculate_indices(text: str, page_count: int) -> list[int] | None:
    gps = text.split(",")
    results = set()
    try:
        for g in gps:
            if "-" in g:
                parts = g.split("-")
                if len(parts) == 2:
                    start, end = int(parts[0]) - 1, int(parts[1]) - 1
                    start = max(0, min(start, page_count))
                    end = max(0, min(end, page_count))
                    for i in range(start, end + 1):
                        results.add(i)
            else:
                g_int = max(0, min(int(g) - 1, page_count))
                results.add(g_int)
        return list(results) if len(results) > 0 else None
    except ValueError:
        pass
