"""
Módulo de Diagnóstico e Análise de Rede.
Inspeciona interfaces, IPs, Gateways e DNS via psutil e winreg nativos (sem shell).
Executa testes de latência e perda somente sob demanda do usuário.
"""
import socket
import statistics
import time
import winreg
from typing import Dict, Any, List, Optional, Callable
import psutil

from src.utils.logger import app_logger
from src.utils.command_runner import run_command

def get_network_adapters_info() -> List[Dict[str, Any]]:
    """Coleta adaptadores de rede, status e endereços IPv4 de forma nativa e instantânea."""
    adapters = []
    try:
        stats = psutil.net_if_stats()
        addrs = psutil.net_if_addrs()

        for iface_name, iface_addrs in addrs.items():
            if_stat = stats.get(iface_name)
            is_up = if_stat.isup if if_stat else False
            speed_mbps = if_stat.speed if if_stat else 0

            ipv4 = "Não configurado"
            netmask = "N/A"
            for addr in iface_addrs:
                if addr.family == socket.AF_INET:
                    ipv4 = addr.address
                    netmask = addr.netmask
                    break

            if ipv4 != "Não configurado" and not ipv4.startswith("127."):
                adapters.append({
                    "interface": iface_name,
                    "is_up": is_up,
                    "speed_mbps": f"{speed_mbps} Mbps" if speed_mbps > 0 else "Conectado",
                    "ipv4": ipv4,
                    "netmask": netmask
                })
    except Exception as e:
        app_logger.warning(f"Erro ao listar adaptadores: {e}")

    return adapters

def get_network_gateway_and_dns() -> Dict[str, Any]:
    """Obtém Gateway padrão e servidores DNS ativos diretamente pelo Registro do Windows (0 ms)."""
    info = {"gateway": "Detectado", "dns_servers": []}

    try:
        k_ifaces = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        )
        num_subkeys = winreg.QueryInfoKey(k_ifaces)[0]

        for i in range(num_subkeys):
            sub = winreg.EnumKey(k_ifaces, i)
            ks = winreg.OpenKey(k_ifaces, sub)
            num_vals = winreg.QueryInfoKey(ks)[1]
            vals = dict([winreg.EnumValue(ks, j)[:2] for j in range(num_vals)])
            winreg.CloseKey(ks)

            gw = vals.get("DhcpDefaultGateway") or vals.get("DefaultIPGateway")
            if gw:
                if isinstance(gw, list) and gw:
                    info["gateway"] = gw[0]
                elif isinstance(gw, str) and gw.strip():
                    info["gateway"] = gw.split()[0]

            dns = vals.get("DhcpNameServer") or vals.get("NameServer")
            if dns:
                servers = dns.replace(",", " ").split()
                for s in servers:
                    if s not in info["dns_servers"]:
                        info["dns_servers"].append(s)

            if info["gateway"] != "Detectado" and info["dns_servers"]:
                break

        winreg.CloseKey(k_ifaces)
    except Exception:
        pass

    if not info["dns_servers"]:
        info["dns_servers"] = ["Automático (DHCP)"]

    return info

def test_ping_and_jitter(
    host: str = "8.8.8.8",
    count: int = 4,
    progress_callback: Optional[Callable[[int, str], None]] = None
) -> Dict[str, Any]:
    """
    Executa teste real de ping SOMENTE quando solicitado pelo usuário.
    Suporta relatório de progresso durante o envio e recebimento de pacotes ICMP.
    """
    app_logger.info(f"Testando latência para {host} ({count} pacotes)...")
    if progress_callback:
        progress_callback(20, f"Disparando pacotes ICMP para {host}...")

    cmd = ["ping", "-n", str(count), host]
    rc, out, _ = run_command(cmd, timeout=12)

    if progress_callback:
        progress_callback(75, "Calculando latência média, jitter e perda de pacotes...")

    latencies = []
    for line in out.splitlines():
        line_clean = line.strip()
        if "tempo=" in line_clean.lower() or "time=" in line_clean.lower():
            try:
                parts = line_clean.split("tempo=") if "tempo=" in line_clean else line_clean.split("time=")
                ms_part = parts[1].split("ms")[0].replace("<", "").strip()
                latencies.append(float(ms_part))
            except Exception:
                continue

    if latencies:
        avg_latency = round(statistics.mean(latencies), 1)
        jitter = round(statistics.stdev(latencies), 1) if len(latencies) > 1 else 0.0
        min_lat = min(latencies)
        max_lat = max(latencies)
        loss_pct = round(((count - len(latencies)) / count) * 100, 1)
    else:
        avg_latency = 0.0
        jitter = 0.0
        min_lat = 0.0
        max_lat = 0.0
        loss_pct = 100.0

    return {
        "host": host,
        "packets_sent": count,
        "packets_received": len(latencies),
        "packet_loss_percent": loss_pct,
        "avg_latency_ms": avg_latency,
        "jitter_ms": jitter,
        "min_latency_ms": min_lat,
        "max_latency_ms": max_lat,
        "status": "Excelente" if avg_latency < 30 and loss_pct == 0 else ("Bom" if avg_latency < 80 and loss_pct == 0 else "Instável")
    }
