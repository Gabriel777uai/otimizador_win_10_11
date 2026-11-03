"""
Monitor de Conexão e Conectividade Externa.
"""
import socket
from typing import Dict, Any

def check_internet_reachability(timeout: float = 3.0) -> Dict[str, Any]:
    """Testa conexão rápida via socket com hosts confiáveis."""
    test_hosts = [("8.8.8.8", 53), ("1.1.1.1", 53)]
    for host, port in test_hosts:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            s.connect((host, port))
            s.close()
            return {"connected": True, "tested_host": host, "status": "Online"}
        except Exception:
            continue
    return {"connected": False, "tested_host": "Nenhum", "status": "Offline / Sem Acesso"}
