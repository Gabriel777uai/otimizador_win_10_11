# Windows Support Toolkit

**Ferramenta Profissional de Suporte Técnico e Manutenção para Windows 10 e Windows 11**  
**Desenvolvido por:** `Gabriel Souza Barros`  
**Versão:** `1.0`  
**Arquivo Principal:** `Windows-Support-Toolkit.ps1`  

---

## 1. Visão Geral e Filosofia do Projeto

O **Windows Support Toolkit** é uma ferramenta profissional desenvolvida especificamente para técnicos de suporte de TI, analistas de Help Desk, administradores de infraestrutura e profissionais de manutenção.

Diferente de scripts genéricos da internet, esta ferramenta:
- **Não executa comandos agressivos às cegas.**
- **Não utiliza falsas otimizações** (como limpadores de registro mágicos, destruição de cache de memória útil ou scripts que desativam serviços essenciais do Windows).
- **Protege a integridade do sistema operacional**, respeitando diretrizes oficiais da Microsoft.
- **Possui arquitetura 100% modular**, com um menu interativo baseado em `switch`, além de suporte a execução via parâmetros de linha de comando (`CLI`).
- **Gera auditoria completa e automática** por meio de transcrições de log e relatórios técnicos em formatos texto (`.txt`) e web responsivo (`.html`).

---

## 2. Requisitos e Compatibilidade

| Requisito | Detalhe |
|---|---|
| **Sistemas Operacionais** | Windows 10 (versão 1809 ou superior) e Windows 11 (todas as compilações, incluindo 24H2 Copilot+ PC) |
| **Arquiteturas** | x64 (64 bits), x86 (32 bits) e ARM64 |
| **Edições Suportadas** | Home, Pro, Enterprise e Education |
| **Versão do PowerShell** | **Windows PowerShell 5.1** nativo (compatível também com PowerShell 7.x) |
| **Privilégios** | **Administrador local** (elevação automática via UAC com `RunAs`) |

---

## 3. Como Executar como Administrador

Para executar o Toolkit com privilégios completos de diagnóstico e manutenção:

1. Abra o menu Iniciar, digite `powershell` e selecione **"Executar como Administrador"**.
2. Navegue até a pasta do projeto:
   ```powershell
   cd c:\wamp64\www\project-agente-ia
   ```
3. Execute o script principal:
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File .\Windows-Support-Toolkit.ps1
   ```

### Detecção e Auto-Elevação Automática:
Caso o operador execute o script sem privilégios administrativos (por exemplo, clicando duas vezes ou a partir de um terminal comum), a ferramenta detectará a ausência de direitos elevados, notificará o operador na tela e solicitará autorização para reiniciar a si mesma automaticamente com privilégios de Administrador (`UAC RunAs`).

---

## 4. Modos de Execução via Linha de Comando (CLI)

Além do menu interativo, o script pode ser executado diretamente em rotinas de suporte rápido, automações corporativas ou chamadas remotas:

```powershell
# Modo Padrão (Menu Interativo 30 Opções)
.\Windows-Support-Toolkit.ps1

# Modo Diagnóstico Completo (Sem alterações no sistema)
.\Windows-Support-Toolkit.ps1 -Mode Diagnose

# Modo Suporte Rápido (Diagnóstico expresso não destrutivo + Relatório)
.\Windows-Support-Toolkit.ps1 -Mode QuickSupport

# Modo Limpeza Segura (Arquivos temporários e cache DNS)
.\Windows-Support-Toolkit.ps1 -Mode Cleanup

# Modo Verificação Antimalware (Atualiza Defender e dispara Quick Scan)
.\Windows-Support-Toolkit.ps1 -Mode MalwareScan

# Modo Manutenção Completa (Executa o fluxo de 18 fases estruturadas)
.\Windows-Support-Toolkit.ps1 -Mode FullMaintenance

# Modo Exportação de Relatório (Gera todos os arquivos TXT e HTML)
.\Windows-Support-Toolkit.ps1 -Mode Report

