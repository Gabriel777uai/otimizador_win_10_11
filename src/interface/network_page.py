"""
Página de Otimização e Diagnóstico de Rede - ALTUS PC OPTIMIZER.
Permite medição real de ping, perda e jitter, configuração de DNS com rollback e reparação de conexão
com execução 100% assíncrona, progresso real e diálogos personalizados.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QComboBox, QLineEdit
)
from PySide6.QtCore import Qt, QThread

from src.modules.network.network_analyzer import (
    get_network_adapters_info, get_network_gateway_and_dns, test_ping_and_jitter
)
from src.modules.network.dns_optimizer import (
    get_current_dns_status, apply_custom_dns, restore_previous_dns, DNS_PROFILES
)
from src.modules.network.network_repair import renew_ip_lease, reset_winsock_catalog
from src.modules.cleaning.dns_cache_cleaner import flush_dns_cache
from src.modules.reports.history_manager import log_operation_event
from src.core.progress_manager import ProgressReporter
from src.interface.dialogs.custom_dialogs import (
    CustomConfirmDialog, CustomMessageDialog, OperationResultDialog, CustomProgressDialog, show_toast
)

class NetworkTaskWorker(QThread):
    """Worker assíncrono para operações de rede com callback e tratamento de exceção."""
    def __init__(self, reporter: ProgressReporter, task_func, kwargs=None, op_title: str = "Operação de Rede"):
        super().__init__()
        self.reporter = reporter
        self.task_func = task_func
        self.kwargs = kwargs or {}
        self.op_title = op_title
        self.result = {}

    def run(self):
        self.reporter.start(self.op_title, "Iniciando diagnóstico de rede...", total_items=100)
        if "progress_callback" not in self.kwargs:
            self.kwargs["progress_callback"] = self.reporter.as_callback()

        try:
            res = self.task_func(**self.kwargs)
            self.result = res if isinstance(res, dict) else {"success": True, "result": res}
            
            if self.reporter.is_cancelled:
                self.reporter.cancel()
                return

            if isinstance(res, dict) and not res.get("success", True):
                self.reporter.fail(res.get("message", "A operação falhou."))
            else:
                self.reporter.complete(self.result)
        except Exception as e:
            self.result = {"success": False, "message": str(e)}
            self.reporter.fail(f"Erro inesperado: {e}")

class NetworkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.refresh_network_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        lbl_title = QLabel("DIAGNÓSTICO E OTIMIZAÇÃO DE REDE")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Diagnóstico de latência, jitter, configuração de provedores DNS e reparação de conexão")
        lbl_sub.setProperty("class", "PageSubtitle")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Cards de Status de Rede
        top_cards = QHBoxLayout()

        # Card IP e Gateway
        self.card_net_info = QFrame()
        self.card_net_info.setProperty("class", "CardFrame")
        c1 = QVBoxLayout(self.card_net_info)
        lbl_ad_title = QLabel("ADAPTADOR / IP LOCAL")
        lbl_ad_title.setProperty("class", "CardTitle")
        c1.addWidget(lbl_ad_title)
        self.lbl_ip_val = QLabel("Detectando...")
        self.lbl_ip_val.setProperty("class", "CardValue")
        self.lbl_gw_sub = QLabel("Gateway: ...")
        self.lbl_gw_sub.setProperty("class", "CardSub")
        c1.addWidget(self.lbl_ip_val)
        c1.addWidget(self.lbl_gw_sub)
        top_cards.addWidget(self.card_net_info)

        # Card Teste de Latência
        self.card_ping = QFrame()
        self.card_ping.setProperty("class", "CardFrame")
        c2 = QVBoxLayout(self.card_ping)
        lbl_ping_t = QLabel("LATÊNCIA MÉDIA (PING) & JITTER")
        lbl_ping_t.setProperty("class", "CardTitle")
        c2.addWidget(lbl_ping_t)
        self.lbl_ping_val = QLabel("-- ms")
        self.lbl_ping_val.setProperty("class", "CardValue")
        self.lbl_jitter_sub = QLabel("Perda: 0% | Jitter: 0 ms")
        self.lbl_jitter_sub.setProperty("class", "CardSub")
        c2.addWidget(self.lbl_ping_val)
        c2.addWidget(self.lbl_jitter_sub)
        top_cards.addWidget(self.card_ping)

        layout.addLayout(top_cards)

        # Card de Teste de Latência e Limpeza de Cache
        card_ping_test = QFrame()
        card_ping_test.setProperty("class", "CardFrame")
        pt_layout = QVBoxLayout(card_ping_test)
        pt_layout.setSpacing(12)

        lbl_test_t = QLabel("TESTE DE LATÊNCIA E CACHE DNS")
        lbl_test_t.setProperty("class", "SectionTitle")
        pt_layout.addWidget(lbl_test_t)

        lbl_test_sub = QLabel("Envie pacotes ICMP para avaliar tempo de resposta e jitter ou limpe o cache de resolução DNS")
        lbl_test_sub.setProperty("class", "CardSub")
        pt_layout.addWidget(lbl_test_sub)

        ping_box = QHBoxLayout()
        ping_box.setSpacing(12)
        lbl_dest = QLabel("Destino:")
        lbl_dest.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        ping_box.addWidget(lbl_dest)

        self.txt_host = QLineEdit("8.8.8.8")
        self.txt_host.setFixedHeight(36)
        self.txt_host.setMinimumWidth(180)
        self.txt_host.setPlaceholderText("Ex: 8.8.8.8, 1.1.1.1 ou google.com")
        ping_box.addWidget(self.txt_host)

        btn_ping = QPushButton("📡 Testar Latência")
        btn_ping.setProperty("class", "SecondaryButton")
        btn_ping.setFixedHeight(36)
        btn_ping.clicked.connect(self._run_ping_test)
        ping_box.addWidget(btn_ping)

        btn_flush = QPushButton("🧹 Limpar Cache DNS")
        btn_flush.setProperty("class", "SecondaryButton")
        btn_flush.setFixedHeight(36)
        btn_flush.clicked.connect(self._handle_flush_dns)
        ping_box.addWidget(btn_flush)
        ping_box.addStretch()

        pt_layout.addLayout(ping_box)
        layout.addWidget(card_ping_test)

        # Área de Configuração de DNS
        dns_frame = QFrame()
        dns_frame.setProperty("class", "CardFrame")
        dns_l = QVBoxLayout(dns_frame)
        dns_l.setSpacing(12)

        lbl_dns_t = QLabel("CONFIGURAÇÃO SEGURA DE SERVIDORES DNS")
        lbl_dns_t.setProperty("class", "SectionTitle")
        dns_l.addWidget(lbl_dns_t)

        lbl_dns_sub = QLabel("Alterne para servidores DNS de baixa latência com backup automático das configurações atuais")
        lbl_dns_sub.setProperty("class", "CardSub")
        dns_l.addWidget(lbl_dns_sub)

        dns_row = QHBoxLayout()
        dns_row.setSpacing(12)
        lbl_prov = QLabel("Provedor:")
        lbl_prov.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        dns_row.addWidget(lbl_prov)

        self.combo_dns = QComboBox()
        self.combo_dns.addItems(list(DNS_PROFILES.keys()))
        self.combo_dns.setFixedHeight(36)
        self.combo_dns.setMinimumWidth(220)
        dns_row.addWidget(self.combo_dns)

        btn_apply_dns = QPushButton("⚡ Aplicar Novo DNS")
        btn_apply_dns.setProperty("class", "PrimaryButton")
        btn_apply_dns.setFixedHeight(36)
        btn_apply_dns.clicked.connect(self._apply_dns)
        dns_row.addWidget(btn_apply_dns)

        btn_restore_dns = QPushButton("↺ Restaurar DNS Anterior")
        btn_restore_dns.setProperty("class", "SecondaryButton")
        btn_restore_dns.setFixedHeight(36)
        btn_restore_dns.clicked.connect(self._restore_dns)
        dns_row.addWidget(btn_restore_dns)
        dns_row.addStretch()

        dns_l.addLayout(dns_row)
        layout.addWidget(dns_frame)

        # Área de Reparação de Conexão
        rep_frame = QFrame()
        rep_frame.setProperty("class", "CardFrame")
        rep_l = QVBoxLayout(rep_frame)
        rep_l.setSpacing(12)

        lbl_rep_t = QLabel("REPARAÇÃO AVANÇADA DE CONEXÃO")
        lbl_rep_t.setProperty("class", "SectionTitle")
        rep_l.addWidget(lbl_rep_t)

        rep_sub = QLabel("Ferramentas para restauração em caso de instabilidade severa ou perda de rota")
        rep_sub.setProperty("class", "CardSub")
        rep_l.addWidget(rep_sub)

        rep_btns = QHBoxLayout()
        rep_btns.setSpacing(12)
        btn_renew = QPushButton("🔄 Renovar Concessão de IP (DHCP)")
        btn_renew.setProperty("class", "SecondaryButton")
        btn_renew.setFixedHeight(36)
        btn_renew.clicked.connect(self._renew_ip)
        rep_btns.addWidget(btn_renew)

        btn_winsock = QPushButton("⚠️ Redefinir Pilha Winsock (Nível 3)")
        btn_winsock.setProperty("class", "DangerButton")
        btn_winsock.setFixedHeight(36)
        btn_winsock.clicked.connect(self._reset_winsock)
        rep_btns.addWidget(btn_winsock)
        rep_btns.addStretch()

        rep_l.addLayout(rep_btns)
        layout.addWidget(rep_frame)

        layout.addStretch()

    def refresh_network_status(self):
        adapters = get_network_adapters_info()
        net = get_network_gateway_and_dns()
        if adapters:
            ad = adapters[0]
            self.lbl_ip_val.setText(f"{ad['ipv4']} ({ad['speed_mbps']})")
            self.lbl_gw_sub.setText(f"Interface: {ad['interface']} | Gateway: {net.get('gateway', 'N/A')}")
        else:
            self.lbl_ip_val.setText("Desconectado")

    def _run_ping_test(self):
        host = self.txt_host.text().strip() or "8.8.8.8"
        reporter = ProgressReporter()
        worker = NetworkTaskWorker(reporter, test_ping_and_jitter, {"host": host, "count": 4}, op_title="Diagnóstico de Conexão")
        dlg = CustomProgressDialog(self, reporter, "Testando Latência de Rede", can_cancel=True)
        worker.start()
        dlg.exec()
        worker.wait()

        res = worker.result
        avg = res.get("avg_latency_ms", 0)
        loss = res.get("packet_loss_percent", 0)
        jitter = res.get("jitter_ms", 0)

        self.lbl_ping_val.setText(f"{avg} ms")
        self.lbl_jitter_sub.setText(f"Perda: {loss}% | Jitter: {jitter} ms | Classificação: {res.get('status', 'OK')}")

        OperationResultDialog(
            self,
            title="Diagnóstico de Conexão",
            message=f"Teste finalizado para o host {host}:",
            stats={
                "Latência Média": f"{avg} ms",
                "Perda de Pacotes": f"{loss}%",
                "Jitter (Variação)": f"{jitter} ms",
                "Classificação": res.get("status", "Normal")
            }
        ).exec()

    def _handle_flush_dns(self):
        res = flush_dns_cache()
        log_operation_event("Limpeza de Cache DNS", "Concluído" if res.get("success") else "Falha", res.get("output", ""))
        CustomMessageDialog(
            self,
            title="Cache DNS Redefinido",
            message=res.get("output", "O cache de resolução DNS foi esvaziado com êxito."),
            dialog_type="success" if res.get("success") else "error"
        ).exec()
        show_toast(self, "Cache DNS limpo!", "success")

    def _apply_dns(self):
        provider = self.combo_dns.currentText()
        adapters = get_network_adapters_info()
        adapter_name = adapters[0]["interface"] if adapters else "Ethernet"

        confirm = CustomConfirmDialog(
            parent=self,
            title="Configurar Novo DNS",
            message=f"Deseja aplicar os servidores DNS do provedor '{provider}' na interface '{adapter_name}'?\n\n"
                    "O estado atual (modo e servidores) será salvo em backup com proteção de rollback automático.",
            confirm_text="Aplicar DNS",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = NetworkTaskWorker(
                reporter,
                apply_custom_dns,
                {"adapter_name": adapter_name, "profile_name": provider, "user_confirmed": True},
                op_title=f"Configurando DNS ({provider})"
            )
            dlg = CustomProgressDialog(self, reporter, "Aplicando Servidores DNS", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            if res.get("success"):
                log_operation_event("Configuração de DNS", "Concluído", res.get("message", ""))
                CustomMessageDialog(self, "DNS Atualizado", res.get("message"), dialog_type="success").exec()
                show_toast(self, f"DNS alterado para {provider}!", "success")
                self.refresh_network_status()
            else:
                CustomMessageDialog(self, "Erro na Configuração", res.get("message"), dialog_type="error").exec()

    def _restore_dns(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Restaurar DNS Anterior",
            message="Deseja restaurar as configurações originais de DNS salvas no último backup?\n\n"
                    "O ALTUS recuperará o modo exato original (estático ou automático DHCP).",
            confirm_text="Restaurar DNS",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = NetworkTaskWorker(
                reporter,
                restore_previous_dns,
                {"user_confirmed": True},
                op_title="Restaurando Configuração de DNS"
            )
            dlg = CustomProgressDialog(self, reporter, "Restaurando DNS", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            if res.get("success"):
                log_operation_event("Restauração de DNS", "Concluído", res.get("message", ""))
                CustomMessageDialog(self, "DNS Restaurado", res.get("message"), dialog_type="success").exec()
                show_toast(self, "Configurações de DNS restauradas!", "success")
                self.refresh_network_status()
            else:
                CustomMessageDialog(self, "Falha na Restauração", res.get("message"), dialog_type="error").exec()

    def _renew_ip(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Renovar Concessão de IP (DHCP)",
            message="Esta ação liberará e solicitará um novo endereço IP ao roteador (ipconfig /release e /renew).\n\n"
                    "Haverá uma perda temporária de conectividade por alguns segundos. Deseja continuar?",
            confirm_text="Renovar Agora",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = NetworkTaskWorker(
                reporter,
                renew_ip_lease,
                {"user_confirmed": True},
                op_title="Renovação de Concessão DHCP"
            )
            dlg = CustomProgressDialog(self, reporter, "Renovando IP", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            if res.get("success"):
                log_operation_event("Renovação DHCP", "Concluído", res.get("message", ""))
                CustomMessageDialog(self, "Conexão Renovada", res.get("message"), dialog_type="success").exec()
                self.refresh_network_status()
                show_toast(self, "IP renovado com sucesso!", "success")
            else:
                CustomMessageDialog(self, "Falha na Renovação", res.get("message"), dialog_type="error").exec()

    def _reset_winsock(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Redefinição do Catálogo Winsock (Avançado)",
            message="Atenção: A redefinição do catálogo Winsock restaura as configurações do protocolo de transporte "
                    "do Windows para o padrão de fábrica.\n\n"
                    "Esta operação é recomendada apenas para solucionar problemas graves de perda de conexão e "
                    "exigirá a reinicialização do computador.\n\nDeseja confirmar?",
            confirm_text="Redefinir Winsock",
            cancel_text="Cancelar",
            is_dangerous=True
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = NetworkTaskWorker(
                reporter,
                reset_winsock_catalog,
                {"user_confirmed": True},
                op_title="Redefinição Winsock"
            )
            dlg = CustomProgressDialog(self, reporter, "Redefinindo Winsock", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            if res.get("success"):
                log_operation_event("Redefinição Winsock", "Aguardando Reinicialização", res.get("message", ""))
                CustomMessageDialog(
                    self,
                    title="Winsock Redefinido",
                    message=res.get("message", "Catálogo Winsock redefinido. Reinicie o sistema para concluir o reparo."),
                    dialog_type="warning"
                ).exec()
                show_toast(self, "Winsock redefinido! Reinicie o PC.", "warning")
            else:
                CustomMessageDialog(self, "Falha no Reparo", res.get("message"), dialog_type="error").exec()
