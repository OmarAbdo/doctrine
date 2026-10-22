"""The sha256 of every file the package index (PyPI) publishes for one exact version."""

import json
import urllib.error
import urllib.request

from doctrine.domain.dependencies.locking import Pin

PYPI = "https://pypi.org/pypi"
TIMEOUT_SECONDS = 30


class PackageIndex:
    def __init__(self, base: str = PYPI) -> None:
        self.base = base.rstrip("/")

    def hashes(self, pin: Pin) -> list[str]:
        address = f"{self.base}/{pin.name}/{pin.version}/json"
        try:
            with urllib.request.urlopen(address, timeout=TIMEOUT_SECONDS) as response:
                release = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise LookupError(f"{pin} isn't on {self.base} ({error.code})") from error
        return [str(file["digests"]["sha256"]) for file in release.get("urls", [])]
