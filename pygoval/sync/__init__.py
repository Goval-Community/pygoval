import requests


from .channel import Channel, Channel0
from .client import Client
from pygoval.types import ConnectionMetadata

__all__ = (
    # pygoval.sync.channel
    "Channel0",
    "Channel",
    # pygoval.sync.client
    "Client",
)


def fetch_token(replId: str, sid: str) -> ConnectionMetadata:
    return requests.post(
        f"https://replit.com/data/repls/{replId}/get_connection_metadata",
        headers={
            "X-Requested-With": "PyGoval (github.com/PotentialStyx/pygoval)",
            "User-Agent": "PyGoval (github.com/PotentialStyx/pygoval)",
            "origin": "https://replit.com",
        },
        cookies={"connect.sid": sid},
    ).json()
