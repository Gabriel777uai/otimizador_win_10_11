"""
Página WINDOWS BACKGROUND CONTROL - ALTUS PC OPTIMIZER.
Interface gráfica desktop moderna em PySide6 para gerenciamento de processos,
recursos de IA, Microsoft Copilot, Recall, Edge, Widgets, Gaming DVR,
indexação de desenvolvimento, serviços e perfis de otimização.
"""
from typing import Dict, Any, List, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QCheckBox, QComboBox, QFileDialog, QLineEdit
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont

from src.core.permissions import is_admin
from src.core.safety_manager import safety_manager
from src.interface.dialogs.custom_dialogs import (
    CustomConfirmDialog, CustomMessageDialog, OperationResultDialog,
    CustomProgressDialog, show_toast
)

import src.modules.windows_background as wb

class BackgroundWorker(QThread):
    """Worker assíncrono para operações de segundo plano sem travamento da interface."""
    finished_signal = Signal(dict)

    def __init__(self, task_func, kwargs=None):
        super().__init__()
        self.task_func = task_func
        self.kwargs = kwargs or {}

    def run(self):
        try:
            res = self.task_func(**self.kwargs)
            self.finished_signal.emit(res if isinstance(res, dict) else {"success": True, "result": res})
        except Exception as e:
            self.finished_signal.emit({"success": False, "message": str(e)})

