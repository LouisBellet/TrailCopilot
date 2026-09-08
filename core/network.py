import socket

def is_connected(timeout: float = 0.5) -> bool:
    """
    Vérifie instantanément si la machine a accès à Internet.
    Teste l'accès direct aux serveurs DNS publics (Cloudflare/Google) sur le port 53.
    """
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, 53))
            sock.close()
            return True
        except OSError:
            continue
    return False