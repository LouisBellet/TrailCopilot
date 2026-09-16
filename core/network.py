import socket
import urllib.request

def is_connected(timeout: float = 1.5) -> bool:
    """
    Vérification robuste de l'accès Internet.
    Teste le port 443 (HTTPS) vers Cloudflare/Google puis valide via une requête HTTP.
    """
    for host in ("1.1.1.1", "8.8.8.8"):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, 443))
            sock.close()
            return True
        except OSError:
            pass

    try:
        urllib.request.urlopen("https://www.google.com", timeout=timeout)
        return True
    except Exception:
        return False