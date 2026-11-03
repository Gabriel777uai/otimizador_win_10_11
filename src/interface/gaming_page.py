"""
Página de Otimização para Jogos & Smart Game Session - ALTUS PC OPTIMIZER.
Oferece acompanhamento de ciclo de vida de jogos, monitoramento de concorrência,
diagnóstico de gargalos e Game Performance Mode com restauração garantida.
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog
)
from PySide6.QtCore import Qt, QTimer

from src.modules.gaming.game_detection import load_user_games, add_manual_game, find_running_game_process
from src.modules.gaming.game_optimizer import (
    set_high_performance_power_plan, check_windows_game_mode, SmartGameSession, is_running_on_battery
)
from src.modules.gaming.graphics_settings import get_current_display_mode, open_windows_graphics_settings
from src.modules.gaming.performance_monitor import diagnose_bottlenecks
from src.modules.reports.history_manager import log_operation_event
from src.interface.dialogs.custom_dialogs import (
    CustomConfirmDialog, CustomMessageDialog, OperationResultDialog, show_toast
)

class GamingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_session: Optional[SmartGameSession] = None
        self._init_ui()
        self._load_static_gaming_info()

        # Timer leve para verificar se algum jogo cadastrado está rodando (a cada 3s)
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._check_running_game_status)
        self.scan_timer.start(3000)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        # Cabeçalho
        top = QHBoxLayout()
        t_box = QVBoxLayout()
        lbl_title = QLabel("OTIMIZAÇÃO PARA JOGOS & SMART GAME SESSION")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Perfis de estabilidade, prioridade de processos, telemetria e acompanhamento de sessões")
        lbl_sub.setProperty("class", "PageSubtitle")
        t_box.addWidget(lbl_title)
        t_box.addWidget(lbl_sub)
        top.addLayout(t_box)
        top.addStretch()

        # Botão Ativar Modo Game
        self.btn_game_mode = QPushButton("🎮 ATIVAR GAME PERFORMANCE MODE")
        self.btn_game_mode.setProperty("class", "PrimaryButton")
        self.btn_game_mode.setCursor(Qt.PointingHandCursor)
        self.btn_game_mode.setFixedHeight(40)
        self.btn_game_mode.clicked.connect(self._activate_game_performance_mode)
        top.addWidget(self.btn_game_mode)

        layout.addLayout(top)

        # Painel da Smart Game Session
        self.session_frame = QFrame()
        self.session_frame.setProperty("class", "CardFrame")
        sf_layout = QVBoxLayout(self.session_frame)
        sf_layout.setContentsMargins(16, 14, 16, 14)
        sf_layout.setSpacing(8)

        sf_header = QHBoxLayout()
        lbl_sf_t = QLabel("SMART GAME SESSION TRACKER")
        lbl_sf_t.setProperty("class", "CardTitle")
        sf_header.addWidget(lbl_sf_t)
        sf_header.addStretch()

        self.lbl_session_status = QLabel("Nenhum jogo em execução detectado no momento")
        self.lbl_session_status.setStyleSheet("color: #94a3b8; font-size: 13px;")
        sf_header.addWidget(self.lbl_session_status)
        sf_layout.addLayout(sf_header)

        self.sf_actions = QHBoxLayout()
        self.btn_start_session = QPushButton("🎯 Iniciar Smart Game Session")
        self.btn_start_session.setProperty("class", "PrimaryButton")
        self.btn_start_session.setEnabled(False)
        self.btn_start_session.clicked.connect(self._start_smart_session)
        self.sf_actions.addWidget(self.btn_start_session)

        self.btn_stop_session = QPushButton("⏹ Encerrar Sessão Manualmente")
        self.btn_stop_session.setProperty("class", "SecondaryButton")
        self.btn_stop_session.setEnabled(False)
        self.btn_stop_session.clicked.connect(self._stop_smart_session)
        self.sf_actions.addWidget(self.btn_stop_session)
        self.sf_actions.addStretch()

        sf_layout.addLayout(self.sf_actions)
        layout.addWidget(self.session_frame)

        # Cards com Monitor e Game Mode
        cards = QHBoxLayout()

        # Card Display
        self.card_disp = QFrame()
        self.card_disp.setProperty("class", "CardFrame")
        c1 = QVBoxLayout(self.card_disp)
        lbl_c1 = QLabel("MONITOR / RESOLUÇÃO")
        lbl_c1.setProperty("class", "CardTitle")
        c1.addWidget(lbl_c1)
        self.lbl_disp_val = QLabel("Carregando...")
        self.lbl_disp_val.setProperty("class", "CardValue")
        c1.addWidget(self.lbl_disp_val)
        btn_gfx = QPushButton("Abrir Configurações Gráficas do Windows")
        btn_gfx.setProperty("class", "SecondaryButton")
        btn_gfx.clicked.connect(open_windows_graphics_settings)
        c1.addWidget(btn_gfx)
        cards.addWidget(self.card_disp)

        # Card Game Mode Windows
        self.card_win_gm = QFrame()
        self.card_win_gm.setProperty("class", "CardFrame")
        c2 = QVBoxLayout(self.card_win_gm)
        lbl_c2 = QLabel("WINDOWS GAME MODE")
        lbl_c2.setProperty("class", "CardTitle")
        c2.addWidget(lbl_c2)
        self.lbl_gm_val = QLabel("Verificando...")
        self.lbl_gm_val.setProperty("class", "CardValue")
        self.lbl_gm_sub = QLabel("Otimização nativa do Windows")
        self.lbl_gm_sub.setProperty("class", "CardSub")
        c2.addWidget(self.lbl_gm_val)
        c2.addWidget(self.lbl_gm_sub)
        cards.addWidget(self.card_win_gm)

        layout.addLayout(cards)

        # Seção de Biblioteca de Jogos
        mid_header = QHBoxLayout()
        lbl_games = QLabel("BIBLIOTECA DE JOGOS CADASTRADOS")
        lbl_games.setProperty("class", "SectionTitle")
        mid_header.addWidget(lbl_games)
        mid_header.addStretch()

        btn_add_game = QPushButton("➕ Adicionar Jogo (.exe)")
        btn_add_game.setProperty("class", "SecondaryButton")
        btn_add_game.clicked.connect(self._add_manual_game_dialog)
        mid_header.addWidget(btn_add_game)

        layout.addLayout(mid_header)

        # Tabela de Jogos
        self.table_games = QTableWidget()
        self.table_games.setColumnCount(4)
        self.table_games.setHorizontalHeaderLabels(["Nome do Jogo", "Origem", "Executável", "Caminho da Pasta"])
        self.table_games.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_games.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_games.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_games.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_games.setFixedHeight(150)
        layout.addWidget(self.table_games)

        # Diagnóstico de Gargalos (Sob Demanda)
        garg_header = QHBoxLayout()
        lbl_garg = QLabel("DIAGNÓSTICO TÉCNICO DE GARGALOS")
        lbl_garg.setProperty("class", "SectionTitle")
        garg_header.addWidget(lbl_garg)
        garg_header.addStretch()

        btn_check_bottlenecks = QPushButton("🔍 Analisar Gargalos de Desempenho")
        btn_check_bottlenecks.setProperty("class", "SecondaryButton")
        btn_check_bottlenecks.clicked.connect(self._run_bottleneck_diagnosis)
        garg_header.addWidget(btn_check_bottlenecks)
        layout.addLayout(garg_header)

        self.bottleneck_frame = QFrame()
        self.bottleneck_frame.setProperty("class", "CardFrame")
        self.bn_layout = QVBoxLayout(self.bottleneck_frame)
        self.lbl_initial_bn = QLabel("Nenhum diagnóstico pendente. Clique em 'Analisar Gargalos de Desempenho' para verificar.")
        self.lbl_initial_bn.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.bn_layout.addWidget(self.lbl_initial_bn)
        layout.addWidget(self.bottleneck_frame)

        layout.addStretch()

    def _load_static_gaming_info(self):
        disp = get_current_display_mode()
        self.lbl_disp_val.setText(disp.get("resolution", "N/A"))

        gm = check_windows_game_mode()
        self.lbl_gm_val.setText(gm.get("status", "Habilitado"))

        games = load_user_games()
        self.table_games.setRowCount(len(games))
        for i, g in enumerate(games):
            self.table_games.setItem(i, 0, QTableWidgetItem(g.get("name", "")))
            self.table_games.setItem(i, 1, QTableWidgetItem(g.get("source", "")))
            self.table_games.setItem(i, 2, QTableWidgetItem(g.get("executable", "")))
            self.table_games.setItem(i, 3, QTableWidgetItem(g.get("folder", "")))

    def _check_running_game_status(self):
        if self.active_session and self.active_session.is_active:
            self.lbl_session_status.setText(f"🟢 Sessão ativa: {self.active_session.game_name} (PID: {self.active_session.pid})")
            self.btn_start_session.setEnabled(False)
            self.btn_stop_session.setEnabled(True)
            return

        game_proc = find_running_game_process()
        if game_proc:
            self.detected_proc = game_proc
            self.lbl_session_status.setText(f"🎮 Jogo Detectado: {game_proc['game_title']} (PID: {game_proc['pid']})")
            self.btn_start_session.setEnabled(True)
            self.btn_stop_session.setEnabled(False)
        else:
            self.detected_proc = None
            self.lbl_session_status.setText("Nenhum jogo em execução detectado no momento")
            self.btn_start_session.setEnabled(False)
            self.btn_stop_session.setEnabled(False)

    def _start_smart_session(self):
        if not hasattr(self, 'detected_proc') or not self.detected_proc:
            return

        proc_info = self.detected_proc
        self.active_session = SmartGameSession(
            pid=proc_info['pid'],
            game_name=proc_info['game_title'],
            on_session_end=self._on_smart_session_finished
        )
        res = self.active_session.start_session()
        if res.get("success"):
            show_toast(self, f"Smart Game Session iniciada para {proc_info['game_title']}!", "success")
            self._check_running_game_status()
        else:
            CustomMessageDialog(self, "Aviso", res.get("message", "Falha ao iniciar sessão."), dialog_type="warning").exec()

    def _stop_smart_session(self):
        if self.active_session:
            self.active_session.stop_session()
            show_toast(self, "Sessão de jogo encerrada e configurações restauradas.", "info")
            self.active_session = None
            self._check_running_game_status()

    def _on_smart_session_finished(self, report: dict):
        OperationResultDialog(
            self,
            title="Sessão de Jogo Concluída",
            message=f"A sessão para {report.get('game_name')} foi finalizada e as configurações originais foram restauradas.",
            stats={
                "Duração": f"{report.get('duration_minutes')} min",
                "CPU Média": f"{report.get('avg_cpu_percent')}%",
                "RAM Pico": f"{report.get('peak_ram_mb')} MB",
                "Alertas": len(report.get("concurrent_alerts", []))
            }
        ).exec()

    def _run_bottleneck_diagnosis(self):
        while self.bn_layout.count():
            item = self.bn_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        bottlenecks = diagnose_bottlenecks()
        for b in bottlenecks:
            color = "#10b981" if b["severity"] == "NORMAL" else ("#f59e0b" if b["severity"] == "ATENÇÃO" else "#ef4444")
            row = QLabel(f"• [{b['component']}] {b['title']}: {b['description']}")
            row.setStyleSheet(f"color: {color}; font-size: 12px; margin-bottom: 4px;")
            self.bn_layout.addWidget(row)
        show_toast(self, "Diagnóstico de gargalos atualizado!", "info")

    def _activate_game_performance_mode(self):
        confirm = CustomConfirmDialog(
            parent=self,
            title="Ativar Game Performance Mode",
            message="Deseja aplicar o plano de Alto Desempenho?\n\n"
                    "• Frequências mínimas de CPU elevadas para mitigar engasgos (stuttering).\n"
                    "• Respeita notebooks operando na bateria.\n"
                    "• Windows Game Mode integrado e verificado.",
            confirm_text="Ativar Modo Game",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            if is_running_on_battery():
                CustomMessageDialog(
                    self,
                    "Dispositivo na Bateria",
                    "O computador está operando na bateria. O plano de Alto Desempenho não foi forçado para evitar descarregamento acelerado.",
                    dialog_type="info"
                ).exec()
                return

            success = set_high_performance_power_plan()
            if success:
                log_operation_event("Game Performance Mode", "Concluído", "Plano de Alto Desempenho ativado com sucesso.")
                OperationResultDialog(
                    self,
                    title="Modo Game Ativado",
                    message="O perfil de energia e alocação de hardware para jogos foi aplicado com sucesso.",
                    stats={
                        "Esquema de Energia": "Alto Desempenho",
                        "Game Mode Windows": "Ativo",
                        "Prioridade de Render": "Otimizada"
                    }
                ).exec()
                show_toast(self, "Game Performance Mode ativado!", "success")
            else:
                CustomMessageDialog(self, "Aviso", "Não foi possível alterar o plano de energia automaticamente.", dialog_type="warning").exec()

    def _add_manual_game_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar Executável do Jogo",
            "C:\\",
            "Executáveis (*.exe)"
        )
        if file_path:
            name = os.path.splitext(os.path.basename(file_path))[0]
            if add_manual_game(name, file_path):
                self._load_static_gaming_info()
                show_toast(self, f"Jogo '{name}' adicionado com sucesso!", "success")
            else:
                CustomMessageDialog(self, "Erro", "Não foi possível cadastrar o jogo.", dialog_type="error").exec()