# Simulação / Teste Seguro (CmdletBinding ShouldProcess)
.\Windows-Support-Toolkit.ps1 -Mode Cleanup -WhatIf
```

---

## 5. Descrição Detalhada dos Módulos do Menu

A ferramenta conta com 30 módulos controlados via menu principal com estrutura `switch ($opcao)`:

```
======================================================================
 WINDOWS SUPPORT TOOLKIT
 Ferramenta Profissional de Suporte Windows
 Desenvolvido por: Gabriel Souza Barros
 Versão: 1.0
======================================================================
 COMPUTADOR : TI-004  |  USUÁRIO : BRASILC\suporte
 WINDOWS    : Microsoft Windows 10 Pro (64 bits)  |  BUILD   : 19045
 PROCESSADOR: AMD Ryzen 5 4500 6-Core Processor
 MEMÓRIA    : 15.8 GB Total (4.5 GB Livre / 71.5% Usado)
 UPTIME     : 9d 10h 15m
----------------------------------------------------------------------
 [ 1 ] Diagnóstico completo do computador
 [ 2 ] Diagnóstico e saúde dos discos
 [ 3 ] Verificação CHKDSK (Scan / Spotfix / F / R)
 [ 4 ] Reparação de imagem DISM (Check / Restore / Component)
 [ 5 ] Reparação de arquivos de sistema SFC (/scannow)
 [ 6 ] Limpeza de arquivos temporários
 [ 7 ] Limpeza de componentes do Windows (WinSxS)
 [ 8 ] Limpeza da Lixeira
 [ 9 ] Limpeza de cache DNS
 [10 ] Otimização de SSD/HDD (TRIM / Defrag Inteligente)
 [11 ] Diagnóstico de memória RAM e processos
 [12 ] Diagnóstico de CPU e GPU
 [13 ] Diagnóstico de programas de inicialização
 [14 ] Diagnóstico de serviços do Windows
 [15 ] Diagnóstico de eventos do Windows (Event Viewer)
 [16 ] Diagnóstico de conectividade e rede
 [17 ] Reparação avançada de rede (Winsock / TCP-IP Reset)
 [18 ] Atualização de assinaturas do Defender
 [19 ] Verificação rápida do Defender (Quick Scan)
 [20 ] Verificação completa de malware (Full Scan)
 [21 ] Microsoft Defender Offline (Reboot WDO)
 [22 ] Histórico de ameaças detectadas pelo Defender
 [23 ] Limpeza profunda controlada
 [24 ] Diagnóstico do Windows Update
 [25 ] Exportar relatório completo (TXT e HTML)
 [26 ] Diagnóstico de recursos de IA do Windows
 [27 ] Gerenciar / Desativar recursos de IA (com backup)
 [28 ] Otimização geral segura
 [29 ] Criar ponto de restauração do sistema
 [30 ] Executar manutenção completa recomendada (18 Fases)
 [ 0 ] Sair do Toolkit
