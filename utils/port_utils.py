import socket

def find_free_port(default_port: int) -> int:
    """
    指定されたポートが使用中でなければそのポートを返し、使用中であれば次のポートを順に探索して空いているものを返します。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('localhost', default_port)) != 0:
            return default_port
    for port in range(default_port + 1, default_port + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return default_port
