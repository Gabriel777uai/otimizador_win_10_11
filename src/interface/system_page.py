"""
Página de Desempenho do Sistema e Manutenção Avançada - ALTUS PC OPTIMIZER.
Inspeção sob demanda de processos e integridade do SO com execução assíncrona e relatórios de progresso.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit
)
from PySide6.QtCore import Qt, QThread

from src.modules.gaming.performance_monitor import get_top_resource_consumers
from src.modules.windows.disk_health import optimize_volume_smart, run_chkdsk_scan
from src.modules.windows.system_health import run_sfc_scan, run_dism_scan
from src.modules.reports.history_manager import log_operation_event
from src.core.progress_manager import ProgressReporter
from src.interface.dialogs.custom_dialogs import (
    CustomConfirmDialog, CustomMessageDialog, OperationResultDialog, CustomProgressDialog, show_toast
)

class SystemTaskWorker(QThread):
    """Worker assíncrono para operações de sistema (TRIM, SFC, DISM, Chkdsk)."""
    def __init__(self, reporter: ProgressReporter, task_func, kwargs=None, op_title: str = "Tarefa de Sistema"):
        super().__init__()
        self.reporter = reporter
        self.task_func = task_func
        self.kwargs = kwargs or {}
        self.op_title = op_title
        self.result = {}

    def run(self):
        self.reporter.start(self.op_title, "Iniciando verificação do sistema...", total_items=100)
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

class SystemPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        lbl_title = QLabel("DESEMPENHO DO SISTEMA E INTEGRIDADE DO WINDOWS")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Inspeção de processos e ferramentas oficiais da Microsoft sob demanda")
        lbl_sub.setProperty("class", "PageSubtitle")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_sub)

        # Tabela de Processos
        proc_header = QHBoxLayout()
        lbl_proc_t = QLabel("PROCESSOS COM MAIOR CONSUMO DE MEMÓRIA (TOP RAM)")
        lbl_proc_t.setProperty("class", "SectionTitle")
        proc_header.addWidget(lbl_proc_t)
        proc_header.addStretch()

        btn_load_procs = QPushButton("🔍 Carregar / Atualizar Processos")
        btn_load_procs.setProperty("class", "SecondaryButton")
        btn_load_procs.clicked.connect(self.refresh_processes)
        proc_header.addWidget(btn_load_procs)
        layout.addLayout(proc_header)

        self.table_procs = QTableWidget()
        self.table_procs.setColumnCount(4)
        self.table_procs.setHorizontalHeaderLabels(["PID", "Nome do Processo", "Consumo de RAM (MB)", "% de Memória"])
        self.table_procs.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_procs.setFixedHeight(140)
        layout.addWidget(self.table_procs)

        # Ações de Otimização de Armazenamento e Integridade
        actions_grid = QHBoxLayout()

        # Frame Disco
        f_disk = QFrame()
        f_disk.setProperty("class", "CardFrame")
        dl = QVBoxLayout(f_disk)
        lbl_disk_t = QLabel("OTIMIZAÇÃO DE DISCO (TRIM / DEFRAG)")
        lbl_disk_t.setProperty("class", "CardTitle")
        dl.addWidget(lbl_disk_t)
        sub_d = QLabel("Identifica o hardware da unidade específica e aplica TRIM (SSD) ou Defrag (HDD).")
        sub_d.setProperty("class", "CardSub")
        dl.addWidget(sub_d)
        btn_trim = QPushButton("Executar Otimização Inteligente (C:)")
        btn_trim.setProperty("class", "SecondaryButton")
        btn_trim.clicked.connect(self._handle_smart_optimize)
        dl.addWidget(btn_trim)
        btn_chk = QPushButton("Verificação Rápida de Integridade (CHKDSK /scan)")
        btn_chk.setProperty("class", "SecondaryButton")
        btn_chk.clicked.connect(self._handle_chkdsk)
        dl.addWidget(btn_chk)
        actions_grid.addWidget(f_disk)

        # Frame Ferramentas do Sistema (SFC / DISM)
        f_sys = QFrame()
        f_sys.setProperty("class", "CardFrame")
        sl = QVBoxLayout(f_sys)
        lbl_sys_t = QLabel("INTEGRIDADE DO WINDOWS (SFC & DISM)")
        lbl_sys_t.setProperty("class", "CardTitle")
        sl.addWidget(lbl_sys_t)
        sub_s = QLabel("Ferramentas nativas do Windows para restaurar binários corrompidos (Nível 3).")
        sub_s.setProperty("class", "CardSub")
        sl.addWidget(sub_s)
        btn_sfc = QPushButton("Verificar Arquivos de Sistema (SFC /scannow)")
        btn_sfc.setProperty("class", "SecondaryButton")
        btn_sfc.clicked.connect(self._handle_sfc)
        sl.addWidget(btn_sfc)
        btn_dism = QPushButton("Reparar Imagem do Windows (DISM /RestoreHealth)")
        btn_dism.setProperty("class", "DangerButton")
        btn_dism.clicked.connect(self._handle_dism)
        sl.addWidget(btn_dism)
        actions_grid.addWidget(f_sys)

        layout.addLayout(actions_grid)

        # Terminal de Logs / Saída
        lbl_term_t = QLabel("RELATÓRIO DA ÚLTIMA FERRAMENTA EXECUTADA")
        lbl_term_t.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_term_t)

        self.txt_output = QTextEdit()
        self.txt_output.setReadOnly(True)
        self.txt_output.setStyleSheet("""
            background-color: #050b14;
            color: #00d2ff;
            font-family: Consolas, monospace;
            font-size: 12px;
            border: 1px solid #162238;
            border-radius: 8px;
            padding: 10px;
        """)
        self.txt_output.setPlaceholderText("Os logs e saídas do terminal das ferramentas SFC, DISM e CHKDSK aparecerão aqui...")
        layout.addWidget(self.txt_output)

    def refresh_processes(self):
        procs = get_top_resource_consumers(limit=10)
        self.table_procs.setRowCount(len(procs))
        for i, p in enumerate(procs):
            self.table_procs.setItem(i, 0, QTableWidgetItem(str(p["pid"])))
            self.table_procs.setItem(i, 1, QTableWidgetItem(str(p["name"])))
            self.table_procs.setItem(i, 2, QTableWidgetItem(f"{p['memory_mb']:.1f} MB"))
            self.table_procs.setItem(i, 3, QTableWidgetItem(f"{p['memory_percent']:.1f}%"))
        show_toast(self, "Lista de processos atualizada!", "info")

    def _handle_smart_optimize(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Otimização Inteligente de Armazenamento",
            message="O ALTUS identificará o dispositivo físico da unidade C: e disparará o comando adequado:\n\n"
                    "• TRIM (ReTrim) caso a partição esteja em SSD/NVMe.\n"
                    "• Desfragmentação caso esteja em disco magnético (HDD).\n\n"
                    "Deseja prosseguir?",
            confirm_text="Otimizar Agora",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = SystemTaskWorker(
                reporter,
                optimize_volume_smart,
                {"drive_letter": "C", "user_confirmed": True},
                op_title="Otimização de Armazenamento"
            )
            dlg = CustomProgressDialog(self, reporter, "Otimizando Unidade C:", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            if res.get("success"):
                log_operation_event("Otimização de Volume", "Concluído", res.get("message", ""))
                OperationResultDialog(
                    self,
                    title="Otimização Concluída",
                    message=res.get("message", "Ação concluída com sucesso."),
                    stats={
                        "Unidade": res.get("drive", "C:"),
                        "Ação Executada": res.get("action", "Otimização"),
                        "Tipo de Mídia": res.get("media_type", "Detectado")
                    }
                ).exec()
                show_toast(self, "Otimização de disco finalizada!", "success")
            else:
                CustomMessageDialog(self, "Falha na Otimização", res.get("message", "Erro ao otimizar volume."), dialog_type="error").exec()

    def _handle_chkdsk(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Verificação de Integridade (CHKDSK Online)",
            message="Será executado o comando 'chkdsk C: /scan' (somente leitura online).\n\n"
                    "A unidade permanecerá montada e os arquivos não serão bloqueados. Deseja iniciar?",
            confirm_text="Iniciar Verificação",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = SystemTaskWorker(
                reporter,
                run_chkdsk_scan,
                {"drive_letter": "C", "user_confirmed": True},
                op_title="Verificação CHKDSK /scan"
            )
            dlg = CustomProgressDialog(self, reporter, "Verificando Integridade do Sistema de Arquivos", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            out = res.get("output", "")
            self.txt_output.setPlainText(out)

            if res.get("success"):
                log_operation_event("CHKDSK Scan", "Concluído", res.get("message", ""))
                CustomMessageDialog(
                    self,
                    title="CHKDSK Concluído",
                    message="Verificação concluída sem detecção de falhas graves no volume C:.",
                    dialog_type="success"
                ).exec()
            else:
                CustomMessageDialog(self, "Aviso do CHKDSK", res.get("message", "Problemas ou avisos identificados."), dialog_type="warning").exec()

    def _handle_sfc(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Verificação de Componentes (SFC /scannow)",
            message="A ferramenta SFC (System File Checker) verificará a integridade de todos os arquivos protegidos do Windows "
                    "e reparará arquivos ausentes ou corrompidos utilizando o cache local.\n\n"
                    "O processo pode levar alguns minutos. Deseja iniciar a verificação?",
            confirm_text="Iniciar SFC",
            cancel_text="Cancelar",
            is_dangerous=False
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = SystemTaskWorker(
                reporter,
                run_sfc_scan,
                {"user_confirmed": True},
                op_title="Verificação SFC /scannow"
            )
            dlg = CustomProgressDialog(self, reporter, "Executando SFC /scannow", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            out = res.get("output", "")
            self.txt_output.setPlainText(out)

            if res.get("success"):
                log_operation_event("SFC Scan", "Concluído", res.get("message", ""))
                CustomMessageDialog(
                    self,
                    title="SFC /scannow Finalizado",
                    message=res.get("message", "Verificação de arquivos protegidos concluída."),
                    dialog_type="success"
                ).exec()
            else:
                CustomMessageDialog(self, "Falha no SFC", res.get("message", "Erro ao executar SFC."), dialog_type="error").exec()

    def _handle_dism(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Reparo da Imagem do Windows (DISM /RestoreHealth)",
            message="Atenção: A ferramenta DISM verificará e reparará o repositório de componentes do Windows "
                    "usando o Windows Update como fonte de reparo.\n\n"
                    "Esta operação exige conexão com a Internet e privilégios de Administrador. Deseja prosseguir?",
            confirm_text="Iniciar Reparo DISM",
            cancel_text="Cancelar",
            is_dangerous=True
        )
        if confirm.exec():
            reporter = ProgressReporter()
            worker = SystemTaskWorker(
                reporter,
                run_dism_scan,
                {"mode": "RestoreHealth", "user_confirmed": True},
                op_title="DISM /RestoreHealth"
            )
            dlg = CustomProgressDialog(self, reporter, "Executando DISM /RestoreHealth", can_cancel=False)
            worker.start()
            dlg.exec()
            worker.wait()

            res = worker.result
            out = res.get("output", "")
            self.txt_output.setPlainText(out)

            if res.get("success"):
                log_operation_event("DISM RestoreHealth", "Concluído", res.get("message", ""))
                CustomMessageDialog(
                    self,
                    title="DISM Concluído",
                    message="O repositório de componentes do Windows foi reparado com sucesso.",
                    dialog_type="success"
                ).exec()
            else:
                CustomMessageDialog(self, "Falha no DISM", res.get("message", "Erro durante a execução do DISM."), dialog_type="error").exec()
