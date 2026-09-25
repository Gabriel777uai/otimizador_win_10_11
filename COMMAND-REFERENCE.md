# Referência Técnica de Comandos (Command Reference)

**Windows Support Toolkit**  
**Desenvolvido por:** `Gabriel Souza Barros`  
**Versão:** `1.0`  
**Documento Técnico de Auditoria de Comandos e Cmdlets**

---

## 1. Introdução

Este documento detalha todos os comandos nativos do sistema operacional, executáveis de diagnóstico e cmdlets do PowerShell utilizados internamente pelo **Windows Support Toolkit**. Cada comando possui sua finalidade explicada tecnicamente, justificando seu uso em ambiente de suporte de TI e infraestrutura corporativa.

---

## 2. Diagnóstico de Hardware e Sistema Operacional (CIM / WMI)

### `Get-CimInstance -ClassName Win32_OperatingSystem`
- **Finalidade:** Consulta informações detalhadas da instalação do Windows.
- **Propriedades Extraídas:** `Caption` (edição do Windows), `Version` (versão do kernel), `BuildNumber` (compilação do sistema), `OSArchitecture` (64 bits/32 bits/ARM), `LastBootUpTime` (data/hora da última inicialização para cálculo de uptime), `TotalVisibleMemorySize` e `FreePhysicalMemory`.
- **Vantagem Técnica:** Utiliza o protocolo WSMAN/CIM moderno em vez do obsoleto WMI DCOM (`Get-WmiObject`), garantindo rapidez e menor overhead.

### `Get-CimInstance -ClassName Win32_Processor`
- **Finalidade:** Extrai métricas do processador principal (CPU).
- **Propriedades Extraídas:** `Name` (modelo comercial), `NumberOfCores` (núcleos físicos), `NumberOfLogicalProcessors` (threads lógicos), `MaxClockSpeed` (frequência base em MHz) e `LoadPercentage` (carga instantânea).

### `Get-CimInstance -ClassName Win32_PhysicalMemory`
- **Finalidade:** Audita os módulos de memória física instalados nos slots da placa-mãe.
- **Propriedades Extraídas:** `DeviceLocator` (slot ocupado, ex: DIMM_A1), `Manufacturer` (fabricante do pente), `PartNumber` (código do módulo), `Capacity` (capacidade em bytes convertida para GB) e `Speed` (velocidade de operação em MHz).

### `Get-CimInstance -ClassName Win32_VideoController`
- **Finalidade:** Inspeciona os adaptadores de vídeo dedicados e integrados (GPU).
- **Propriedades Extraídas:** `Name` (modelo da placa de vídeo), `DriverVersion` (versão do driver de exibição instalado), `AdapterRAM` (quantidade de memória de vídeo VRAM dedicada) e `Status`.

### `Get-CimInstance -ClassName Win32_BIOS` e `Win32_BaseBoard`
- **Finalidade:** Identifica a placa-mãe e versão de firmware instalada para fins de inventário e suporte a drivers.
- **Propriedades Extraídas:** Fabricante, versão do SMBIOS, data da BIOS e modelo/revisão da placa-mãe.

---

## 3. Armazenamento e Diagnóstico de Discos

### `Get-PhysicalDisk`
- **Finalidade:** Identifica os discos físicos instalados diretamente na controladora SATA, NVMe ou SAS.
- **Propriedades Utilizadas:** `DeviceId`, `FriendlyName`, `MediaType` (SSD, HDD, SCM), `BusType` (NVMe, SATA, USB), `HealthStatus` (Healthy, Warning, Unhealthy) e `Size`.
- **Importância Técnica:** Permite ao Toolkit identificar com precisão matemática se a unidade é de estado sólido (SSD) ou mecânica (HDD), impedindo desfragmentações indevidas.

### `Get-Volume`
- **Finalidade:** Lista as partições lógicas formatadas e mapeadas no Windows.
- **Propriedades Utilizadas:** `DriveLetter`, `FileSystem` (NTFS, ReFS, FAT32), `Size`, `SizeRemaining` (espaço livre) e `HealthStatus`.
- **Regra de Alerta:** Emite `[WARNING]` para volumes com menos de 20% de espaço livre e `[CRITICAL]` para volumes com menos de 10%.

