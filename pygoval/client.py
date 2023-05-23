from pygoval.types import ConnectionMetadata, ConnectionState

from .exceptions import GovalException, ConnectionMetadataExeption
from .channel import Channel, Channel0
from .proto import api_pb2 as api

from typing import Optional
import websocket
import asyncio
import time

# TODO: Handle closing the client
# TODO: Error on action when client is disconnected
# TODO: Handle redirects


class Client:
    _websocket: websocket.WebSocket
    wait_messages_task: asyncio.Task[None]

    channels: dict[int, Channel]
    chan0: Channel0

    state: ConnectionState
    last_ping: float

    def __init__(self):
        self.channels = {}
        self.last_ping = 0
        self.state = ConnectionState.DISCONNECTED

    def _send(self, cmd: api.Command):
        self._websocket.send_binary(cmd.SerializePartialToString())

    def get_close_channel(self, id: int):
        async def close():
            await self.chan0.request(
                api.Command(
                    closeChan=api.CloseChannel(
                        action=api.CloseChannel.Action.TRY_CLOSE, id=id
                    )
                )
            )

        return close

    async def start(self, metadata: ConnectionMetadata):
        if error := metadata.get("message"):
            raise ConnectionMetadataExeption(error)

        self.state = ConnectionState.CONNECTING

        self._websocket = websocket.create_connection(
            metadata["gurl"] + "/wsv2/" + metadata["token"]
        )

        self.chan0 = Channel0(self._send, 0, "chan0", "chan0")
        self.channels[0] = self.chan0

        self.wait_messages_task = asyncio.get_event_loop().create_task(
            self.wait_messages(), name="Client#wait_messages"
        )

        self.state = ConnectionState.CONNECTED

    async def open_channel(
        self,
        service: str,
        name: Optional[str] = None,
        action: api.OpenChannel.Action.ValueType = api.OpenChannel.Action.CREATE,
    ) -> Channel:
        cmd = api.Command(openChan=api.OpenChannel(service=service, action=action))

        if name:
            cmd.openChan.name = name
        res = await self.chan0.request(cmd)

        if not res.openChanRes:
            raise GovalException(f"Expected openChanRes message got {res}")

        if res.openChanRes.error:
            raise GovalException(
                f"Got error {res.openChanRes.error} while opening channel"
            )

        channel = Channel(
            self._send,
            res.openChanRes.id,
            service,
            name,
            self.get_close_channel(res.openChanRes.id),
        )

        self.channels[res.openChanRes.id] = channel
        return channel

    async def wait_messages(self):
        while True:
            result: bytes = await asyncio.get_event_loop().run_in_executor(
                None, self._websocket.recv
            )  # type: ignore
            cmd = api.Command()
            cmd.ParseFromString(result)

            if cmd.protocolError.text:
                print("GovalException:", cmd.protocolError.text)
                if self.state != ConnectionState.DISCONNECTING:
                    await self.close()
                else:
                    for id in list(self.channels.keys()):
                        del self.channels[id]

                raise GovalException(cmd.protocolError.text)
                # self.wait_messages_task.cancel()

            channel = cmd.channel or 0
            await self.channels[channel]._on_message(cmd)

            if self.last_ping + 0.2 < time.time():
                await asyncio.get_event_loop().run_in_executor(
                    None, self._websocket.ping
                )

            await asyncio.sleep(0)

    async def close(self):
        self.state = ConnectionState.DISCONNECTING
        for channel_id, channel in list(self.channels.items()):
            if channel_id == 0:
                continue
            await channel.close()
            del self.channels[channel_id]
        self.wait_messages_task.cancel()
        self.state = ConnectionState.DISCONNECTED
        # raise NotImplementedError("WIP")
