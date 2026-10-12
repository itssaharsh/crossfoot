"""Settings shared by the commands: how many model calls may be in flight at once (`--workers`)."""
DEFAULT_WORKERS = 3
workers = DEFAULT_WORKERS


def set_workers(n) -> int:
    global workers
    workers = max(1, int(n))
    return workers
