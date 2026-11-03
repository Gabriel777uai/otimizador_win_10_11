# AUDITORIA TÉCNICA E PLANO DE TRANSIÇÃO
## PROJETO: ALTUS PC OPTIMIZER
**Origem do Legado:** `Windows-Support-Toolkit.ps1` e `COMMAND-REFERENCE.md`  
**Autor Original:** Gabriel Souza Barros  
**Arquiteto Responsável pela Refatoração:** Equipe de Engenharia Altus  
**Data:** 03/11/2026  

---

## 1. Visão Geral da Auditoria

O projeto legado consistia em um script monolítico em PowerShell (`Windows-Support-Toolkit.ps1`) com aproximadamente 3.000 linhas, focado em suporte técnico e diagnóstico de TI corporativo.

Para a evolução no **ALTUS PC OPTIMIZER**, realizamos a auditoria técnica de todas as 48 rotinas e cmdlets presentes no repositório. O objetivo foi:
1. Validar comandos reais suportados pelo Windows 10 e Windows 11.
2. Identificar riscos operacionais, como comandos irreversíveis ou que causam interrupção abrupta de serviços.
3. Separar comandos em camadas de segurança (**Nível 1 - Seguro**, **Nível 2 - Controlado**, **Nível 3 - Avançado**, e **Proibidos**).
4. Migrar a lógica para serviços modulares em Python com APIs nativas do Windows (`win32api`, `psutil`, `ctypes`, WMI/CIM e utilitários oficiais).

---

## 2. Matriz Completa de Auditoria de Funcionalidades