### `Get-StorageReliabilityCounter -PhysicalDisk $disk`
- **Finalidade:** Acessa contadores avançados de confiabilidade física da unidade de armazenamento (telemetria S.M.A.R.T. profunda).
- **Métricas Consultadas:**
  - `Temperature`: Temperatura operacional instantânea em graus Celsius.
  - `PowerOnHours`: Total de horas de funcionamento do disco.
  - `Wear`: Indicador percentual de desgaste de células NAND flash (específico para SSDs).
  - `ReadErrorsTotal` / `WriteErrorsTotal`: Erros totais de leitura e escrita.
  - `ReadErrorsUncorrected` / `WriteErrorsUncorrected`: Falhas irrecuperáveis de blocos de disco (indicador crítico de falha iminente).

---

## 4. Verificação de Disco e Reparo Estrutural (CHKDSK)

### `chkdsk.exe C: /scan`
- **Finalidade:** Executa varredura online do sistema de arquivos NTFS.
- **Comportamento:** Somente leitura (`read-only`), não desmonta o volume do sistema, não trava serviços e não requer reinicialização da máquina.
- **Aplicação:** Modo recomendado para diagnóstico inicial e preventivo.

### `chkdsk.exe C: /spotfix`
- **Finalidade:** Aplica correções rápidas pontuais que o Windows já registrou internamente no diário de integridade.
- **Comportamento:** Muito mais rápido que um `/f` tradicional, operando em segundos durante a reinicialização.

### `chkdsk.exe C: /f`
- **Finalidade:** Corrige inconsistências na tabela mestra de arquivos (MFT), descritores de segurança e diretórios órfãos.
- **Comportamento:** Em unidades de sistema (`C:`), agenda a verificação para o próximo boot da máquina.

### `chkdsk.exe C: /f /r`
- **Finalidade:** Localiza setores físicos defeituosos (`bad sectors`) e tenta recuperar dados legíveis.
- **Comportamento:** Operação agressiva e intensiva que leva de 2 a 6 horas. Exige dupla confirmação no Toolkit.

---

## 5. Reparação do Repositório de Componentes (DISM)

### `DISM.exe /Online /Cleanup-Image /CheckHealth`
- **Finalidade:** Verifica de forma instantânea se o repositório de componentes (`WinSxS`) já foi marcado pelo sistema como corrompido.
- **Tempo de Execução:** Menor que 5 segundos.

### `DISM.exe /Online /Cleanup-Image /ScanHealth`
- **Finalidade:** Realiza uma leitura minuciosa de todos os pacotes e arquivos de manifesto no repositório de componentes para identificar corrupções ocultas.
- **Tempo de Execução:** Aproximadamente 5 a 10 minutos.

### `DISM.exe /Online /Cleanup-Image /RestoreHealth`
- **Finalidade:** Repara o repositório de componentes do Windows substituindo arquivos corrompidos por versões íntegras provenientes do Windows Update ou mídia oficial local.
- **Importância:** Deve ser executado antes do `sfc /scannow` em cenários onde o SFC relata arquivos não recuperáveis.

### `DISM.exe /Online /Cleanup-Image /StartComponentCleanup`
- **Finalidade:** Limpa versões obsoletas e substituídas de componentes e atualizações antigas acumuladas no diretório `WinSxS`.
- **Segurança:** Totalmente homologado pela Microsoft; mantém capacidade de rollback das atualizações recentes.

### `DISM.exe /Online /Cleanup-Image /StartComponentCleanup /ResetBase`
- **Finalidade:** Redefine a base de todos os componentes do sistema operacional.
- **Aviso Técnico:** Operação irreversível que remove a possibilidade de desinstalar atualizações e pacotes de serviços aplicados anteriormente. Exige confirmação dupla digitando `'CONFIRMAR'`.

---

## 6. Verificação de Arquivos Protegidos do Sistema (SFC)