----------------------------------------------------------------------
```

### [1] Diagnóstico Completo do Computador (`Get-SystemDiagnostic`)
Coleta informações nativas via WMI/CIM sobre placa-mãe, processador, memória RAM, slots físicos, BIOS, versão do kernel, arquitetura, usuário atual e tempo de uptime.

### [2] Diagnóstico e Saúde dos Discos (`Get-DiskHealth`)
Exibe discos físicos via `Get-PhysicalDisk`, volumes lógicos, espaço livre em GB e percentual, além de consultar os contadores de confiabilidade de hardware `Get-StorageReliabilityCounter` (temperatura, horas de uso, desgaste de NAND, erros de leitura/gravação não corrigidos).

### [3] Verificação CHKDSK (`Invoke-DiskCheck`)
Oferece quatro modalidades de verificação:
- **Online segura (`/scan`):** Somente leitura, sem desmontagem de volume e sem travar o sistema.
- **Spotfix (`/spotfix`):** Correção rápida de falhas identificadas previamente pelo NTFS.
- **Correção estrutural (`/f`):** Correção do sistema de arquivos, agendada para a próxima reinicialização se o disco estiver em uso.
- **Varredura profunda (`/f /r`):** Leitura exaustiva de superfície para recuperação de setores defeituosos (operação demorada com dupla confirmação obrigatória).

### [4] Reparação de Imagem DISM (`Repair-WindowsImage`)
Permite inspecionar o flag de integridade (`/CheckHealth`), escanear o repositório de componentes (`/ScanHealth`), reparar arquivos corrompidos a partir do Windows Update (`/RestoreHealth`) e executar limpeza oficial de componentes (`/StartComponentCleanup`). A opção `/ResetBase` exige confirmação dupla por ser irreversível.

### [5] Reparação SFC (`Repair-SystemFiles`)
Executa `sfc /scannow` em primeiro plano e analisa detalhadamente o código de saída e os logs de integridade. Identifica se não houve violações, se arquivos foram recuperados, se existem corrupções irrecuperáveis (indicando necessidade de DISM) ou se há reinicialização pendente.

### [6] Limpeza de Temporários (`Clear-SystemJunk`)
Calcula previamente o tamanho e a quantidade de arquivos na pasta Temp do Usuário, Temp do Windows e cache de miniaturas. Remove apenas arquivos não bloqueados e executa `cleanmgr /VERYLOWDISK`. Calcula e relata exatamente quanto espaço foi liberado na unidade C:.

### [7] Limpeza de Componentes do Windows (`Clear-ComponentStore`)
Executa `DISM.exe /Online /Cleanup-Image /StartComponentCleanup` para liberar espaço ocupado por atualizações antigas substituídas no WinSxS de maneira oficial e segura.

### [8] Limpeza da Lixeira (`Clear-RecycleBinSecure`)
Esvazia de forma controlada as lixeiras de todos os volumes fixos com confirmação prévia.

### [9] Limpeza de Cache DNS (`Clear-NetworkCache`)
Executa `ipconfig /flushdns` para liberar registros corrompidos de resolução de nomes.

### [10] Otimização de SSD/HDD (`Optimize-StorageVolume`)
Detecta automaticamente a mídia física da unidade:
- **SSD:** Executa comando **TRIM (`-ReTrim`)**, liberando blocos sem submeter a memória flash a desgastes desnecessários.
- **HDD Mecânico:** Aplica desfragmentação controlada (`-Defrag`).
- **Garantia:** O Toolkit nunca força desfragmentação tradicional em unidades SSD.

### [11] Diagnóstico de Memória RAM (`Get-MemoryDiagnostic`)
Exibe memória instalada, disponível, percentual de uso, slots ocupados, velocidade e o Top 25 processos com maior consumo (Working Set). Informa alertas para processos usando mais de 20% da memória física. Inclui diagnóstico do Pagefile (arquivo de paginação) e esclarece tecnicamente por que "limpadores de RAM" artificiais são nocivos ao Windows.

### [12] Diagnóstico de CPU e GPU (`Get-HardwareDiagnostic`)
Analisa núcleos, threads, clock e carga do processador. Lista os 20 processos com maior tempo de CPU acumulado. Detalha placas de vídeo instaladas, versões dos drivers e memória de vídeo dedicada (VRAM). Permite disparar o diagnóstico energético `powercfg /energy`.

### [13] Diagnóstico de Inicialização (`Get-StartupPrograms`)
Audita programas que iniciam com o Windows através de classes WMI e chaves de registro (`HKLM\Run` e `HKCU\Run`).

### [14] Diagnóstico de Serviços do Windows (`Get-ServiceDiagnostic`)
Permite filtrar serviços em execução, parados ou com falha. Destaca serviços com inicialização automática que se encontram parados para rápida investigação de suporte. Não contém desativações em massa.

### [15] Diagnóstico de Eventos do Windows (`Get-SystemEvents`)
Varre os logs de eventos `System` e `Application` nos últimos 7 dias buscando eventos de nível Crítico (Level 1) e Erro (Level 2). Apresenta estatísticas de origens, IDs mais frequentes e detalhes das ocorrências mais recentes.

### [16] Diagnóstico de Rede (`Test-NetworkHealth`)
Lista adaptadores ativos com IPv4, máscara, gateway, DNS e DHCP. Realiza testes de ping ICMP para o Google DNS (8.8.8.8) e Cloudflare (1.1.1.1), testa resolução de nomes e permite traceroute sob demanda.

### [17] Reparação Avançada de Rede (`Repair-NetworkStack`)
Redefine o catálogo Winsock (`netsh winsock reset`), reinstala a pilha TCP/IP (`netsh int ip reset`) e limpa o DNS. Exige dupla confirmação e alerta sobre reinicialização necessária.

### [18] Atualização do Microsoft Defender (`Update-Defender`)
Força a sincronização e download das últimas assinaturas de vírus e spyware da Microsoft via PowerShell e MpCmdRun.

### [19] Verificação Rápida do Defender (`Start-QuickMalwareScan`)
Dispara o scan rápido do Microsoft Defender nos setores críticos e memória.

### [20] Verificação Completa de Malware (`Start-FullMalwareScan`)
Dispara o exame detalhado de todos os arquivos do disco. Emite aviso de consumo de tempo e recursos com confirmação dupla.

### [21] Microsoft Defender Offline (`Start-DefenderOfflineScan`)
Configura e dispara a verificação em ambiente isolado antes da carga do kernel (`Start-MpWDOScan`). **Avisa com destaque sobre o reinício imediato da máquina e solicita confirmação.**

### [22] Histórico de Ameaças (`Get-MalwareHistory`)
Consulta `Get-MpThreatDetection` e `Get-MpThreat` para auditar vírus, malwares ou trojans já bloqueados ou detectados.

### [23] Limpeza Profunda Controlada (`Invoke-DeepClean`)
Agrupa limpeza de temporários, limpeza de componentes WinSxS, esvaziamento de lixeira, limpeza de DNS e utilitário `cleanmgr`. Permite também limpeza seletiva de logs antigos e reset do cache da Windows Store (`wsreset`).

### [24] Diagnóstico do Windows Update (`Get-WindowsUpdateDiagnostic`)
Audita os serviços vitais (`wuauserv`, `bits`, `cryptsvc`, `dosvc`) e lista os últimos 15 HotFixes/KB instalados com respectivas datas.

### [25] Exportar Relatório Completo (`Export-SupportReport`)
Gera a pasta `SupportReports\YYYY-MM-DD_HH-mm-ss` contendo 10 relatórios técnicos detalhados em `.txt` mais o relatório corporativo moderno `SupportReport.html`.

### [26] Diagnóstico de Recursos de IA do Windows (`Get-WindowsAiDiagnostic`)
Identifica se a máquina roda Windows 11 24H2 Copilot+ PC (Build >= 26100), audita pacotes AppX do Copilot, verifica presença do recurso opcional Windows Recall e inspeciona políticas de registro do Click to Do e Paint Cocreator.

### [27] Gerenciamento e Desativação de IA (`Manage-WindowsAiFeatures`)
Permite desinstalar pacotes AppX do Copilot, desativar o Windows Recall, bloquear o Click to Do e bloquear o Cocreator do Paint via políticas de grupo locais. Realiza backup automático em formato JSON antes de qualquer alteração no registro e permite restauração com um clique.

### [28] Otimização Geral Segura (`Invoke-SafeOptimization`)
Rotina segura composta por 11 passos homologados: ponto de restauração, análise de disco, limpeza de temporários, DISM CheckHealth, SFC scannow, atualização do Defender, TRIM/Defrag inteligente, limpeza de DNS e emissão de relatório.

### [29] Criar Ponto de Restauração (`New-SupportRestorePoint`)
Cria um ponto de restauração do sistema denominado `"Windows Support Toolkit - Antes da Manutencao"`. Detecta e avisa claramente caso a Proteção do Sistema esteja desativada na unidade C:.

### [30] Manutenção Completa Recomendada (`Invoke-FullMaintenance`)
Executa o fluxo de manutenção preventiva em 18 fases estruturadas, gerando auditoria técnica de início ao fim.

---

## 6. Operações Agressivas e Operações que Exigem Reinicialização

O Toolkit possui regras estritas de segurança para proteger os dados do cliente:

| Operação | Exige Reinicialização? | Nível de Risco | Confirmação Exigida | Motivo Técnico |
|---|---|---|---|---|
| **CHKDSK /f ou /f /r** | Sim (ao reiniciar) | Médio / Alto | Sim / Dupla | O volume de sistema não pode ser desmontado com o Windows ativo. |
| **DISM /ResetBase** | Não (mas impede rollback) | Alto | **Dupla ("CONFIRMAR")** | Remove a base de desinstalação de atualizações antigas. |
| **Microsoft Defender Offline** | **Sim (Imediato)** | Médio | **Dupla ("CONFIRMAR")** | Reinicia imediatamente para subir imagem WinPE antimalware. |
| **Reparação de Rede (Reset)** | Sim (Recomendado) | Médio | **Dupla ("CONFIRMAR")** | Reinicia sockets do kernel e drivers de interface de rede. |
| **Desativação de Recall** | Sim (Recomendado) | Baixo | **Dupla ("CONFIRMAR")** | Remoção de recurso opcional do kernel do Windows 11. |
| **Remoção de Pacote Copilot** | Não | Baixo | Sim | Desinstalação controlada via AppX Package Manager. |

---

## 7. Estrutura de Arquivos e Pastas Geradas

A ferramenta gera automaticamente uma estrutura limpa e organizada no diretório onde for executada:

```
project-agente-ia/
│
├── Windows-Support-Toolkit.ps1   # Script principal do Toolkit
├── README.md                      # Manual completo de operação
├── COMMAND-REFERENCE.md           # Referência técnica de comandos e cmdlets
│
├── Logs/                          # Histórico de transcrições de execução
│   └── Support_YYYY-MM-DD_HH-mm-ss.log
│
├── Backups/                       # Backups JSON de políticas de IA e registro
│   └── WindowsAI_YYYY-MM-DD_HH-mm-ss.json
│
└── SupportReports/                # Relatórios técnicos gerados
    └── YYYY-MM-DD_HH-mm-ss/
        ├── System.txt
        ├── Hardware.txt
        ├── Storage.txt
        ├── Windows.txt
        ├── Defender.txt
        ├── Network.txt
        ├── Startup.txt
        ├── Services.txt
        ├── Events.txt
        ├── Processes.txt
        ├── Maintenance.log
        └── SupportReport.html     # Relatório interativo responsivo para clientes/auditoria