class WindowsBackgroundPage(QWidget):
    """Painel principal do módulo Windows Background Control."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.baseline_snapshot = None
        self.current_snapshot = None
        self._init_ui()
        self.refresh_all_diagnostics()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # 1. CABEÇALHO DA PÁGINA COM AÇÕES RÁPIDAS
        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        lbl_title = QLabel("WINDOWS BACKGROUND CONTROL")
        lbl_title.setProperty("class", "PageTitle")
        lbl_sub = QLabel("Controle inteligente de processos, recursos de IA, serviços e otimização avançada do Windows 10/11")
        lbl_sub.setProperty("class", "PageSubtitle")
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        btn_analyze = QPushButton("🔍 Analisar Agora")
        btn_analyze.setProperty("class", "SecondaryButton")
        btn_analyze.setFixedHeight(36)
        btn_analyze.clicked.connect(self.refresh_all_diagnostics)
        header_layout.addWidget(btn_analyze)

        btn_measure = QPushButton("⚖️ Antes / Depois")
        btn_measure.setProperty("class", "SecondaryButton")
        btn_measure.setFixedHeight(36)
        btn_measure.clicked.connect(self._run_before_after_comparison)
        header_layout.addWidget(btn_measure)

        btn_restore_all = QPushButton("↺ Restaurar Tudo")
        btn_restore_all.setProperty("class", "WarningButton")
        btn_restore_all.setFixedHeight(36)
        btn_restore_all.clicked.connect(self._handle_restore_all)
        header_layout.addWidget(btn_restore_all)

        main_layout.addLayout(header_layout)

        # 2. CARDS SUPERIORES DE STATUS DO SISTEMA E IA (4 Cards)
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)

        self.card_os = self._create_status_card("SISTEMA & BUILD", "Detectando...", "Windows OS", "#00d2ff")
        cards_layout.addWidget(self.card_os)

        self.card_copilot = self._create_status_card("MICROSOFT COPILOT", "Detectando...", "Assistente de IA", "#38bdf8")
        cards_layout.addWidget(self.card_copilot)

        self.card_recall = self._create_status_card("WINDOWS RECALL", "Verificando...", "Captura de IA", "#f59e0b")
        cards_layout.addWidget(self.card_recall)

        self.card_edge = self._create_status_card("EDGE & SEGUNDO PLANO", "Analisando...", "Startup Boost & P2P", "#10b981")
        cards_layout.addWidget(self.card_edge)

        main_layout.addLayout(cards_layout)

        # 3. ABAS DE CONTROLE ESPECIALIZADO
        self.tabs = QTabWidget()

        self.tab_processes = self._build_processes_tab()
        self.tab_ai = self._build_ai_tab()
        self.tab_edge_exp = self._build_edge_experience_tab()
        self.tab_gaming_index = self._build_gaming_index_tab()
        self.tab_services = self._build_services_tab()
        self.tab_profiles = self._build_profiles_tab()

        self.tabs.addTab(self.tab_processes, "📊 Processos & Recursos")
        self.tabs.addTab(self.tab_ai, "🤖 IA & Copilot")
        self.tabs.addTab(self.tab_edge_exp, "🌐 Edge & Experiência")
        self.tabs.addTab(self.tab_gaming_index, "🎮 Jogos & Indexação")
        self.tabs.addTab(self.tab_services, "⚙️ Serviços Avançados")
        self.tabs.addTab(self.tab_profiles, "⚡ Perfis de Otimização")

        main_layout.addWidget(self.tabs)

    def _create_status_card(self, title: str, value: str, sub: str, accent: str) -> QFrame:
        """Cria um card com indicador visual e dados."""
        card = QFrame()
        card.setProperty("class", "CardFrame")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setProperty("class", "CardTitle")
        lbl_v = QLabel(value)
        lbl_v.setProperty("class", "CardValue")
        lbl_v.setStyleSheet(f"color: {accent}; font-size: 15px; font-weight: 800; border: none;")
        lbl_s = QLabel(sub)
        lbl_s.setProperty("class", "CardSub")

        cl.addWidget(lbl_t)
        cl.addWidget(lbl_v)
        cl.addWidget(lbl_s)
        card.lbl_val = lbl_v
        card.lbl_sub = lbl_s
        return card

    # =========================================================================
    # ABA 1: PROCESSOS & RECURSOS EM SEGUNDO PLANO
    # =========================================================================
    def _build_processes_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(10)

        top_row = QHBoxLayout()
        lbl_sec = QLabel("MAIORES CONSUMIDORES EM SEGUNDO PLANO (AMOSTRAGEM REAL)")
        lbl_sec.setProperty("class", "SectionTitle")
        top_row.addWidget(lbl_sec)
        top_row.addStretch()

        self.lbl_proc_count = QLabel("Carregando processos...")
        self.lbl_proc_count.setStyleSheet("color: #94a3b8; font-size: 12px;")
        top_row.addWidget(self.lbl_proc_count)
        layout.addLayout(top_row)

        self.table_procs = QTableWidget()
        self.table_procs.setColumnCount(7)
        self.table_procs.setHorizontalHeaderLabels([
            "Processo", "PID", "Fabricante", "Memória (RAM)", "CPU (%)", "Categoria", "Recomendação"
        ])
        header = self.table_procs.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        self.table_procs.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_procs.setFixedHeight(300)
        layout.addWidget(self.table_procs)

        # Banner de Medição Antes e Depois
        self.frame_snapshot = QFrame()
        self.frame_snapshot.setStyleSheet("""
            QFrame {
                background-color: #070d19;
                border: 1px solid #1e3a5f;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        sn_l = QHBoxLayout(self.frame_snapshot)
        sn_l.setSpacing(14)
        
        lbl_icon = QLabel("⚖️")
        lbl_icon.setStyleSheet("font-size: 20px; border: none;")
        sn_l.addWidget(lbl_icon)

        self.lbl_snapshot_text = QLabel("Nenhuma medição antes/depois registrada ainda. Clique em 'Antes / Depois' no topo para registrar o ponto inicial.")
        self.lbl_snapshot_text.setStyleSheet("color: #cbd5e1; font-size: 12px; border: none;")
        self.lbl_snapshot_text.setWordWrap(True)
        sn_l.addWidget(self.lbl_snapshot_text, stretch=1)

        layout.addWidget(self.frame_snapshot)
        return w

    # =========================================================================
    # ABA 2: IA & MICROSOFT COPILOT
    # =========================================================================
    def _build_ai_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(14)

        # Card Copilot
        card_cop = QFrame()
        card_cop.setProperty("class", "CardFrame")
        c_l = QVBoxLayout(card_cop)
        c_l.setSpacing(10)

        lbl_c_t = QLabel("MICROSOFT COPILOT (ASSISTENTE DE INTELIGÊNCIA ARTIFICIAL)")
        lbl_c_t.setProperty("class", "SectionTitle")
        c_l.addWidget(lbl_c_t)

        lbl_c_desc = QLabel("O Copilot integra serviços de IA ao Windows 11 e Edge, mantendo conexões e processos em segundo plano. "
                           "Você pode ocultar o botão da barra de tarefas e desativar suas chamadas sem comprometer outros aplicativos.")
        lbl_c_desc.setProperty("class", "CardSub")
        lbl_c_desc.setWordWrap(True)
        c_l.addWidget(lbl_c_desc)

        self.chk_copilot_disable = QCheckBox("Desativar Microsoft Copilot em segundo plano e ocultar botão na barra de tarefas")
        self.chk_copilot_disable.setChecked(True)
        c_l.addWidget(self.chk_copilot_disable)

        row_cop = QHBoxLayout()
        self.lbl_cop_status = QLabel("Consultando estado...")
        self.lbl_cop_status.setStyleSheet("color: #00d2ff; font-weight: bold;")
        row_cop.addWidget(self.lbl_cop_status)
        row_cop.addStretch()

        btn_apply_cop = QPushButton("⚡ Aplicar Configuração do Copilot")
        btn_apply_cop.setProperty("class", "PrimaryButton")
        btn_apply_cop.setFixedHeight(36)
        btn_apply_cop.clicked.connect(self._handle_apply_copilot)
        row_cop.addWidget(btn_apply_cop)
        c_l.addLayout(row_cop)

        layout.addWidget(card_cop)

        # Card Windows Recall
        card_rec = QFrame()
        card_rec.setProperty("class", "CardFrame")
        r_l = QVBoxLayout(card_rec)
        r_l.setSpacing(10)

        lbl_r_t = QLabel("WINDOWS RECALL (INSTANTÂNEOS DE IA EM COPILOT+ PCS)")
        lbl_r_t.setProperty("class", "SectionTitle")
        r_l.addWidget(lbl_r_t)

        self.lbl_recall_notes = QLabel("Verificando compatibilidade de hardware...")
        self.lbl_recall_notes.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.lbl_recall_notes.setWordWrap(True)
        r_l.addWidget(self.lbl_recall_notes)

        self.chk_recall_disable = QCheckBox("Suspender captura e desativar análise de dados do Windows Recall (DisableAIDataAnalysis)")
        r_l.addWidget(self.chk_recall_disable)

        row_rec = QHBoxLayout()
        self.lbl_recall_badge = QLabel("Hardware Incompatível")
        self.lbl_recall_badge.setStyleSheet("color: #f59e0b; font-weight: bold;")
        row_rec.addWidget(self.lbl_recall_badge)
        row_rec.addStretch()

        self.btn_apply_recall = QPushButton("🛡️ Configurar Windows Recall")
        self.btn_apply_recall.setProperty("class", "WarningButton")
        self.btn_apply_recall.setFixedHeight(36)
        self.btn_apply_recall.clicked.connect(self._handle_apply_recall)
        row_rec.addWidget(self.btn_apply_recall)
        r_l.addLayout(row_rec)

        layout.addWidget(card_rec)
        layout.addStretch()
        return w

    # =========================================================================
    # ABA 3: EDGE & EXPERIÊNCIA WINDOWS
    # =========================================================================
    def _build_edge_experience_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(14)

        # Card Edge
        f_edge = QFrame()
        f_edge.setProperty("class", "CardFrame")
        el = QVBoxLayout(f_edge)
        el.setSpacing(10)

        lbl_e_t = QLabel("MICROSOFT EDGE BACKGROUND CONTROL")
        lbl_e_t.setProperty("class", "SectionTitle")
        el.addWidget(lbl_e_t)

        lbl_e_sub = QLabel("O Edge mantém instâncias em segundo plano (Startup Boost) e executa extensões mesmo após fechar a janela. "
                           "Esta otimização não apaga senhas, favoritos, perfis nem afeta o WebView2 de outros aplicativos.")
        lbl_e_sub.setProperty("class", "CardSub")
        lbl_e_sub.setWordWrap(True)
        el.addWidget(lbl_e_sub)

        self.chk_edge_boost = QCheckBox("Desativar Startup Boost (impede o Edge de pré-carregar na inicialização do Windows)")
        self.chk_edge_boost.setChecked(True)
        el.addWidget(self.chk_edge_boost)

        self.chk_edge_bg = QCheckBox("Desativar modo em segundo plano (fecha processos e extensões ao fechar a janela do navegador)")
        self.chk_edge_bg.setChecked(True)
        el.addWidget(self.chk_edge_bg)

        row_edge = QHBoxLayout()
        self.lbl_edge_diag = QLabel("Edge ativo...")
        self.lbl_edge_diag.setStyleSheet("color: #00d2ff; font-weight: bold;")
        row_edge.addWidget(self.lbl_edge_diag)
        row_edge.addStretch()

        btn_edge = QPushButton("⚡ Aplicar Otimizações do Edge")
        btn_edge.setProperty("class", "PrimaryButton")
        btn_edge.setFixedHeight(36)
        btn_edge.clicked.connect(self._handle_apply_edge)
        row_edge.addWidget(btn_edge)
        el.addLayout(row_edge)
        layout.addWidget(f_edge)

        # Card Widgets & Sugestões
        f_wid = QFrame()
        f_wid.setProperty("class", "CardFrame")
        wl = QVBoxLayout(f_wid)
        wl.setSpacing(10)

        lbl_w_t = QLabel("WIDGETS, NOTÍCIAS E SUGESTÕES DO WINDOWS")
        lbl_w_t.setProperty("class", "SectionTitle")
        wl.addWidget(lbl_w_t)

        self.chk_wid_hide = QCheckBox("Ocultar painel de Widgets e Notícias da barra de tarefas (reduz consumo constante de rede e RAM)")
        self.chk_wid_hide.setChecked(True)
        wl.addWidget(self.chk_wid_hide)

        self.chk_wid_sug = QCheckBox("Desativar dicas automáticas, sugestões de aplicativos e propagandas no Menu Iniciar")
        self.chk_wid_sug.setChecked(True)
        wl.addWidget(self.chk_wid_sug)

        row_wid = QHBoxLayout()
        row_wid.addStretch()
        btn_wid = QPushButton("⚡ Aplicar Otimizações de Experiência")
        btn_wid.setProperty("class", "PrimaryButton")
        btn_wid.setFixedHeight(36)
        btn_wid.clicked.connect(self._handle_apply_widgets)
        row_wid.addWidget(btn_wid)
        wl.addLayout(row_wid)
        layout.addWidget(f_wid)

        # Card Otimização de Entrega
        f_del = QFrame()
        f_del.setProperty("class", "CardFrame")
        dl = QVBoxLayout(f_del)
        dl.setSpacing(10)

        lbl_d_t = QLabel("COMPARTILHAMENTO DE ATUALIZAÇÕES P2P (DELIVERY OPTIMIZATION)")
        lbl_d_t.setProperty("class", "SectionTitle")
        dl.addWidget(lbl_d_t)

        lbl_d_sub = QLabel("Por padrão, o Windows pode usar sua banda de upload para enviar atualizações a computadores desconhecidos. "
                           "Definir como 'HTTP Apenas' garante downloads 100% seguros diretamente da Microsoft sem consumo de upload.")
        lbl_d_sub.setProperty("class", "CardSub")
        lbl_d_sub.setWordWrap(True)
        dl.addWidget(lbl_d_sub)

        row_del = QHBoxLayout()
        self.lbl_del_st = QLabel("Modo P2P ativo")
        self.lbl_del_st.setStyleSheet("color: #00d2ff; font-weight: bold;")
        row_del.addWidget(self.lbl_del_st)
        row_del.addStretch()

        btn_del = QPushButton("🔒 Baixar Direto da Microsoft (Sem P2P)")
        btn_del.setProperty("class", "SecondaryButton")
        btn_del.setFixedHeight(36)
        btn_del.clicked.connect(self._handle_apply_delivery)
        row_del.addWidget(btn_del)
        dl.addLayout(row_del)
        layout.addWidget(f_del)

        layout.addStretch()
        return w

    # =========================================================================
    # ABA 4: JOGOS & INDEXAÇÃO DE DESENVOLVIMENTO
    # =========================================================================
    def _build_gaming_index_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(14)

        # Card Game DVR
        f_game = QFrame()
        f_game.setProperty("class", "CardFrame")
        gl = QVBoxLayout(f_game)
        gl.setSpacing(10)

        lbl_g_t = QLabel("CAPTURA CONTÍNUA EM SEGUNDO PLANO (GAME DVR / XBOX)")
        lbl_g_t.setProperty("class", "SectionTitle")
        gl.addWidget(lbl_g_t)

        lbl_g_sub = QLabel("A gravação em segundo plano grava vídeo sem parar no disco para permitir clipes de 'Gravar isso'. "
                           "Desativá-la elimina centenas de megabytes de escrita contínua em SSD/HDD. O Modo de Jogo e a barra Xbox continuam funcionando.")
        lbl_g_sub.setProperty("class", "CardSub")
        lbl_g_sub.setWordWrap(True)
        gl.addWidget(lbl_g_sub)

        row_game = QHBoxLayout()
        self.chk_dvr_disable = QCheckBox("Desativar gravação contínua em segundo plano (HistoricalCaptureEnabled=0)")
        self.chk_dvr_disable.setChecked(True)
        row_game.addWidget(self.chk_dvr_disable)
        row_game.addStretch()

        btn_dvr = QPushButton("🎮 Otimizar Captura de Jogos")
        btn_dvr.setProperty("class", "PrimaryButton")
        btn_dvr.setFixedHeight(36)
        btn_dvr.clicked.connect(self._handle_apply_game_dvr)
        row_game.addWidget(btn_dvr)
        gl.addLayout(row_game)
        layout.addWidget(f_game)

        # Card Smart Index
        f_idx = QFrame()
        f_idx.setProperty("class", "CardFrame")
        il = QVBoxLayout(f_idx)
        il.setSpacing(10)

        lbl_i_t = QLabel("INDEXAÇÃO INTELIGENTE DE PROJETOS DE CÓDIGO (WINDOWS SEARCH)")
        lbl_i_t.setProperty("class", "SectionTitle")
        il.addWidget(lbl_i_t)

        lbl_i_sub = QLabel("Diretórios de bibliotecas pesadas (node_modules, vendor, .git, venv) sobrecarregam o indexador SearchIndexer. "
                           "Mapeie e exclua essas pastas da pesquisa para economizar I/O e CPU. Nenhum arquivo será excluído.")
        lbl_i_sub.setProperty("class", "CardSub")
        lbl_i_sub.setWordWrap(True)
        il.addWidget(lbl_i_sub)

        btn_row_idx = QHBoxLayout()
        btn_scan_folders = QPushButton("🔍 Mapear Pastas de Projetos (node_modules, .git, venv)")
        btn_scan_folders.setProperty("class", "SecondaryButton")
        btn_scan_folders.setFixedHeight(36)
        btn_scan_folders.clicked.connect(self._scan_dev_folders)
        btn_row_idx.addWidget(btn_scan_folders)

        btn_add_custom = QPushButton("📁 Adicionar Pasta Manualmente...")
        btn_add_custom.setProperty("class", "SecondaryButton")
        btn_add_custom.setFixedHeight(36)
        btn_add_custom.clicked.connect(self._add_custom_dev_folder)
        btn_row_idx.addWidget(btn_add_custom)
        btn_row_idx.addStretch()
        il.addLayout(btn_row_idx)

        self.table_folders = QTableWidget()
        self.table_folders.setColumnCount(3)
        self.table_folders.setHorizontalHeaderLabels(["Excluir da Busca", "Nome", "Caminho do Diretório"])
        self.table_folders.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_folders.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_folders.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_folders.setFixedHeight(160)
        il.addWidget(self.table_folders)

        row_save_idx = QHBoxLayout()
        self.lbl_idx_status = QLabel("Nenhuma pasta mapeada ainda.")
        self.lbl_idx_status.setStyleSheet("color: #94a3b8; font-size: 12px;")
        row_save_idx.addWidget(self.lbl_idx_status)
        row_save_idx.addStretch()

        btn_apply_idx = QPushButton("💾 Salvar Exclusões da Indexação")
        btn_apply_idx.setProperty("class", "PrimaryButton")
        btn_apply_idx.setFixedHeight(36)
        btn_apply_idx.clicked.connect(self._save_index_exclusions)
        row_save_idx.addWidget(btn_apply_idx)
        il.addLayout(row_save_idx)

        layout.addWidget(f_idx)
        layout.addStretch()
        return w

    # =========================================================================
    # ABA 5: SERVIÇOS AVANÇADOS
    # =========================================================================
    def _build_services_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(10)

        # Banner de Proteção
        prot_banner = QFrame()
        prot_banner.setStyleSheet("background-color: #0c1829; border: 1px solid #00d2ff; border-radius: 8px; padding: 10px;")
        pb_l = QHBoxLayout(prot_banner)
        lbl_p_ico = QLabel("🛡️")
        lbl_p_ico.setStyleSheet("font-size: 18px; border: none;")
        pb_l.addWidget(lbl_p_ico)
        lbl_p_txt = QLabel("PROTEÇÃO ATIVA: Serviços vitais do Windows (RPC, DHCP, DNS, Windows Defender, Firewall, Áudio e drivers) "
                           "são estritamente protegidos pelo Safety Manager e NUNCA serão desativados.")
        lbl_p_txt.setStyleSheet("color: #e2e8f0; font-size: 12px; font-weight: 600; border: none;")
        lbl_p_txt.setWordWrap(True)
        pb_l.addWidget(lbl_p_txt, stretch=1)
        layout.addWidget(prot_banner)

        svc_top = QHBoxLayout()
        lbl_s_t = QLabel("SERVIÇOS OPCIONAIS E DE TERCEIROS CONFIGURÁVEIS")
        lbl_s_t.setProperty("class", "SectionTitle")
        svc_top.addWidget(lbl_s_t)
        svc_top.addStretch()

        btn_refresh_svc = QPushButton("🔄 Atualizar Lista de Serviços")
        btn_refresh_svc.setProperty("class", "SecondaryButton")
        btn_refresh_svc.setFixedHeight(32)
        btn_refresh_svc.clicked.connect(self._load_services_table)
        svc_top.addWidget(btn_refresh_svc)
        layout.addLayout(svc_top)

        self.table_services = QTableWidget()
        self.table_services.setColumnCount(6)
        self.table_services.setHorizontalHeaderLabels([
            "Nome do Serviço", "Nome de Exibição", "Inicialização", "Estado", "Categoria", "Segurança"
        ])
        h_svc = self.table_services.horizontalHeader()
        h_svc.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h_svc.setSectionResizeMode(1, QHeaderView.Stretch)
        h_svc.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        h_svc.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        h_svc.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        h_svc.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table_services.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_services.setFixedHeight(280)
        layout.addWidget(self.table_services)

        row_svc_action = QHBoxLayout()
        lbl_mod = QLabel("Alterar Inicialização do Selecionado:")
        lbl_mod.setStyleSheet("color: #e2e8f0; font-weight: 600;")
        row_svc_action.addWidget(lbl_mod)

        self.combo_svc_type = QComboBox()
        self.combo_svc_type.addItems(["Manual (demand)", "Desativado (disabled)", "Automático (auto)"])
        self.combo_svc_type.setFixedHeight(36)
        self.combo_svc_type.setMinimumWidth(180)
        row_svc_action.addWidget(self.combo_svc_type)

        btn_apply_svc = QPushButton("⚙️ Aplicar ao Serviço Selecionado")
        btn_apply_svc.setProperty("class", "PrimaryButton")
        btn_apply_svc.setFixedHeight(36)
        btn_apply_svc.clicked.connect(self._apply_service_change)
        row_svc_action.addWidget(btn_apply_svc)
        row_svc_action.addStretch()

        layout.addLayout(row_svc_action)
        return w

    # =========================================================================
    # ABA 6: PERFIS DE OTIMIZAÇÃO (3 PERFIS PROFISSIONAIS)
    # =========================================================================
    def _build_profiles_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(10, 12, 10, 10)
        layout.setSpacing(14)

        lbl_p_info = QLabel("SELEÇÃO DE PERFIS PROFISSIONAIS DE SEGUNDO PLANO")
        lbl_p_info.setProperty("class", "SectionTitle")
        layout.addWidget(lbl_p_info)

        lbl_p_sub = QLabel("Cada perfil agrupa um conjunto coerente e reversível de políticas. Todas as ações geram registros automáticos no Auto Recovery Center.")
        lbl_p_sub.setProperty("class", "CardSub")
        layout.addWidget(lbl_p_sub)

        profiles_grid = QHBoxLayout()
        profiles_grid.setSpacing(14)

        for p in wb.get_available_profiles():
            card = self._build_profile_card(p)
            profiles_grid.addWidget(card)

        layout.addLayout(profiles_grid)
        layout.addStretch()
        return w

    def _build_profile_card(self, p: Dict[str, Any]) -> QFrame:
        """Monta um card interativo para um dos perfis profissionais."""
        card = QFrame()
        card.setProperty("class", "CardFrame")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 16, 18, 16)
        cl.setSpacing(10)

        lbl_tag = QLabel(p.get("tag", "PERFIL"))
        lbl_tag.setStyleSheet("color: #00d2ff; font-size: 11px; font-weight: bold; letter-spacing: 0.5px;")
        cl.addWidget(lbl_tag)

        lbl_name = QLabel(p["name"])
        lbl_name.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: 800;")
        lbl_name.setWordWrap(True)
        cl.addWidget(lbl_name)

        lbl_desc = QLabel(p["description"])
        lbl_desc.setStyleSheet("color: #cbd5e1; font-size: 12px; line-height: 1.3;")
        lbl_desc.setWordWrap(True)
        cl.addWidget(lbl_desc)

        cl.addWidget(QLabel("AÇÕES INCLUÍDAS:"))
        actions_box = QVBoxLayout()
        actions_box.setSpacing(4)
        for act in p.get("actions_description", []):
            lbl_act = QLabel(f"• {act}")
            lbl_act.setStyleSheet("color: #94a3b8; font-size: 11px;")
            lbl_act.setWordWrap(True)
            actions_box.addWidget(lbl_act)
        cl.addLayout(actions_box)

        cl.addStretch()

        btn_apply = QPushButton(f"⚡ Aplicar {p['id'].replace('_', ' ')}")
        btn_apply.setProperty("class", "PrimaryButton")
        btn_apply.setFixedHeight(36)
        btn_apply.clicked.connect(lambda _, pid=p["id"]: self._apply_profile(pid))
        cl.addWidget(btn_apply)

        return card

    # =========================================================================
    # LÓGICA DE DIAGNÓSTICO E CONTROLE
    # =========================================================================
    def refresh_all_diagnostics(self):
        """Atualiza todos os cards e tabelas de diagnóstico."""
        feats = wb.detect_all_windows_features()

        # Atualiza Card 1: SO & Build
        os_text = f"{feats.os_name} (Build {feats.build_number})"
        self.card_os.lbl_val.setText(os_text)
        self.card_os.lbl_sub.setText(f"Edição: {feats.edition} | {feats.architecture}")

        # Atualiza Card 2: Copilot
        if feats.copilot_installed:
            cop_val = "Ativo na Barra" if feats.copilot_taskbar_visible else "Oculto / Desativado"
            cop_color = "#38bdf8" if feats.copilot_taskbar_visible else "#10b981"
        else:
            cop_val = "Não Instalado"
            cop_color = "#94a3b8"
        self.card_copilot.lbl_val.setText(cop_val)
        self.card_copilot.lbl_val.setStyleSheet(f"color: {cop_color}; font-size: 15px; font-weight: 800; border: none;")
        self.card_copilot.lbl_sub.setText(f"{feats.copilot_processes_active} processos de IA em execução")

        # Atualiza Card 3: Recall
        if feats.recall_hardware_compatible:
            rec_val = "Desativado" if feats.recall_disabled else "Compatível / Ativo"
            rec_color = "#10b981" if feats.recall_disabled else "#00d2ff"
        else:
            rec_val = "Hardware Incompatível"
            rec_color = "#f59e0b"
        self.card_recall.lbl_val.setText(rec_val)
        self.card_recall.lbl_val.setStyleSheet(f"color: {rec_color}; font-size: 15px; font-weight: 800; border: none;")
        self.card_recall.lbl_sub.setText("Requer NPU Copilot+ e Win11 24H2")

        # Atualiza Card 4: Edge & P2P
        p2p_txt = "P2P Desativado (HTTP)" if feats.delivery_p2p_mode == 0 else "P2P Ativo (Consome Upload)"
        self.card_edge.lbl_val.setText("Otimizado" if feats.edge_startup_boost_disabled else "Startup Boost Ativo")
        self.card_edge.lbl_sub.setText(p2p_txt)

        # Atualiza Controles da Aba de IA
        self.lbl_cop_status.setText(f"Status Atual: {cop_val}")
        self.lbl_recall_notes.setText(feats.recall_notes)
        self.lbl_recall_badge.setText("Compatível" if feats.recall_hardware_compatible else "Incompatível")
        self.btn_apply_recall.setEnabled(feats.recall_hardware_compatible)

        # Atualiza Aba de Edge e P2P
        self.lbl_edge_diag.setText("Startup Boost: " + ("Desativado" if feats.edge_startup_boost_disabled else "Ativo"))
        self.lbl_del_st.setText(p2p_txt)

        # Carrega tabelas
        self._load_processes_table()
        self._load_services_table()

    def _load_processes_table(self):
        """Preenche a tabela com os maiores consumidores em segundo plano."""
        procs = wb.background_analyzer.get_top_background_consumers(limit=25)
        self.table_procs.setRowCount(len(procs))
        self.lbl_proc_count.setText(f"Total analisado: {len(procs)} processos")

        for r, p in enumerate(procs):
            self.table_procs.setItem(r, 0, QTableWidgetItem(p["name"]))
            self.table_procs.setItem(r, 1, QTableWidgetItem(str(p["pid"])))
            self.table_procs.setItem(r, 2, QTableWidgetItem(p["publisher"]))
            self.table_procs.setItem(r, 3, QTableWidgetItem(f"{p['memory_rss_mb']} MB"))
            self.table_procs.setItem(r, 4, QTableWidgetItem(f"{p['cpu_percent']}%"))
            self.table_procs.setItem(r, 5, QTableWidgetItem(p["category"]))

            recom = "Protegido (Sistema)" if not p["is_safe_to_close"] else "Seguro Fechar Antes de Jogar"
            item_recom = QTableWidgetItem(recom)
            if not p["is_safe_to_close"]:
                item_recom.setForeground(QColor("#10b981"))
            else:
                item_recom.setForeground(QColor("#38bdf8"))
            self.table_procs.setItem(r, 6, item_recom)

    def _load_services_table(self):
        """Carrega serviços opcionais e de terceiros na tabela."""
        all_svcs = wb.service_analyzer.analyze_windows_services()
        # Filtra opcionais e terceiros primeiro
        filtered = [s for s in all_svcs if s.can_configure or not s.is_protected][:35]
        self.services_cache = filtered
        self.table_services.setRowCount(len(filtered))

        for r, s in enumerate(filtered):
            self.table_services.setItem(r, 0, QTableWidgetItem(s.name))
            self.table_services.setItem(r, 1, QTableWidgetItem(s.display_name))
            self.table_services.setItem(r, 2, QTableWidgetItem(s.start_type))
            self.table_services.setItem(r, 3, QTableWidgetItem(s.status))
            self.table_services.setItem(r, 4, QTableWidgetItem(s.category))

            sec_item = QTableWidgetItem("Protegido" if s.is_protected else "Configurável")
            sec_item.setForeground(QColor("#10b981") if s.is_protected else QColor("#00d2ff"))
            self.table_services.setItem(r, 5, sec_item)

    # =========================================================================
    # AÇÕES DE CONFIGURAÇÃO INDIVIDUAL
    # =========================================================================
    def _handle_apply_copilot(self):
        disable = self.chk_copilot_disable.isChecked()
        res = wb.configure_copilot(disable=disable, user_confirmed=True)
        if res.get("success"):
            show_toast(self, res.get("message"), "success")
            self.refresh_all_diagnostics()
        else:
            CustomMessageDialog(self, "Aviso Copilot", res.get("message"), dialog_type="warning").exec()

    def _handle_apply_recall(self):
        disable = self.chk_recall_disable.isChecked()
        confirm = CustomConfirmDialog(
            self,
            title="Confirmação - Windows Recall",
            message="A desativação do Windows Recall suspenderá a captura periódica de instantâneos semânticos da tela.\n\n"
                    "Deseja aplicar esta política no Registro do Windows?",
            confirm_text="Confirmar Alteração",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            res = wb.configure_recall(disable=disable, user_confirmed=True)
            if res.get("success"):
                show_toast(self, res.get("message"), "success")
                self.refresh_all_diagnostics()
            else:
                CustomMessageDialog(self, "Aviso Recall", res.get("message"), dialog_type="warning").exec()

    def _handle_apply_edge(self):
        boost = self.chk_edge_boost.isChecked()
        bg = self.chk_edge_bg.isChecked()
        res = wb.configure_edge_background(disable_startup_boost=boost, disable_background_mode=bg, user_confirmed=True)
        if res.get("success"):
            show_toast(self, res.get("message"), "success")
            self.refresh_all_diagnostics()
        else:
            CustomMessageDialog(self, "Aviso Edge", res.get("message"), dialog_type="warning").exec()

    def _handle_apply_widgets(self):
        hide_w = self.chk_wid_hide.isChecked()
        dis_sug = self.chk_wid_sug.isChecked()
        res = wb.configure_widgets(hide_widgets=hide_w, disable_suggestions=dis_sug, user_confirmed=True)
        if res.get("success"):
            show_toast(self, res.get("message"), "success")
            self.refresh_all_diagnostics()
        else:
            CustomMessageDialog(self, "Aviso Widgets", res.get("message"), dialog_type="warning").exec()

    def _handle_apply_delivery(self):
        res = wb.configure_delivery_optimization(disable_p2p_sharing=True, user_confirmed=True)
        if res.get("success"):
            show_toast(self, res.get("message"), "success")
            self.refresh_all_diagnostics()
        else:
            CustomMessageDialog(self, "Aviso Delivery Optimization", res.get("message"), dialog_type="warning").exec()

    def _handle_apply_game_dvr(self):
        dis_dvr = self.chk_dvr_disable.isChecked()
        res = wb.configure_gaming_dvr(disable_background_recording=dis_dvr, user_confirmed=True)
        if res.get("success"):
            show_toast(self, res.get("message"), "success")
            self.refresh_all_diagnostics()
        else:
            CustomMessageDialog(self, "Aviso Game DVR", res.get("message"), dialog_type="warning").exec()

    def _scan_dev_folders(self):
        """Mapeia pastas pesadas de desenvolvimento."""
        folders = wb.scan_common_dev_folders()
        self.table_folders.setRowCount(len(folders))
        self.lbl_idx_status.setText(f"{len(folders)} pastas localizadas.")

        for r, f in enumerate(folders):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked)
            self.table_folders.setItem(r, 0, chk)
            self.table_folders.setItem(r, 1, QTableWidgetItem(f["name"]))
            self.table_folders.setItem(r, 2, QTableWidgetItem(f["path"]))

        show_toast(self, f"{len(folders)} pastas de desenvolvimento localizadas!", "info")

    def _add_custom_dev_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Pasta para Excluir da Indexação")
        if folder:
            r = self.table_folders.rowCount()
            self.table_folders.insertRow(r)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked)
            self.table_folders.setItem(r, 0, chk)
            self.table_folders.setItem(r, 1, QTableWidgetItem(Path(folder).name))
            self.table_folders.setItem(r, 2, QTableWidgetItem(folder))
            self.lbl_idx_status.setText(f"{self.table_folders.rowCount()} pastas na lista.")

    def _save_index_exclusions(self):
        paths = []
        for r in range(self.table_folders.rowCount()):
            item = self.table_folders.item(r, 0)
            if item and item.checkState() == Qt.Checked:
                p_item = self.table_folders.item(r, 2)
                if p_item and p_item.text():
                    paths.append(p_item.text())

        if not paths:
            CustomMessageDialog(self, "Aviso de Indexação", "Selecione ao menos uma pasta da tabela para salvar.", dialog_type="info").exec()
            return

        res = wb.configure_index_exclusions(paths, user_confirmed=True)
        if res.get("success"):
            show_toast(self, res.get("message"), "success")
        else:
            CustomMessageDialog(self, "Erro na Indexação", res.get("message"), dialog_type="warning").exec()

    def _apply_service_change(self):
        row = self.table_services.currentRow()
        if row < 0 or row >= len(self.services_cache):
            CustomMessageDialog(self, "Seleção Necessária", "Selecione um serviço da tabela para alterar a inicialização.", dialog_type="info").exec()
            return

        svc = self.services_cache[row]
        if svc.is_protected:
            CustomMessageDialog(self, "Ação Bloqueada", f"O serviço '{svc.name}' é protegido e não pode ser modificado.", dialog_type="warning").exec()
            return

        type_map = {
            0: "demand",
            1: "disabled",
            2: "auto"
        }
        target_type = type_map.get(self.combo_svc_type.currentIndex(), "demand")

        confirm = CustomConfirmDialog(
            self,
            title="Alterar Inicialização de Serviço",
            message=f"Deseja alterar a inicialização do serviço '{svc.display_name}' ({svc.name}) para '{target_type}'?\n\n"
                    "O estado anterior será registrado no Auto Recovery Center para reversão de 1 clique.",
            confirm_text="Confirmar Alteração",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            res = wb.configure_optional_service(svc.name, target_type, user_confirmed=True)
            if res.get("success"):
                show_toast(self, res.get("message"), "success")
                self._load_services_table()
            else:
                CustomMessageDialog(self, "Falha na Configuração", res.get("message"), dialog_type="error").exec()

    # =========================================================================
    # APLICAÇÃO E REVERSÃO DE PERFIS
    # =========================================================================
    def _apply_profile(self, profile_id: str):
        profile_info = wb.optimization_profiles.PROFILES_CATALOG.get(profile_id, {})
        confirm = CustomConfirmDialog(
            self,
            title=f"Aplicar {profile_info.get('name')}",
            message=f"{profile_info.get('description')}\n\n"
                    "Todas as configurações alteradas serão registradas no Auto Recovery Center com rollback disponível a qualquer momento.\n\n"
                    "Deseja prosseguir com a aplicação deste perfil?",
            confirm_text="Aplicar Perfil Agora",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            res = wb.apply_profile(profile_id, user_confirmed=True)
            if res.get("success"):
                OperationResultDialog(
                    self,
                    title="Perfil Aplicado com Sucesso",
                    message=f"O perfil {profile_info.get('name')} foi configurado com êxito.",
                    stats={
                        "Perfil Ativo": profile_id,
                        "Ações Concluídas": len(res.get("actions_completed", [])),
                        "Rollback ID": res.get("master_record_id", "OK"),
                        "Status": "Otimizado"
                    }
                ).exec()
                self.refresh_all_diagnostics()
                show_toast(self, f"Perfil {profile_id} ativo!", "success")
            else:
                CustomMessageDialog(self, "Falha ao Aplicar Perfil", res.get("message"), dialog_type="error").exec()

    def _run_before_after_comparison(self):
        """Coleta instantâneo atual e compara com o instantâneo de referência."""
        if not self.baseline_snapshot:
            self.baseline_snapshot = wb.take_system_snapshot()
            self.lbl_snapshot_text.setText(
                f"Ponto Inicial (Antes) registrado às {self.baseline_snapshot.timestamp}: "
                f"RAM Usada: {self.baseline_snapshot.ram_used_gb} GB ({self.baseline_snapshot.ram_percent}%) | "
                f"CPU: {self.baseline_snapshot.cpu_percent}% | Processos: {self.baseline_snapshot.process_count}."
            )
            show_toast(self, "Ponto de referência 'Antes' registrado!", "info")
            return

        after = wb.take_system_snapshot()
        delta = wb.compare_snapshots(self.baseline_snapshot, after, applied_operations=["Otimizações de Segundo Plano"])
        
        OperationResultDialog(
            self,
            title="Análise Comparativa Antes & Depois",
            message=delta["summary"],
            stats={
                "Memória Liberada": f"{delta['ram_diff_mb']} MB",
                "Variação de CPU": f"{delta['cpu_diff_pct']}%",
                "Diferença Processos": f"{delta['process_count_diff']}",
                "Recursos Reduzidos": f"{delta['features_reduced_count']}"
            }
        ).exec()

    def _handle_restore_all(self):
        confirm = CustomConfirmDialog(
            self,
            title="Restaurar Configurações Originais",
            message="Deseja reverter todas as modificações ativas realizadas pelo Windows Background Control?\n\n"
                    "O Auto Recovery Center restaurará os valores originais do Registro, políticas e serviços gravados no ledger.",
            confirm_text="Restaurar Tudo",
            cancel_text="Cancelar"
        )
        if confirm.exec():
            res = wb.background_recovery.restore_all_background_optimizations()
            if res.get("success"):
                show_toast(self, res.get("message"), "success")
                self.refresh_all_diagnostics()
            else:
                CustomMessageDialog(self, "Aviso de Restauração", res.get("message"), dialog_type="warning").exec()