### `sfc.exe /scannow`
- **Finalidade:** Verifica a integridade de todos os arquivos binários protegidos do Windows (`.dll`, `.exe`, drivers do kernel) e substitui versões corrompidas usando o cache íntegro do WinSxS.
- **Interpretação Técnica do Toolkit:**
  - Código 0 e mensagem sem violação: `[OK] Nenhuma violação encontrada`.
  - Arquivos recuperados com sucesso: `[INFO] Corrupções corrigidas com êxito`.
  - Arquivos corrompidos não recuperados: `[WARNING] Falha na recuperação de arquivos. Recomendado DISM /RestoreHealth`.
  - Reinicialização pendente: Registra necessidade de reboot do sistema.

---

## 7. Limpeza e Otimização de Armazenamento

### `Remove-Item` em pastas temporárias
- **Caminhos Analisados:**
  - `$env:TEMP\*` (Arquivos temporários da sessão do usuário)
  - `C:\Windows\Temp\*` (Arquivos temporários de instaladores e serviços do sistema)
  - `$env:LOCALAPPDATA\Microsoft\Windows\Explorer\thumbcache_*` (Cache de miniaturas de imagens)
- **Regras:** Executado com `-Recurse -Force -ErrorAction SilentlyContinue`. Arquivos em uso não travam o processo; arquivos pessoais nunca são afetados.

### `Clear-RecycleBin -Force`
- **Finalidade:** Esvazia permanentemente a lixeira de todas as unidades mapeadas.

### `cleanmgr.exe /VERYLOWDISK`
- **Finalidade:** Dispara o utilitário nativo de Limpeza de Disco da Microsoft em modo não interativo e prioritário para liberação imediata de espaço de sistema.

### `Optimize-Volume -DriveLetter $dl -ReTrim -Verbose`
- **Finalidade:** Executa o comando **TRIM** em unidades SSD.
- **Fundamento Técnico:** Notifica o controlador do SSD sobre quais blocos de dados foram excluídos e não contêm mais dados válidos, permitindo que a controladora limpe as células NAND de forma eficiente sem degradar a velocidade de escrita ou causar desgaste prematuro.

### `Optimize-Volume -DriveLetter $dl -Defrag -Verbose`
- **Finalidade:** Desfragmenta o sistema de arquivos em discos rígidos mecânicos (HDD) para aproximar blocos contíguos e reduzir o tempo de busca mecânica da cabeça de leitura.

---

## 8. Diagnóstico e Reparo de Conectividade de Rede

### `Get-CimInstance Win32_NetworkAdapterConfiguration -Filter "IPEnabled = True"`
- **Finalidade:** Audita apenas as placas de rede ativas que possuem endereçamento IP configurado, coletando IPv4, máscara de sub-rede, gateway padrão, servidores DNS e status do DHCP.

### `Test-Connection -ComputerName 8.8.8.8 -Count 2 -Quiet`
- **Finalidade:** Testa conectividade de pacotes ICMP (Ping) para testar a rota externa independente da resolução de nomes.

### `[System.Net.Dns]::GetHostAddresses("google.com")`
- **Finalidade:** Testa a capacidade do sistema em consultar os servidores DNS configurados e resolver endereços de nomes de domínio (FQDN) para endereços IP públicos.

### `ipconfig.exe /flushdns`
- **Finalidade:** Esvazia e redefine o conteúdo do cache de resolução do cliente DNS do Windows.

### `netsh.exe winsock reset`
- **Finalidade:** Redefine o catálogo do Winsock para a configuração padrão de fábrica. Essencial para solucionar falhas de conectividade causadas por malwares, proxies corrompidos ou desinstalações defeituosas de VPNs.

### `netsh.exe int ip reset`
- **Finalidade:** Redefine toda a pilha de protocolos TCP/IP gravando novamente as chaves de registro essenciais do kernel de rede. Exige reinicialização da máquina.

---

## 9. Segurança e Microsoft Defender

### `Update-MpSignature`
- **Finalidade:** Força o download e aplicação imediata das mais recentes definições de inteligência antimalware da Microsoft.

### `Get-MpComputerStatus`
- **Finalidade:** Audita o estado de saúde dos motores do Defender:
  - `AntivirusEnabled`: Motor antivírus ativo.
  - `RealTimeProtectionEnabled`: Proteção em tempo real ativa.
  - `AntivirusSignatureVersion`: Versão atual do banco de assinaturas.
  - `BehaviorMonitorEnabled`: Monitoramento proativo de comportamento.
  - `IoavProtectionEnabled`: Verificação de arquivos baixados da internet.
  - `NISEnabled`: Sistema de inspeção de rede contra exploits.

