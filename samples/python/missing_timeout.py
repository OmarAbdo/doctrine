import requests


def fetch(address: str) -> str:
    return requests.get(address).text
