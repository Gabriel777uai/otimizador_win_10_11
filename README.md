# ALTUS PC OPTIMIZER
### Sistema Profissional de Otimização, Diagnóstico e Manutenção do Windows

![Versão](https://img.shields.io/badge/versão-3.0.0--Pro-00d2ff.svg)
![Plataforma](https://img.shields.io/badge/plataforma-Windows%2010%20%7C%20Windows%2011-0078d4.svg)
![Segurança](https://img.shields.io/badge/segurança-Safety%20Manager%20Central-00e676.svg)
![Testes](https://img.shields.io/badge/testes-30%20passed%20(100%25)-brightgreen.svg)
![Empacotamento](https://img.shields.io/badge/executável-Único%20.EXE%20(Standalone)-ffd600.svg)

---

## 1. Visão Geral e Princípios Técnicos

O **ALTUS PC OPTIMIZER** é uma solução de engenharia de software desktop projetada especificamente para Windows 10 e Windows 11. Desenvolvido em Python com interface moderna em **PySide6** e empacotado em um **executável único independente (`dist/ALTUS-PC-OPTIMIZER.exe`)**, o sistema combina diagnósticos reais de hardware, manutenção preventiva do sistema de arquivos, telemetria gráfica avançada (Intel PresentMon), monitoramento térmico, análise de estabilidade e recuperação de configurações.

### Princípios de Engenharia de Desempenho e Segurança
- **Segurança Centralizada e Inegociável (Safety Manager):** Nenhuma alteração crítica ocorre sem validação central de privilégios e confirmação explícita do usuário. Ações perigosas (como desativar antivírus/firewall/UAC, apagar Prefetch, limpar Registro ou usar prioridade Realtime) são bloqueadas na raiz.
- **Transparência de Métricas Reais:** Nenhuma métrica é inventada ou simulada. Métricas não disponíveis no hardware são apresentadas como "Não disponível".
- **Progresso Real e Assíncrono:** Todas as rotinas demoradas rodam em threads de segundo plano sem travar a interface gráfica, transmitindo progresso real item por item.
- **Reversibilidade de Alterações (Auto Recovery Center):** Todas as alterações em configurações de sistema (DNS, plano de energia, entradas de inicialização) geram um registro formal no livro-razão (`recovery_ledger.json`) permitindo rollback instantâneo a qualquer momento.

---

## 2. Estrutura e Arquitetura do Software

```text
ALTUS-PC-OPTIMIZER/
├── main.py                             # Ponto de entrada e tratamento com fallback de UI nativa
├── requirements.txt                    # Dependências do projeto (PySide6, psutil, platformdirs)
├── build.bat                           # Script de compilação PyInstaller com controle de processos
├── README.md                           # Documentação técnica oficial
│
├── src/
│   ├── core/                           # Núcleo de segurança, ciclo de vida e recuperação
│   │   ├── application.py              # Ciclo de vida da aplicação e checagem de recuperação
│   │   ├── safety_manager.py           # Registro central de operações autorizadas e níveis de risco
│   │   ├── recovery_manager.py         # Livro-razão (Ledger) e estratégias automatizadas de rollback
│   │   ├── progress_manager.py         # Gerenciador thread-safe de progresso real e cancelamento
│   │   ├── system_detection.py         # Telemetria rápida sem shell (CPU, GPU, VRAM real, discos, SO)
│   │   ├── permissions.py              # Auditoria de privilégios UAC / Administrador
│   │   └── config_manager.py           # Persistência de configurações em settings.json
│   │
│   ├── modules/                        # Módulos de serviço especializados
│   │   ├── cleaning/                   # Limpeza inteligente e armazenamento
│   │   │   ├── temp_cleaner.py         # Limpeza com validação TOCTOU e detecção lstat
│   │   │   ├── thumbnail_cleaner.py    # Limpeza segura de cache de miniaturas
│   │   │   ├── windows_update_cleaner.py # Gestão estrita de serviços e cache SoftwareDistribution
│   │   │   ├── dns_cache_cleaner.py    # Limpeza de cache local DNS
│   │   │   └── storage_analyzer.py     # Auditoria de unidades e esvaziamento seguro da Lixeira
│   │   │
│   │   ├── performance/                # NOVO: Performance Lab e benchmarks reais
│   │   │   ├── presentmon_collector.py # Integração oficial com telemetria Intel PresentMon (ETW)
│   │   │   ├── metrics_calculator.py   # Cálculos rigorosos de FPS Médio, 1% Low, 0.1% Low e Pacing
│   │   │   ├── benchmark_manager.py    # Histórico de benchmarks e comparativo de deltas antes/depois
│   │   │   └── report_exporter.py      # Exportação de relatórios em CSV e HTML
│   │   │
│   │   ├── gaming/                     # Otimização para jogos e Smart Game Session
│   │   │   ├── game_optimizer.py       # SmartGameSession com proteção de PID e respeito à bateria
│   │   │   ├── game_detection.py       # Localização de jogos Steam e processos em execução
│   │   │   ├── startup_optimizer.py    # Reativação de inicializadores com preservação de tipos de registro
│   │   │   ├── performance_monitor.py  # Diagnóstico técnico de gargalos
│   │   │   └── graphics_settings.py    # Modos de exibição e integração com o Windows
│   │   │
│   │   ├── thermal/                    # NOVO: Thermal Guard e monitoramento térmico
│   │   │   └── thermal_manager.py      # Sensores NVIDIA-SMI, WMI, clocks e análise de throttling
│   │   │
│   │   ├── network/                    # Diagnóstico e conectividade
│   │   │   ├── network_analyzer.py     # Diagnóstico de interfaces, ping e jitter com progresso
│   │   │   ├── dns_optimizer.py        # Configuração com rollback e backup exato de DNS estático/DHCP
│   │   │   └── network_repair.py       # Renovação DHCP e redefinição de catálogo Winsock
│   │   │
│   │   ├── windows/                    # Confiabilidade e agendador
│   │   │   ├── reliability_analyzer.py # NOVO: Varredura de eventos de falhas no Event Log do Windows
│   │   │   ├── task_scheduler.py       # NOVO: Integração oficial com o Windows Task Scheduler (schtasks)
│   │   │   ├── disk_health.py          # Identificação precisa de hardware para Optimize-Volume (C:)
│   │   │   └── system_health.py        # Ferramentas nativas SFC /scannow e DISM /RestoreHealth
│   │   │
│   │   └── reports/                    # Auditoria e histórico de operações
│   │       ├── report_generator.py
│   │       └── history_manager.py
│   │
│   ├── interface/                      # Interface gráfica PySide6 (12 Seções Especializadas)
│   │   ├── main_window.py              # Janela principal com 12 páginas navegáveis
│   │   ├── splash_screen.py            # Tela de carregamento tecnológica com etapas
│   │   ├── dashboard.py                # Painel de controle e monitoramento sob demanda
│   │   ├── cleaning_page.py            # Limpeza inteligente com workers assíncronos
│   │   ├── gaming_page.py              # Smart Game Session e biblioteca de jogos
│   │   ├── performance_lab_page.py     # NOVO: Telemetria PresentMon e comparação de benchmarks
│   │   ├── thermal_guard_page.py       # NOVO: Telemetria térmica de CPU/GPU e diagnóstico de throttling
│   │   ├── network_page.py             # Diagnóstico de ping, configuração DNS e reparos
│   │   ├── system_page.py              # Otimização de volume (TRIM/Defrag) e SFC/DISM
│   │   ├── startup_page.py             # Gerenciamento e reativação de programas de inicialização
│   │   ├── auto_recovery_page.py       # NOVO: Central de restauração e rollback de modificações
│   │   ├── reliability_page.py         # NOVO: Linha do tempo de falhas e estabilidade do SO
│   │   ├── reports_page.py             # Trilha de auditoria e logs detalhados
│   │   ├── settings_page.py            # Preferências de interface e agendamento Task Scheduler
│   │   │
│   │   └── dialogs/custom_dialogs.py   # Diálogos modais padronizados, progresso real e toasts
│   │
│   └── utils/                          # Utilitários de sistema e I/O seguro
│       ├── command_runner.py
│       ├── validators.py               # Proteção TOCTOU e confinamento em raízes autorizadas
│       ├── file_operations.py          # Detecção de reparse points (lstat) e limpeza segura
│       └── logger.py                   # Registro de logs em %LOCALAPPDATA%
│
├── tests/                              # Suíte completa com 30 testes automatizados
│   ├── test_cleaning.py
│   ├── test_network.py
│   ├── test_safety.py
│   ├── test_system_detection.py
│   ├── test_ui_dialogs.py
│   ├── test_recovery_and_rollback.py   # NOVO: Testes de rollback e integridade de DNS
│   ├── test_windows_update_and_services.py # NOVO: Testes de tolerância a falhas em serviços
│   ├── test_reparse_and_safety_advanced.py # NOVO: Testes de links simbólicos e TOCTOU
│   └── test_performance_and_gaming.py  # NOVO: Testes de métricas e sessões de jogos
│
└── dist/
    └── ALTUS-PC-OPTIMIZER.exe          # Executável único compilado e testado
```

---

## 3. Funcionalidades Detalhadas por Módulo

### 3.1 Safety Manager Centralizado
- Classificação estrita em 4 níveis: `LEVEL_1_SAFE`, `LEVEL_2_CONTROLLED`, `LEVEL_3_ADVANCED` e `FORBIDDEN`.
- Lista negra irrevogável para rotinas nocivas ao Windows.
- O nível de risco e a exigência de privilégios de cada operação são determinados pelo registro central oficial, impedindo que chamadores subestimem permissões.

### 3.2 Performance Lab & PresentMon
- Integração de telemetria baseada em ETW via Intel PresentMon.
- Cálculo de métricas da indústria de jogos:
  - **FPS Médio:** Taxa média de quadros por segundo.
  - **1% Low:** Média dos piores 1% de quadros, revelando micro-engasgos (stuttering).
  - **0.1% Low:** Quedas extremas de taxa de quadros.
  - **Frametime Médio e Percentis (P50, P95, P99):** Consistência na entrega de quadros.
- Comparação direta de benchmarks: grava sessões "Linha de Base" e "Com Otimização ALTUS" e calcula variações percentuais.
- Exportação em formato de relatório técnico estruturado em **CSV** e **HTML estilizado**.

### 3.3 Smart Game Session
- Identificação precisa de jogos em execução por nome de processo, PID e `create_time` (evitando colisão de PIDs reciclados pelo Windows).
- Proteção de bateria: NUNCA força plano de alto desempenho caso o notebook esteja na bateria.
- Elevação controlada para prioridade `AboveNormal` (NUNCA `Realtime`).
- Rastreamento de processos concorrentes que consumam CPU de forma anômala em segundo plano.
- Restauração automática do plano de energia e prioridades no encerramento da sessão.

### 3.4 Thermal Guard & Sensores
- Leitura direta via **NVIDIA-SMI** (temperatura de GPU, clock em MHz, consumo em Watts e velocidade de ventoinhas).
- Frequências reais de operação de CPU via contadores do subsistema Windows.
- Diagnóstico de Thermal Throttling baseado em evidências: exige temperatura crítica combinada com queda acentuada de clock. Não diagnostica throttling apenas por aquecimento natural.

### 3.5 Auto Recovery Center
- Registro de todas as modificações em livro-razão estruturado (`recovery_ledger.json`).
- Reversão garantida para:
  - **Servidores DNS:** restaura o modo exato original (estático com a lista ordenada de IPs ou automático DHCP).
  - **Planos de Energia:** restaura o GUID do esquema anterior.
  - **Inicializadores:** reativa valores com o tipo original no Registro (`REG_SZ` / `REG_EXPAND_SZ`) ou restaura atalhos da quarentena.
- Verificação no início da aplicação: detecta e reverte automaticamente operações que tenham ficado pendentes por encerramento súbito do computador.

### 3.6 Windows Reliability Analyzer
- Consulta estruturada aos logs oficiais do Windows (`System` e `Application`) dos últimos 7 dias.
- Categorização de incidentes: falhas de aplicativos (Event ID 1000/1002), desligamentos inesperados (Kernel-Power 41/6008), falhas de drivers de vídeo (TDR) e erros de disco.
- Apresenta gravidade, impacto técnico no SO e recomendações práticas.

### 3.7 Agendamento no Windows Task Scheduler
- Criação e edição de tarefas oficiais no Agendador de Tarefas do Windows (`schtasks.exe`).
- Permite configurar dia da semana e horário.
- A tarefa agendada executa em modo silencioso (`--auto-maintenance`), limitada estritamente a operações seguras de Nível 1.

---

## 4. Resultados da Suíte de Testes Automatizados

Execução validada no ambiente Windows com 30 testes unitários e de integração:

```text
============================= test session starts =============================
platform win32 -- Python 3.14.0, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\wamp64\www\otimizador_win_10_11
plugins: anyio-4.12.1, platformdirs-4.14.3
collected 30 items

tests/test_cleaning.py::test_safe_temp_path_validation PASSED            [  3%]
tests/test_cleaning.py::test_temp_cleanup_dry_run PASSED                 [  6%]
tests/test_cleaning.py::test_clean_files_safely_dry_run PASSED           [ 10%]
tests/test_network.py::test_ipv4_validation PASSED                       [ 13%]
tests/test_network.py::test_dns_profiles_integrity PASSED                [ 16%]
tests/test_network.py::test_internet_reachability PASSED                 [ 20%]
tests/test_performance_and_gaming.py::test_benchmark_metrics_calculations PASSED [ 23%]
tests/test_performance_and_gaming.py::test_benchmark_comparison_deltas PASSED [ 26%]
tests/test_performance_and_gaming.py::test_thermal_throttling_requires_evidence PASSED [ 30%]
tests/test_performance_and_gaming.py::test_smart_game_session_protects_pid_reuse PASSED [ 33%]
tests/test_recovery_and_rollback.py::test_recovery_operation_registration PASSED [ 36%]
tests/test_recovery_and_rollback.py::test_rollback_dns_static_exact_servers PASSED [ 40%]
tests/test_recovery_and_rollback.py::test_rollback_dns_dhcp_mode PASSED  [ 43%]
tests/test_recovery_and_rollback.py::test_interrupted_operation_auto_recovery_on_startup PASSED [ 46%]
tests/test_reparse_and_safety_advanced.py::test_reparse_point_detection_via_attributes PASSED [ 50%]
tests/test_reparse_and_safety_advanced.py::test_validate_file_blocks_paths_outside_authorized_roots PASSED [ 53%]
tests/test_reparse_and_safety_advanced.py::test_validate_file_blocks_recent_files_toctou PASSED [ 56%]
tests/test_safety.py::test_forbidden_operations_are_blocked PASSED       [ 60%]
tests/test_safety.py::test_safe_operations_allowed PASSED                [ 63%]
tests/test_safety.py::test_controlled_operations_require_confirmation PASSED [ 66%]
tests/test_system_detection.py::test_cpu_detection PASSED                [ 70%]
tests/test_system_detection.py::test_memory_detection PASSED             [ 73%]
tests/test_system_detection.py::test_os_detection PASSED                 [ 76%]
tests/test_system_detection.py::test_full_system_snapshot PASSED         [ 80%]
tests/test_ui_dialogs.py::test_progress_reporter_lifecycle PASSED        [ 83%]
tests/test_ui_dialogs.py::test_progress_cancellation PASSED              [ 86%]
tests/test_windows_update_and_services.py::test_cleanup_aborted_when_update_in_progress PASSED [ 90%]
tests/test_windows_update_and_services.py::test_cleanup_aborted_when_reboot_pending PASSED [ 93%]
tests/test_windows_update_and_services.py::test_service_stop_failure_aborts_cleanup PASSED [ 96%]
tests/test_windows_update_and_services.py::test_services_always_restored_in_finally PASSED [100%]

============================= 30 passed in 9.81s ==============================
```

---

## 5. Como Executar e Compilar

### 5.1 Executável Standalone (Sem Necessidade de Python)
O executável principal está pronto para uso em:
```text
dist/ALTUS-PC-OPTIMIZER.exe
```
Basta dar um duplo clique para abrir. Para funcionalidades que alteram parâmetros globais de rede e serviços (Níveis 2 e 3), execute o aplicativo com "Executar como Administrador".

### 5.2 Execução via Código-Fonte (Desenvolvimento)
```powershell
pip install -r requirements.txt
python main.py
```

### 5.3 Compilação com PyInstaller
Para gerar novamente o executável único:
```powershell
.\build.bat
```
O script encerra instâncias abertas automaticamente para liberar bloqueios de arquivo e compila o binário otimizado.

---

## 6. Limitações Conhecidas e Comportamentos Esperados

1. **Sensores de Temperatura de CPU em Placas-Mãe Genéricas:** Algumas placas-mãe não expõem as interfaces ACPI padrão (`MSAcpi_ThermalZoneTemperature`) para aplicações em modo usuário sem drivers proprietários de kernel. Por princípio de segurança, o ALTUS não instala drivers de kernel de terceiros não assinados; nestes casos específicos, a temperatura é apresentada honestamente como "Não disponível".
2. **Reversão de Operações Destrutivas:** Limpezas de arquivos temporários e esvaziamento da Lixeira removem dados descartados permanentemente. O Auto Recovery Center gerencia reversões de configurações do sistema operacional (DNS, energia, inicializadores), nunca a restauração de arquivos deliberadamente apagados.
3. **Captura de Telemetria de Jogos em DirectX 9 Muito Antigos:** O PresentMon requer suporte a ETW e subsistemas gráficos modernos (DirectX 11, DirectX 12 ou Vulkan). Jogos legados (OpenGL ou DirectX 8/9 puros) podem requerer adaptadores ou fornecer apenas dados de recursos de hardware do Windows.
4. **Notebooks em Bateria:** O ALTUS não força o plano de Alto Desempenho enquanto o notebook estiver desconectado da tomada, prevenindo consumo acelerado da bateria.

---

## 7. Dependências e Licenças de Terceiros

- **Python:** Python Software Foundation License.
- **PySide6 (Qt for Python):** LGPLv3 / Commercial.
- **psutil:** BSD-3-Clause License.
- **platformdirs:** MIT License.
- **Intel PresentMon (Opcional para ETW):** MIT / Apache 2.0 License.
