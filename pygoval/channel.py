from .exceptions import ChannelClosed, GovalException
from pygoval.types import ChannelStatus
from .proto import api_pb2 as api
from . import base36

from typing import Any, Callable, Optional
import asyncio
import random


class Channel:
    _send: Callable[[api.Command], None]
    _close: Optional[Any]

    request_map: dict[str, asyncio.Future[api.Command]]
    command_listeners: list[Callable[[api.Command], None]]

    status: ChannelStatus
    name: Optional[str]
    channel_id: int
    service: str

    def __init__(
        self,
        send: Callable[[api.Command], None],
        channel_id: int,
        service: str,
        name: Optional[str] = None,
        close_channel: Optional[Any] = None,
    ):
        self.request_map = {}
        self._send = send
        self.command_listeners = []
        self._close = close_channel

        self.channel_id = channel_id
        self.service = service
        self.name = name
        self.status = ChannelStatus.OPEN

    def on_command(self, func: Callable[[api.Command], None]) -> Callable[[], None]:
        if self.status == ChannelStatus.CLOSED:
            raise ChannelClosed("Cannot attach command listener to a closed channel")

        self.command_listeners.append(func)

        # destroy listener
        return lambda: self.command_listeners.remove(func)

    async def close(self, reason="Unknown Reason"):
        if not self._close:
            raise GovalException(
                f"Channel with id: {self.channel_id} "
                + "cannot be closed as it wasn't initialized correctly"
            )
            return
        self.status = ChannelStatus.CLOSING

        await self._close()

        for ref, request in self.request_map.items():
            request.set_exception(ChannelClosed(reason))
            del self.request_map[ref]

        self.command_listeners = []

        self.status = ChannelStatus.CLOSED
        pass

    async def _on_message(self, cmd: api.Command):
        for listener in self.command_listeners:
            listener(cmd)

        if cmd.ref in self.request_map:
            self.request_map[cmd.ref].set_result(cmd)
            del self.request_map[cmd.ref]

    async def request(self, cmd: api.Command) -> api.Command:
        ref = base36.encode(random.randint(int(1e15), int(1e16 - 1)))
        cmd.ref = ref

        await self.send(cmd)

        future: asyncio.Future[api.Command] = asyncio.get_event_loop().create_future()
        self.request_map[ref] = future

        return await future

    async def send(self, cmd: api.Command):
        if self.status == ChannelStatus.CLOSED:
            raise ChannelClosed("Cannot send messages to a closed channel")

        if self.status == ChannelStatus.CLOSING:
            raise ChannelClosed(
                "Cannot send messages after requesting to close the channel"
            )

        cmd.channel = self.channel_id
        self._send(cmd)


class Channel0(Channel):
    def close(self, _=""):
        raise GovalException("Channel 0 cannot be closed, close the client instead.")
