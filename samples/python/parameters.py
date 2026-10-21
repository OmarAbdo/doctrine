def connect(host: str, port: int, user: str, password: str, timeout: int) -> str:
    return host + str(port) + user + password + str(timeout)
