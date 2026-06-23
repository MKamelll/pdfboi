def calculate_indices(text: str) -> list[int] | None:
    gps = text.split(",")
    results = set()
    try:
        for g in gps:
            if "-" in g:
                parts = g.split("-")
                if len(parts) == 2:
                    start, end = int(parts[0]) - 1, int(parts[1]) - 1
                    start = max(0, min(start, self.page_count))
                    end = max(0, min(end, self.page_count))
                    for i in range(start, end + 1):
                        results.add(i)
            else:
                g_int = max(0, min(int(g) - 1, self.page_count))
                results.add(g_int)
        return list(results)
    except ValueError:
        pass
