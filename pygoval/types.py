import enum
from typing import Optional, TypedDict


# TODO: use enum.StrEnum when min python version is bumped to 3.11
class ChannelStatus(enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CLOSING = "closing"


class ConnectionState(enum.IntEnum):
    CONNECTING = 0
    CONNECTED = 1
    DISCONNECTED = 2
    DISCONNECTING = 3


class ConnectionMetadata(TypedDict):
    token: str
    gurl: str
    conmanURL: str
    message: Optional[str]