### `Start-MpScan -ScanType QuickScan`
- **Finalidade:** Realiza varredura rápida nas áreas mais vulneráveis do sistema (memória RAM, chaves de autorun e diretórios de sistema).

### `Start-MpScan -ScanType FullScan`
- **Finalidade:** Varredura exaustiva de todos os arquivos e partições da máquina.

### `Start-MpWDOScan`
- **Finalidade:** Inicia a verificação **Microsoft Defender Offline (WDO)**. O sistema operacional é reiniciado imediatamente em um ambiente WinPE isolado para detecção de ameaças que se ocultam do kernel ativo.

### `Get-MpThreatDetection` e `Get-MpThreat`
- **Finalidade:** Recupera o histórico de ameaças detectadas, nomes de pragas, arquivos afetados e ações executadas (quarentena ou remoção).

---

## 10. Diagnóstico de Eficiência Energética e Bateria

### `powercfg.exe /energy /output "$caminho"`
- **Finalidade:** Analisa o comportamento energético do sistema durante 60 segundos e gera um relatório HTML com erros de ACPI, consumo excessivo de timers e dispositivos que impedem o modo de suspensão.

### `powercfg.exe /batteryreport /output "$caminho"`
- **Finalidade:** Em notebooks e dispositivos portáteis, extrai o histórico de ciclos de carga, capacidade nominal de projeto e capacidade atual da bateria em mWh, permitindo calcular o desgaste real do hardware.

---

## 11. Gerenciamento de Recursos de IA do Windows

### `Get-AppxPackage -AllUsers | Where-Object { $_.Name -match "Copilot" }`
- **Finalidade:** Localiza pacotes UWP/AppX do Microsoft Copilot instalados no sistema para todos os usuários.

### `Remove-AppxPackage -AllUsers`
- **Finalidade:** Remove com segurança o pacote de aplicativo do Copilot sem comprometer dependências do Windows.

### `Get-WindowsOptionalFeature -Online | Where-Object { $_.FeatureName -match "Recall|AI" }`
- **Finalidade:** Consulta a presença do recurso opcional nativo do Windows Recall no catálogo de recursos do Windows 11.

### `Disable-WindowsOptionalFeature -Online -FeatureName "Recall" -Remove`
- **Finalidade:** Desativa e remove os binários do Windows Recall da imagem do sistema operacional.

### Políticas de Registro (Group Policies locais):
- **Click to Do:** Chave `HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI` -> Valor `DisableClickToDo` (DWORD 1 para desativar).
- **Cocreator do Paint:** Chave `HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Paint` -> Valor `DisableCocreator` (DWORD 1 para desativar).
- **Segurança de Backup:** O Toolkit executa `Backup-RegistryPolicyState` antes de gravar qualquer chave, salvando em `.\Backups\WindowsAI_YYYY-MM-DD_HH-mm-ss.json` para permitir reversão imediata.

---

## 12. Ponto de Restauração e Auditoria

### `Checkpoint-Computer -Description "..." -RestorePointType "MODIFY_SETTINGS"`
- **Finalidade:** Cria um ponto de restauração do sistema antes de manutenções ou reparos estruturais.
- **Verificação Prévia:** O Toolkit consulta `SystemRestoreEnabled` e alerta claramente caso a proteção da unidade C: esteja desligada pelo administrador.

### `Start-Transcript` e `Stop-Transcript`
- **Finalidade:** Grava toda a saída de tela do console no arquivo `.\Logs\Support_YYYY-MM-DD_HH-mm-ss.log`, garantindo trilha de auditoria completa para comprovação técnica junto a clientes e departamentos de conformidade (Compliance).

---

## 13. Conclusão

Todos os comandos acima foram selecionados com base em padrões de engenharia de sistemas da Microsoft, garantindo que o **Windows Support Toolkit** entregue o mais alto padrão de qualidade técnica, segurança de dados e eficácia operacional.
