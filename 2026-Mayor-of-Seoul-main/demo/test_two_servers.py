"""Run the source and broadcaster as separate Uvicorn processes."""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

ROOT = Path(__file__).resolve().parent


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def server(module, port, **variables):
    with subprocess.Popen(
        [sys.executable, "-m", "uvicorn", f"{module}:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "error"],
        cwd=ROOT,
        env={**os.environ, **variables},
    ) as process:
        try:
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline and process.poll() is None:
                try:
                    with urlopen(f"http://127.0.0.1:{port}/health", timeout=0.5) as response:
                        health = json.load(response)
                    break
                except (URLError, TimeoutError):
                    time.sleep(0.05)
            else:
                raise RuntimeError(f"{module} did not start on port {port}")
            yield health
        finally:
            if process.poll() is None:
                process.terminate()


class TwoServerTest(unittest.IsolatedAsyncioTestCase):
    async def test_replay_and_source_unavailable(self):
        source_port = free_port()
        with server("election_source", source_port, ELECTION_REPLAY_INTERVAL="0.01") as source:
            self.assertEqual(source["role"], "election-source")
            broadcast_port = free_port()
            feed = f"ws://127.0.0.1:{source_port}/ws/feed"
            browser = f"ws://127.0.0.1:{broadcast_port}/ws/replay"
            with server("app", broadcast_port, ELECTION_FEED_URL=feed) as broadcast:
                self.assertEqual(broadcast["role"], "broadcast")
                async with connect(browser) as stream:
                    events = [json.loads(message) async for message in stream]
                self.assertEqual([event["sequence"] for event in events], list(range(31)))
                self.assertTrue(all(event["mode"] == "simulation" for event in events))
                self.assertTrue(all(event["source_sent_at"] <= event["delivered_at"] for event in events))
                self.assertEqual(events[-1]["count_progress_pct"], 100)
                self.assertEqual(events[-1]["counted_ballots"], 5289383)
                self.assertTrue(events[-1]["complete"])

        unavailable_port = free_port()
        with server("app", unavailable_port, ELECTION_FEED_URL=feed):
            async with connect(f"ws://127.0.0.1:{unavailable_port}/ws/replay") as stream:
                failure = json.loads(await stream.recv())
                self.assertEqual(failure["code"], "election_feed_unavailable")
                with self.assertRaises(ConnectionClosed) as closed:
                    await stream.recv()
                self.assertEqual(closed.exception.rcvd.code, 1011)