| Funcionalidade Legada | Arquivo de Origem | Comando / Mecanismo Executado | Exige Admin? | Riscos Identificados | Reaproveitamento no ALTUS | Alterações e Refatoração Necessária |
| :--- | :--- | :--- | :---: | :--- | :---: | :--- |
| `Get-SystemDiagnostic` | `Windows-Support-Toolkit.ps1` | `Get-CimInstance Win32_OperatingSystem`, `Win32_Processor`, `Win32_PhysicalMemory` | Não | Nenhum. Leitura de hardware e SO. | **Sim** | Migrar para `src/core/system_detection.py` usando `psutil` + WMI/CIM nativo. Muito mais rápido e sem instanciar console PS. |
| `Get-DiskHealth` | `Windows-Support-Toolkit.ps1` | `Get-PhysicalDisk`, `Get-Volume`, `Get-StorageReliabilityCounter` | Leitura básica não; SMART sim | Falha em controladoras RAID ou discos USB em contadores SMART. | **Sim** | Migrar para `src/modules/windows/disk_health.py`. Detectar SSD/HDD e coletar saúde e espaço real por partição. |
| `Invoke-DiskCheck` | `Windows-Support-Toolkit.ps1` | `chkdsk.exe C: /scan`, `/spotfix`, `/f`, `/r` | Sim | `/f` e `/r` exigem reboot e podem levar horas travando o boot. | **Sim (Controlado)** | Manter `/scan` (somente leitura seguro) e disponibilizar agendamento consciente no módulo avançado. |
| `Repair-WindowsImage` | `Windows-Support-Toolkit.ps1` | `DISM.exe /Online /Cleanup-Image /ScanHealth` / `/RestoreHealth` | Sim | Consome alta CPU e banda se baixar do Windows Update. | **Sim (Avançado)** | Migrar para `src/modules/windows/system_health.py` como ação de Nível 3, com barra de progresso e execução assíncrona. |
| `DISM /ResetBase` | `Windows-Support-Toolkit.ps1` | `DISM.exe /StartComponentCleanup /ResetBase` | Sim | **IRREVERSÍVEL**: impede a desinstalação de atualizações prévias. | **NÃO (PROIBIDO)** | **REMOVIDO** conforme regras de segurança do projeto Altus. |
| `Repair-SystemFiles` | `Windows-Support-Toolkit.ps1` | `sfc.exe /scannow` | Sim | Leva de 5 a 15 min; pode requerer reboot. | **Sim (Avançado)** | Migrar para `src/modules/windows/system_health.py` executado em thread secundária com leitura de log `CBS.log`. |
| `Clear-SystemJunk` | `Windows-Support-Toolkit.ps1` | `Remove-Item` em `$env:TEMP`, `C:\Windows\Temp`, `thumbcache_*` | Não para User; Sim para Win | Deletar arquivos recém-criados em uso pode causar falha em instaladores. | **Sim (Refatorado)** | Migrar para `src/modules/cleaning/temp_cleaner.py` aplicando filtro de **idade (> 7 dias)**, sem travar processos e sem tocar em links simbólicos. |
| `Clear-RecycleBinSecure` | `Windows-Support-Toolkit.ps1` | `Clear-RecycleBin -Force` | Não | Perda acidental de arquivos não revisados pelo usuário. | **Sim (Controlado)** | Migrar para Nível 2; exibir tamanho ocupado e exigir confirmação explícita separada. |
| `cleanmgr.exe /VERYLOWDISK` | `Windows-Support-Toolkit.ps1` | Execução cega de cleanmgr | Sim | Comportamento não interativo sem seleção fina dos componentes. | **Substituído** | Substituído por análise granular nativa do Altus PC Optimizer. |
| `Clear-ComponentStore` | `Windows-Support-Toolkit.ps1` | `DISM /StartComponentCleanup` | Sim | Alto uso de disco durante execução. | **Sim (Controlado)** | Incluído no módulo avançado de manutenção do sistema com confirmação. |
| `Clear-NetworkCache` | `Windows-Support-Toolkit.ps1` | `ipconfig.exe /flushdns` | Não | Nenhum risco funcional; apenas limpa resolução temporária. | **Sim (Seguro)** | Migrar para `src/modules/cleaning/dns_cache_cleaner.py`. Apresentar saída real do Windows. |
| `Optimize-StorageVolume` | `Windows-Support-Toolkit.ps1` | `Optimize-Volume -ReTrim` / `-Defrag` | Sim | Desfragmentar SSD reduz vida útil das células NAND. | **Sim (Protegido)** | Validar obrigatoriamente se é SSD (executar apenas TRIM) ou HDD (desfragmentação autorizada). |
| `Get-MemoryDiagnostic` | `Windows-Support-Toolkit.ps1` | `Get-Process`, `Get-CimInstance Win32_OperatingSystem` | Não | Nenhum. | **Sim** | Migrar para `src/modules/gaming/performance_monitor.py` com métricas em tempo real (CPU, RAM por processo, paginação). |
| `Get-StartupPrograms` | `Windows-Support-Toolkit.ps1` | Consulta ao Registro `Run`, `RunOnce`, pasta Startup | Não | Nenhum na consulta; risco moderado ao desativar. | **Sim** | Migrar para `src/modules/gaming/startup_optimizer.py`. Permitir desativar/reativar com backup do valor original. |
| `Test-NetworkHealth` | `Windows-Support-Toolkit.ps1` | Ping 8.8.8.8, DNS Google, gateway | Não | Nenhum. | **Sim** | Migrar para `src/modules/network/network_analyzer.py` incluindo latência, perda de pacotes e jitter. |
| `Repair-NetworkStack` | `Windows-Support-Toolkit.ps1` | `netsh winsock reset`, `netsh int ip reset`, DHCP renew | Sim | Interrupção imediata de rede e necessidade mandatória de reboot. | **Sim (Avançado)** | Separar em ferramentas individuais: renovação de IP (Nível 2) e Winsock Reset (Nível 3 com duplo aviso). |
| `Windows Update Cache` | Incompleto no legado | Exclusão direta de arquivos em `SoftwareDistribution` | Sim | Danificar catálogo se serviços estiverem rodando ou atualizações em progresso. | **Implementação Nova Segura** | `src/modules/cleaning/windows_update_cleaner.py`: checa status do `wuauserv` e reboot pendente, para serviços, limpa apenas `Download` e restaura serviços. |
| `Gerenciador de Jogos & FPS` | Inexistente no legado | N/A | Não | Métricas falsas de FPS prejudicam a credibilidade da ferramenta. | **Nova Implementação** | `src/modules/gaming/`: detecção de bibliotecas Steam, processos de jogos ativos, modo Game Performance Mode, prioridade AboveNormal temporária e monitoramento real. |
| `Configuração de DNS` | Inexistente no legado | N/A | Sim | Perda de conexão caso servidor DNS seja inválido. | **Nova Implementação** | `src/modules/network/dns_optimizer.py`: Cloudflare (1.1.1.1), Google (8.8.8.8) com backup e restauração automática da configuração prévia. |
| `Safety Manager` | Parcialmente no legado | Verificações manuais de `$IsAdmin` | N/A | Falta de barramento unificado de autorização e rollback. | **Nova Arquitetura** | `src/core/safety_manager.py`: controle centralizado de níveis (1-Seguro, 2-Controlado, 3-Avançado, Proibidos). |

---

## 3. Diretrizes de Substituição e Eliminação

1. **Remoção de `/ResetBase`**: A remoção da base do WinSxS retira o direito do usuário reverter patches problemáticos da Microsoft. Fica estritamente banida.
2. **Remoção de scripts cegos de registro**: Nenhuma chave de registro será removida sem esquema de rollback e justificativa técnica documental.
3. **Substituição de chamadas PowerShell lentas**: Consultas de CPU, RAM, processos e rede que demoravam 2 a 4 segundos via PowerShell agora executam em microssegundos via chamadas diretas de C/Python (`psutil`, Win32 API).
4. **Isolamento de privilégios**: A aplicação principal roda em espaço de usuário comum. Tarefas administrativas utilizam subprocessos elevados via UAC ou verb `runas` com validação estrita de argumentos.

---
Documento auditado e validado para a construção do **ALTUS PC OPTIMIZER**.
