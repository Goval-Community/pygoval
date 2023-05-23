from .proto import api_pb2 as api
import aiohttp


from .channel import Channel, Channel0
from .exceptions import GovalException, ConnectionMetadataExeption, ChannelClosed
from .client import Client
from .types import ConnectionMetadata, ChannelStatus, ConnectionState
import pygoval.sync as sync

__all__ = (
    # pygoval.types
    "ConnectionMetadataExeption",
    "ConnectionMetadata",
    "ConnectionState",
    # pygoval.exceptions
    "GovalException",
    "ChannelClosed",
    # pygoval.channel
    "ChannelStatus",
    "Channel0",
    "Channel",
    # pygoval.client
    "Client",
    # pygoval.sync
    "sync",
    # pygoval.proto
    "api",
)


async def fetch_token(replId: str, sid: str) -> ConnectionMetadata:
    async with aiohttp.ClientSession(
        headers={
            "X-Requested-With": "PyGoval (github.com/PotentialStyx/pygoval)",
            "User-Agent": "PyGoval (github.com/PotentialStyx/pygoval)",
            "origin": "https://replit.com",
        },
        cookies={"connect.sid": sid},
    ) as session:
        async with session.post(
            f"https://replit.com/data/repls/{replId}/get_connection_metadata"
        ) as response:
            return await response.json()
