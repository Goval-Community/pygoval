import queue
import threading
from pygoval.exceptions import GovalException, ConnectionMetadataExeption
from pygoval.types import ConnectionMetadata, ConnectionState
from pygoval.proto import api_pb2 as api
from .channel import Channel, Channel0

from typing import Optional
import websocket
import multiprocessing
import time


# TODO: Handle closing the client
# TODO: Error on action when client is disconnected
# TODO: Handle redirects


class Client:
    _websocket: websocket.WebSocket
    wait_messages_thread: multiprocessing.Process

    channels: dict[int, Channel]
    chan0: Channel0

    state: ConnectionState
    last_ping: float

    def __init__(self):
        self.channels = {}
        self.last_ping = 0
        self.state = ConnectionState.DISCONNECTED
        self.incoming_message_queue = queue.Queue()
        self.outgoing_message_queue = queue.Queue()

    def _send(self, cmd: api.Command):
        self._websocket.send_binary(cmd.SerializePartialToString())

    def get_close_channel(self, id: int):
        def close():
            self.chan0.request(
                api.Command(
                    closeChan=api.CloseChannel(action=api.CloseChannel.Action.TRY_CLOSE)
                )
            )

        return close

    def start(self, metadata: ConnectionMetadata):
        if error := metadata.get("message"):
            raise ConnectionMetadataExeption(error)

        self.state = ConnectionState.CONNECTING

        self._websocket = websocket.create_connection(
            metadata["gurl"] + "/wsv2/" + metadata["token"], enable_multithread=True
        )

        self.chan0 = Channel0(self._send, 0, "chan0", "chan0")
        self.channels[0] = self.chan0

        self.wait_messages_thread = multiprocessing.Process(
            target=self.wait_messages, args=(self._websocket,), daemon=True
        )
        self.wait_messages_thread.start()

        self.state = ConnectionState.CONNECTED

    def open_channel(
        self,
        service: str,
        name: Optional[str] = None,
        action: api.OpenChannel.Action.ValueType = api.OpenChannel.Action.CREATE,
    ) -> Channel:
        cmd = api.Command(openChan=api.OpenChannel(service=service, action=action))

        if name:
            cmd.openChan.name = name
        res = self.chan0.request(cmd)

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

    def wait_messages(self, websocket: websocket.WebSocket):
        while True:
            result: bytes = websocket.recv()  # type: ignore
            cmd = api.Command()
            cmd.ParseFromString(result)

            channel = cmd.channel or 0
            # self.incoming_message_queue.put
            # print(cmd)
            if cmd.ref:
                self.channels[channel].request_map[cmd.ref] = cmd
            else:
                print(cmd)
            # self.channels[channel]._on_message(cmd)

            if self.last_ping + 0.2 < time.time():
                websocket.ping()

    def close(self):
        pass
        # self.wait_messages_thread.stop