```

---

## 8. Como Restaurar Políticas de Recursos de IA

Antes de aplicar qualquer alteração em políticas de registro relacionadas ao Windows AI (Click to Do, Cocreator do Paint, etc.), a ferramenta captura o estado original e salva um arquivo em:
`.\Backups\WindowsAI_YYYY-MM-DD_HH-mm-ss.json`

### Para Restaurar:
1. Abra o Toolkit e selecione a opção **[27] Gerenciar / Desativar recursos de IA**.
2. Escolha a opção **[7] Restaurar Política a partir de Arquivo de Backup JSON**.
3. O sistema listará todos os backups encontrados com data e hora.
4. Digite o número correspondente ao backup e confirme a restauração.
5. O valor original do Registro será restaurado imediatamente.

---

## 9. Como Interpretar os Resultados Técnicos

A interface utiliza classificações de severidade padronizadas por cores para facilitar a triagem técnica:

- **`[OK]` (Verde):** Componente íntegro, comando finalizado com sucesso ou recurso operando dentro dos parâmetros de normalidade.
- **`[INFO]` (Ciano):** Mensagem de orientação, dados diagnósticos ou finalização de rotina de coleta.
- **`[WARNING]` (Amarelo):** Atenção requerida. Exemplos: espaço livre entre 10% e 20%, arquivos corrompidos que foram reparados com êxito pelo SFC, ou serviço Defender parado.
- **`[ERROR]` (Vermelho):** Falha na execução de um utilitário, violação de acesso ou erro de execução reportado pelo processo.
- **`[CRITICAL]` (Magenta):** Condição crítica que demanda ação imediata. Exemplos: disco com saúde física não saudável no S.M.A.R.T., espaço livre inferior a 10% na unidade C: ou corrupções irreversíveis no sistema de arquivos.

---

## 10. Créditos do Desenvolvedor

**Windows Support Toolkit**  
Desenvolvido por: **Gabriel Souza Barros**  
Versão: **1.0**  
Todos os direitos reservados. Uso corporativo, profissional e acadêmico autorizado.
