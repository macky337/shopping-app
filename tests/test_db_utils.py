import socket
import os
import pytest
from utils.port_utils import find_free_port

class DummySocket:
    def __init__(self, *args, **kwargs):
        pass
    def connect_ex(self, addr):
        # always indicate port is in use
        return 0
    def close(self):
        pass
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        pass

@ pytest.mark.parametrize("default_port, expected", [
    (65000, 65000),
    (8501, 8501)
])
def test_find_free_port_default_available(default_port, expected):
    port = find_free_port(default_port)
    assert port == expected

def test_find_free_port_skips_in_use(monkeypatch):
    """Port is in use, so next port should be returned"""
    sequence = [0, 1]
    def fake_connect_ex(self, addr):
        return sequence.pop(0)
    # Patch socket.socket to return DummySocket and override connect_ex
    monkeypatch.setattr(socket, 'socket', lambda *args, **kwargs: DummySocket())
    DummySocket.connect_ex = fake_connect_ex
    port = find_free_port(8501)
    assert port == 8502
