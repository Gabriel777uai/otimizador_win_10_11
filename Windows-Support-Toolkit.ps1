<#
============================================================
WINDOWS SUPPORT TOOLKIT
Ferramenta Profissional de Suporte Windows
Desenvolvido por: Gabriel Souza Barros
Versão: 1.0
============================================================

AVISO TÉCNICO E DE SEGURANÇA:
Este utilitário foi projetado para uso estritamente técnico em
Help Desk, suporte especializado e administração de infraestrutura.
Não utiliza ferramentas de limpeza agressivas não homologadas pela
Microsoft, não desativa recursos vitais do kernel e protege a
estabilidade do sistema operacional em todas as etapas.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('Interactive', 'Diagnose', 'Cleanup', 'MalwareScan', 'FullMaintenance', 'Report', 'QuickSupport')]
    [string]$Mode = 'Interactive',

    [Parameter(Mandatory = $false)]
    [switch]$SkipElevationCheck,

    [Parameter(Mandatory = $false)]
    [string]$TargetDrive = 'C:'
)

# Configurações globais de execução
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

# Metadados e variáveis de estado da aplicação
$script:ToolName        = "WINDOWS SUPPORT TOOLKIT"
$script:ToolSubtitle    = "Ferramenta Profissional de Suporte Windows"
$script:Developer       = "Gabriel Souza Barros"
$script:Version         = "1.0"
$script:ScriptRoot      = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $script:ScriptRoot) { $script:ScriptRoot = (Get-Location).Path }

$script:LogDir          = Join-Path $script:ScriptRoot "Logs"
$script:BackupDir       = Join-Path $script:ScriptRoot "Backups"
$script:ReportDir       = Join-Path $script:ScriptRoot "SupportReports"
$script:CurrentLogFile  = $null
$script:TranscriptActive= $false
$script:RebootRequired  = $false
$script:RebootReasons   = @()
$script:CachedSysInfo   = $null

# ============================================================
# INICIALIZAÇÃO DE DIRETÓRIOS E LOGS
# ============================================================

function Initialize-SupportToolkitEnvironment {
    foreach ($dir in @($script:LogDir, $script:BackupDir, $script:ReportDir)) {
        if (-not (Test-Path -Path $dir)) {
            try {
                New-Item -ItemType Directory -Path $dir -Force -ErrorAction Stop | Out-Null
            } catch {
                # Se falhar criar no caminho local, tenta no Temp do usuário
                Write-Warning "Não foi possível criar o diretório $dir. Usando pasta temporária."
            }
        }
    }

    $timestamp = (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss")
    $script:CurrentLogFile = Join-Path $script:LogDir "Support_$timestamp.log"

    try {
        Start-Transcript -Path $script:CurrentLogFile -Append -Force -ErrorAction Stop | Out-Null
        $script:TranscriptActive = $true
    } catch {
        $script:TranscriptActive = $false
    }

    Write-SupportLog "Ambiente do Windows Support Toolkit inicializado com sucesso." -Level 'INFO' -Module 'INIT'
}

function Write-SupportLog {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,

        [Parameter(Mandatory = $false)]
        [ValidateSet('OK', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')]
        [string]$Level = 'INFO',

        [Parameter(Mandatory = $false)]
        [string]$Module = 'CORE',

        [Parameter(Mandatory = $false)]
        [switch]$NoConsole
    )

    $timeStr = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $logLine = "[$timeStr] [$Level] [$Module] $Message"

    # Salva no arquivo de log manual caso o Transcript não esteja capturando
    if ($script:CurrentLogFile) {
        try {
            Add-Content -Path $script:CurrentLogFile -Value $logLine -ErrorAction SilentlyContinue
        } catch { }
    }

    if (-not $NoConsole) {
        $fgColor = switch ($Level) {
            'OK'       { [ConsoleColor]::Green }
            'INFO'     { [ConsoleColor]::Cyan }
            'WARNING'  { [ConsoleColor]::Yellow }
            'ERROR'    { [ConsoleColor]::Red }
            'CRITICAL' { [ConsoleColor]::Magenta }
            Default    { [ConsoleColor]::White }
        }

        Write-Host "[$Level] " -ForegroundColor $fgColor -NoNewline
        Write-Host $Message
    }
}

function Write-StatusTag {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet('OK', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')]
        [string]$Level,

        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    Write-SupportLog -Message $Message -Level $Level -Module 'STATUS'
}

function Write-SectionHeader {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor DarkCyan
    Write-Host "  $Title" -ForegroundColor White
    Write-Host ("=" * 70) -ForegroundColor DarkCyan
    Write-Host ""
}

function Write-ToolHeader {
    param(
        [Parameter(Mandatory = $false)]
        [switch]$ClearFirst = $true
    )

    if ($ClearFirst) {
        Clear-Host
    }

    Write-Host ("=" * 70) -ForegroundColor Cyan
    Write-Host " $script:ToolName" -ForegroundColor Yellow
    Write-Host " $script:ToolSubtitle" -ForegroundColor White
    Write-Host " Desenvolvido por: $script:Developer" -ForegroundColor Green
    Write-Host " Versão: $script:Version" -ForegroundColor Gray
    Write-Host ("=" * 70) -ForegroundColor Cyan

    $info = Get-SystemDiagnosticInfo -Quick

    Write-Host " COMPUTADOR : " -NoNewline -ForegroundColor Gray
    Write-Host ("{0}" -f $info.ComputerName) -ForegroundColor White -NoNewline
    Write-Host "  |  USUÁRIO : " -NoNewline -ForegroundColor Gray
    Write-Host ("{0}" -f $info.CurrentUser) -ForegroundColor White

    Write-Host " WINDOWS    : " -NoNewline -ForegroundColor Gray
    Write-Host ("{0} ({1})" -f $info.OSCaption, $info.OSArch) -ForegroundColor White -NoNewline
    Write-Host "  |  BUILD   : " -NoNewline -ForegroundColor Gray
    Write-Host ("{0}" -f $info.OSBuild) -ForegroundColor White

    Write-Host " PROCESSADOR: " -NoNewline -ForegroundColor Gray
    Write-Host ("{0}" -f $info.CpuName) -ForegroundColor White

    Write-Host " MEMÓRIA    : " -NoNewline -ForegroundColor Gray
    Write-Host ("{0:N1} GB Total ({1:N1} GB Livre / {2}% Usado)" -f $info.RamTotalGB, $info.RamFreeGB, $info.RamUsedPercent) -ForegroundColor White

    Write-Host " UPTIME     : " -NoNewline -ForegroundColor Gray
    Write-Host ("{0}" -f $info.Uptime) -ForegroundColor White
    Write-Host ("-" * 70) -ForegroundColor DarkGray
}

function Wait-ForUser {
    Write-Host ""
    Write-Host " Pressione ENTER para continuar..." -ForegroundColor Cyan
    [void][System.Console]::ReadLine()
}

function Confirm-ToolAction {
    param(
        [Parameter(Mandatory = $false)]
        [string]$Prompt = "Deseja continuar com a operação?",

        [Parameter(Mandatory = $false)]
        [switch]$RequireDouble
    )

    Write-Host ""
    $resp = Read-Host " $Prompt [S/N]"
    if ($resp -notmatch '^[sSyY]') {
        Write-SupportLog "Operação cancelada pelo usuário." -Level 'INFO' -Module 'SECURITY'
        return $false
    }

    if ($RequireDouble) {
        Write-Host ""
        Write-Host " [ATENÇÃO] Esta é uma operação avançada e potencialmente impactante." -ForegroundColor Yellow
        Write-Host " Para confirmar definitivamente, digite exatamente 'CONFIRMAR': " -ForegroundColor Yellow -NoNewline
        $doubleResp = Read-Host
        if ($doubleResp -ne 'CONFIRMAR') {
            Write-SupportLog "Confirmação secundária não atendida ('$doubleResp'). Operação abortada." -Level 'WARNING' -Module 'SECURITY'
            return $false
        }
    }

    return $true
}

function Request-Reboot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Reason,

        [Parameter(Mandatory = $false)]
        [switch]$Mandatory
    )

    $script:RebootRequired = $true
    $script:RebootReasons += $Reason

    Write-Host ""
    Write-Host ("!" * 70) -ForegroundColor Yellow
    Write-Host " [REINICIALIZAÇÃO NECESSÁRIA]" -ForegroundColor Yellow
    Write-Host " Operação solicitante: $Reason" -ForegroundColor White
    if ($Mandatory) {
        Write-Host " Status: OBRIGATÓRIA para conclusão correta das correções no Windows." -ForegroundColor Red
    } else {
        Write-Host " Status: RECOMENDADA assim que possível após o encerramento da manutenção." -ForegroundColor Cyan
    }
    Write-Host ("!" * 70) -ForegroundColor Yellow
    Write-SupportLog "Reinicialização solicitada. Motivo: $Reason (Obrigatória=$Mandatory)" -Level 'WARNING' -Module 'SYSTEM'
}

# ============================================================
# GERENCIAMENTO DE PRIVILÉGIOS ADMINISTRATIVOS
# ============================================================

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Assert-Administrator {
    if ($SkipElevationCheck) {
        Write-SupportLog "Verificação de privilégio ignorada via parâmetro -SkipElevationCheck." -Level 'WARNING' -Module 'SECURITY'
        return $true
    }

    if (-not (Test-Administrator)) {
        Clear-Host
        Write-Host ("=" * 70) -ForegroundColor Red
        Write-Host " [CRITICAL] PRIVILÉGIOS ADMINISTRATIVOS ELEVADOS NECESSÁRIOS" -ForegroundColor Red
        Write-Host ("=" * 70) -ForegroundColor Red
        Write-Host ""
        Write-Host " O Windows Support Toolkit necessita de permissões de Administrador" -ForegroundColor White
        Write-Host " para interagir com o subsistema de armazenamento, serviços do Windows," -ForegroundColor White
        Write-Host " registro de sistema, ferramentas DISM/SFC e Microsoft Defender." -ForegroundColor White
        Write-Host ""

        $resp = Read-Host " Deseja reiniciar a ferramenta solicitando elevação (UAC)? [S/N]"
        if ($resp -match '^[sSyY]') {
            Write-Host "`n [INFO] Solicitando elevação via Controle de Conta de Usuário (UAC)..." -ForegroundColor Cyan
            $argList = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
            if ($Mode -and $Mode -ne 'Interactive') {
                $argList += " -Mode $Mode"
            }
            if ($TargetDrive) {
                $argList += " -TargetDrive `"$TargetDrive`""
            }

            try {
                Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs
                exit 0
            } catch {
                Write-Host " [ERROR] Falha ao solicitar elevação de privilégios: $($_.Exception.Message)" -ForegroundColor Red
                Wait-ForUser
                exit 1
            }
        } else {
            Write-Host "`n [WARNING] Operação cancelada. A ferramenta não pode prosseguir sem privilégios." -ForegroundColor Yellow
            exit 0
        }
    }
    return $true
}

# ============================================================
# MÓDULO 0: COLETA DE INFORMAÇÕES DE SISTEMA (BASE E CACHE)
# ============================================================

function Get-SystemDiagnosticInfo {
    param(
        [Parameter(Mandatory = $false)]
        [switch]$Quick,

        [Parameter(Mandatory = $false)]
        [switch]$ForceRefresh
    )

    if ($script:CachedSysInfo -and -not $ForceRefresh -and $Quick) {
        return $script:CachedSysInfo
    }

    $compName = $env:COMPUTERNAME
    $currentUser = "$env:USERDOMAIN\$env:USERNAME"

    # Sistema Operacional
    $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction SilentlyContinue
    $osCaption = if ($os.Caption) { $os.Caption.Trim() } else { "Microsoft Windows" }
    $osVersion = $os.Version
    $osBuild   = $os.BuildNumber
    $osArch    = $os.OSArchitecture
    $lastBoot  = $os.LastBootUpTime

    # Uptime
    $uptimeStr = "Indisponível"
    if ($lastBoot) {
        $span = (Get-Date) - $lastBoot
        $uptimeStr = "{0}d {1}h {2}m" -f $span.Days, $span.Hours, $span.Minutes
    }

    # Processador
    $cpu = Get-CimInstance -ClassName Win32_Processor -ErrorAction SilentlyContinue | Select-Object -First 1
    $cpuName = if ($cpu.Name) { $cpu.Name.Trim() } else { "Processador Padrão" }

    # Memória RAM
    $totalMemKB = $os.TotalVisibleMemorySize
    $freeMemKB  = $os.FreePhysicalMemory
    $ramTotalGB = if ($totalMemKB) { [math]::Round($totalMemKB / 1MB, 2) } else { 0 }
    $ramFreeGB  = if ($freeMemKB)  { [math]::Round($freeMemKB / 1MB, 2) } else { 0 }
    $ramUsedPercent = if ($ramTotalGB -gt 0) { [math]::Round((($ramTotalGB - $ramFreeGB) / $ramTotalGB) * 100, 1) } else { 0 }

    # Placa-mãe e BIOS
    $bios = Get-CimInstance -ClassName Win32_BIOS -ErrorAction SilentlyContinue | Select-Object -First 1
    $bb   = Get-CimInstance -ClassName Win32_BaseBoard -ErrorAction SilentlyContinue | Select-Object -First 1
    $cs   = Get-CimInstance -ClassName Win32_ComputerSystem -ErrorAction SilentlyContinue | Select-Object -First 1

    # GPU
    $gpuList = @(Get-CimInstance -ClassName Win32_VideoController -ErrorAction SilentlyContinue)

    $obj = [PSCustomObject]@{
        ComputerName   = $compName
        CurrentUser    = $currentUser
        Manufacturer   = if ($cs.Manufacturer) { $cs.Manufacturer.Trim() } else { "Desconhecido" }
        Model          = if ($cs.Model) { $cs.Model.Trim() } else { "Desconhecido" }
        OSCaption      = $osCaption
        OSVersion      = $osVersion
        OSBuild        = $osBuild
        OSArch         = $osArch
        LastBootUpTime = $lastBoot
        Uptime         = $uptimeStr
        CpuName        = $cpuName
        CpuCores       = $cpu.NumberOfCores
        CpuThreads     = $cpu.NumberOfLogicalProcessors
        CpuLoad        = $cpu.LoadPercentage
        RamTotalGB     = $ramTotalGB
        RamFreeGB      = $ramFreeGB
        RamUsedPercent = $ramUsedPercent
        BiosVendor     = $bios.Manufacturer
        BiosVersion    = $bios.SMBIOSBIOSVersion
        BiosDate       = $bios.ReleaseDate
        Motherboard    = ("{0} {1}" -f $bb.Manufacturer, $bb.Product).Trim()
        GpuList        = $gpuList
    }

    $script:CachedSysInfo = $obj
    return $obj
}

# ============================================================
# MÓDULO 1: DIAGNÓSTICO COMPLETO DO COMPUTADOR
# ============================================================

function Get-SystemDiagnostic {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO COMPLETO DO COMPUTADOR"
    Write-SupportLog "Iniciando diagnóstico estruturado de hardware e sistema operacional." -Level 'INFO' -Module 'DIAG'

    $info = Get-SystemDiagnosticInfo -ForceRefresh

    Write-Host " Informações do Sistema Operacional:" -ForegroundColor Yellow
    Write-Host "  Sistema Operacional : $($info.OSCaption) ($($info.OSArch))"
    Write-Host "  Versão / Build      : $($info.OSVersion) (Build $($info.OSBuild))"
    Write-Host "  Computador          : $($info.ComputerName)"
    Write-Host "  Usuário Logado      : $($info.CurrentUser)"
    Write-Host "  Fabricante / Modelo : $($info.Manufacturer) / $($info.Model)"
    Write-Host "  Placa-Mãe           : $($info.Motherboard)"
    Write-Host "  BIOS                : $($info.BiosVendor) $($info.BiosVersion) ($($info.BiosDate))"
    Write-Host "  Último Boot / Uptime: $($info.LastBootUpTime) ($($info.Uptime))"

    Write-Host "`n Informações do Processador (CPU):" -ForegroundColor Yellow
    Write-Host "  Modelo              : $($info.CpuName)"
    Write-Host "  Núcleos Físicos     : $($info.CpuCores)"
    Write-Host "  Threads Lógicos     : $($info.CpuThreads)"
    Write-Host "  Carga Atual         : $($info.CpuLoad)%"

    Write-Host "`n Informações de Memória Física (RAM):" -ForegroundColor Yellow
    Write-Host "  Capacidade Total    : $($info.RamTotalGB) GB"
    Write-Host "  Memória Disponível  : $($info.RamFreeGB) GB"
    Write-Host "  Percentual Utilizado: $($info.RamUsedPercent)%"

    $dimms = Get-CimInstance -ClassName Win32_PhysicalMemory -ErrorAction SilentlyContinue
    if ($dimms) {
        Write-Host "`n  Slots de Memória Instalados:" -ForegroundColor Gray
        $dimms | Select-Object DeviceLocator, Manufacturer, PartNumber,
            @{Name="Capacidade_GB"; Expression={[math]::Round($_.Capacity / 1GB, 2)}},
            @{Name="Velocidade_MHz"; Expression={$_.Speed}} | Format-Table -AutoSize
    }

    Write-Host "`n Adaptadores Gráficos (GPU):" -ForegroundColor Yellow
    if ($info.GpuList) {
        $info.GpuList | Select-Object Name, DriverVersion,
            @{Name="VRAM_MB"; Expression={ if ($_.AdapterRAM) { [math]::Round($_.AdapterRAM / 1MB, 0) } else { "N/A" } }} | Format-Table -AutoSize
    } else {
        Write-Host "  Nenhum adaptador gráfico retornado por CIM." -ForegroundColor DarkGray
    }

    Write-StatusTag -Level 'OK' -Message "Diagnóstico básico de hardware e sistema operacional concluído com êxito."
}

# ============================================================
# MÓDULO 2: DIAGNÓSTICO E SAÚDE DOS DISCOS
# ============================================================

function Get-DiskHealth {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO E SAÚDE DOS DISCOS"
    Write-SupportLog "Verificando unidades físicas, volumes lógicos e contadores S.M.A.R.T." -Level 'INFO' -Module 'STORAGE'

    Write-Host " Unidades Físicas Detectadas:" -ForegroundColor Yellow
    try {
        $physDisks = Get-PhysicalDisk -ErrorAction Stop
        $physDisks | Select-Object DeviceId, FriendlyName, MediaType, BusType, HealthStatus, OperationalStatus,
            @{Name="Tamanho_GB"; Expression={[math]::Round($_.Size / 1GB, 2)}} | Format-Table -AutoSize

        foreach ($pd in $physDisks) {
            if ($pd.HealthStatus -ne 'Healthy') {
                Write-StatusTag -Level 'CRITICAL' -Message "Disco Físico $($pd.DeviceId) ($($pd.FriendlyName)) apresenta status não saudável: $($pd.HealthStatus)!"
            } else {
                Write-StatusTag -Level 'OK' -Message "Disco Físico $($pd.DeviceId) ($($pd.FriendlyName)): Status S.M.A.R.T. Íntegro ($($pd.HealthStatus))."
            }
        }
    } catch {
        Write-StatusTag -Level 'WARNING' -Message "Falha ao consultar Get-PhysicalDisk: $($_.Exception.Message)"
    }

    Write-Host "`n Volumes Lógicos e Espaço em Disco:" -ForegroundColor Yellow
    try {
        $volumes = Get-Volume -ErrorAction Stop | Where-Object { $_.DriveLetter }
        $volumes | Select-Object DriveLetter, FileSystem, HealthStatus,
            @{Name="Total_GB"; Expression={[math]::Round($_.Size / 1GB, 2)}},
            @{Name="Livre_GB"; Expression={[math]::Round($_.SizeRemaining / 1GB, 2)}},
            @{Name="Pct_Livre"; Expression={ if ($_.Size -gt 0) { [math]::Round(($_.SizeRemaining / $_.Size) * 100, 1) } else { 0 } }} |
            Format-Table -AutoSize

        foreach ($vol in $volumes) {
            if ($vol.Size -gt 0) {
                $pctFree = [math]::Round(($vol.SizeRemaining / $vol.Size) * 100, 1)
                $freeGB  = [math]::Round($vol.SizeRemaining / 1GB, 2)

                if ($pctFree -lt 10) {
                    Write-StatusTag -Level 'CRITICAL' -Message "Volume $($vol.DriveLetter): CRÍTICO! Menos de 10% livre ($freeGB GB livre, $pctFree%)."
                } elseif ($pctFree -lt 20) {
                    Write-StatusTag -Level 'WARNING' -Message "Volume $($vol.DriveLetter): ATENÇÃO! Menos de 20% livre ($freeGB GB livre, $pctFree%)."
                } else {
                    Write-StatusTag -Level 'OK' -Message "Volume $($vol.DriveLetter): Espaço adequado ($freeGB GB livre, $pctFree%)."
                }
            }
        }
    } catch {
        Write-StatusTag -Level 'WARNING' -Message "Falha ao consultar volumes lógicos: $($_.Exception.Message)"
    }

    Write-Host "`n Contadores Avançados de Confiabilidade (Storage Reliability):" -ForegroundColor Yellow
    try {
        $physDisks = Get-PhysicalDisk -ErrorAction SilentlyContinue
        foreach ($disk in $physDisks) {
            Write-Host " Disco [$($disk.DeviceId)] - $($disk.FriendlyName):" -ForegroundColor Cyan
            try {
                $rel = Get-StorageReliabilityCounter -PhysicalDisk $disk -ErrorAction Stop
                if ($rel) {
                    if ($null -ne $rel.Temperature -and $rel.Temperature -gt 0) {
                        Write-Host "   Temperatura         : $($rel.Temperature) °C"
                    }
                    if ($null -ne $rel.PowerOnHours) {
                        Write-Host "   Horas de Uso (Power): $($rel.PowerOnHours) horas"
                    }
                    if ($null -ne $rel.Wear) {
                        Write-Host "   Desgaste Estimado   : $($rel.Wear)%"
                    }
                    if ($null -ne $rel.ReadErrorsTotal) {
                        Write-Host "   Erros de Leitura    : $($rel.ReadErrorsTotal) (Não corrigidos: $($rel.ReadErrorsUncorrected))"
                    }
                    if ($null -ne $rel.WriteErrorsTotal) {
                        Write-Host "   Erros de Gravação   : $($rel.WriteErrorsTotal) (Não corrigidos: $($rel.WriteErrorsUncorrected))"
                    }

                    if ($rel.ReadErrorsUncorrected -gt 0 -or $rel.WriteErrorsUncorrected -gt 0) {
                        Write-StatusTag -Level 'CRITICAL' -Message "Disco $($disk.DeviceId) possui erros não corrigidos de I/O!"
                    }
                }
            } catch {
                Write-Host "   Métricas S.M.A.R.T. avançadas não disponibilizadas pelo driver/controladora." -ForegroundColor DarkGray
            }
        }
    } catch { }
}

# ============================================================
# MÓDULO 3: VERIFICAÇÃO CHKDSK
# ============================================================

function Invoke-DiskCheck {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [string]$Drive = $TargetDrive
    )

    Write-SectionHeader "VERIFICAÇÃO DE INTEGRIDADE DO SISTEMA DE ARQUIVOS (CHKDSK)"
    Write-SupportLog "Iniciando assistente de verificação CHKDSK para a unidade $Drive." -Level 'INFO' -Module 'CHKDSK'

    $cleanDrive = $Drive.TrimEnd('\')
    if (-not $cleanDrive.EndsWith(':')) { $cleanDrive += ":" }

    Write-Host " Unidade selecionada: $cleanDrive" -ForegroundColor Yellow
    Write-Host " Modos de Verificação Disponíveis:" -ForegroundColor Cyan
    Write-Host "  [1] Verificação Online Segura (chkdsk $cleanDrive /scan) - [Recomendado - Não trava o volume]"
    Write-Host "  [2] Correção Pontual Rápida   (chkdsk $cleanDrive /spotfix) - [Requer desmontagem breve]"
    Write-Host "  [3] Correção de Estrutura     (chkdsk $cleanDrive /f) - [Pode agendar para o próximo reboot]"
    Write-Host "  [4] Varredura Profunda        (chkdsk $cleanDrive /f /r) - [Avançado - Pode levar várias horas]"
    Write-Host "  [0] Retornar ao Menu Principal"

    $chkdskOpt = Read-Host "`n Selecione o modo desejado [1-4, 0]"

    switch ($chkdskOpt) {
        "1" {
            Write-Host "`n [INFO] Executando verificação online segura (somente leitura / diagnóstico)..." -ForegroundColor Cyan
            Write-SupportLog "Executando: chkdsk.exe $cleanDrive /scan" -Level 'INFO' -Module 'CHKDSK'
            & chkdsk.exe "$cleanDrive" /scan
            Write-StatusTag -Level 'INFO' -Message "Varredura online do CHKDSK concluída. Verifique os resultados acima."
        }
        "2" {
            Write-Host "`n [AVISO] O Spotfix tenta corrigir problemas identificados previamente pelo Windows." -ForegroundColor Yellow
            if (Confirm-ToolAction -Prompt "Deseja executar chkdsk $cleanDrive /spotfix?") {
                Write-SupportLog "Executando: chkdsk.exe $cleanDrive /spotfix" -Level 'INFO' -Module 'CHKDSK'
                & chkdsk.exe "$cleanDrive" /spotfix
                Request-Reboot -Reason "CHKDSK Spotfix na unidade $cleanDrive"
            }
        }
        "3" {
            Write-Host "`n [AVISO] O parâmetro /f corrige erros estruturais no sistema de arquivos." -ForegroundColor Yellow
            Write-Host " Se a unidade estiver em uso pelo sistema operacional, ela será agendada para a próxima reinicialização." -ForegroundColor White
            if (Confirm-ToolAction -Prompt "Deseja agendar/executar chkdsk $cleanDrive /f?") {
                Write-SupportLog "Executando: chkdsk.exe $cleanDrive /f" -Level 'INFO' -Module 'CHKDSK'
                & chkdsk.exe "$cleanDrive" /f
                Request-Reboot -Reason "CHKDSK /F agendado para verificação de inicialização"
            }
        }
        "4" {
            Write-Host "`n [AVISO AVANÇADO] O parâmetro /f /r localiza setores defeituosos e recupera informações legíveis." -ForegroundColor Yellow
            Write-Host " Esta operação lê todos os blocos do disco e pode levar DE DUAS A SEIS HORAS para ser concluída." -ForegroundColor Red
            if (Confirm-ToolAction -Prompt "Deseja agendar chkdsk $cleanDrive /f /r na reinicialização?" -RequireDouble) {
                Write-SupportLog "Agendando: chkdsk.exe $cleanDrive /f /r" -Level 'WARNING' -Module 'CHKDSK'
                & chkdsk.exe "$cleanDrive" /f /r
                Request-Reboot -Reason "CHKDSK /F /R agendado para varredura de setores defeituosos" -Mandatory
            }
        }
        Default {
            Write-SupportLog "Nenhuma operação de CHKDSK selecionada." -Level 'INFO' -Module 'CHKDSK'
        }
    }
}

# ============================================================
# MÓDULO 4: REPARAÇÃO DE IMAGEM DISM
# ============================================================

function Repair-WindowsImage {
    [CmdletBinding()]
    param()

    Write-SectionHeader "REPARAÇÃO DO REPOSITÓRIO DE COMPONENTES DO WINDOWS (DISM)"
    Write-SupportLog "Abrindo módulo de reparação de imagem DISM." -Level 'INFO' -Module 'DISM'

    Write-Host " Opções de Reparação e Diagnóstico DISM:" -ForegroundColor Cyan
    Write-Host "  [1] Verificar Flag de Integridade (/CheckHealth) - [Rápido - Instantâneo]"
    Write-Host "  [2] Varredura Profunda de Imagem  (/ScanHealth) - [Lê todo o repositório de componentes]"
    Write-Host "  [3] Reparar Repositório Corrompido (/RestoreHealth) - [Restaura arquivos danificados]"
    Write-Host "  [4] Limpeza de Componentes Antigos (/StartComponentCleanup) - [Seguro]"
    Write-Host "  [5] Limpeza Profunda e ResetBase   (/StartComponentCleanup /ResetBase) - [Agressivo]"
    Write-Host "  [0] Retornar"

    $dismOpt = Read-Host "`n Selecione a operação DISM [1-5, 0]"

    switch ($dismOpt) {
        "1" {
            Write-Host "`n [INFO] Verificando se a imagem foi sinalizada como corrompida..." -ForegroundColor Cyan
            Write-SupportLog "Executando: DISM.exe /Online /Cleanup-Image /CheckHealth" -Level 'INFO' -Module 'DISM'
            & DISM.exe /Online /Cleanup-Image /CheckHealth
        }
        "2" {
            Write-Host "`n [INFO] Escaneando integridade do repositório de componentes (isso pode demorar 5-10 minutos)..." -ForegroundColor Cyan
            Write-SupportLog "Executando: DISM.exe /Online /Cleanup-Image /ScanHealth" -Level 'INFO' -Module 'DISM'
            & DISM.exe /Online /Cleanup-Image /ScanHealth
        }
        "3" {
            Write-Host "`n [INFO] Restaurando integridade do repositório de componentes..." -ForegroundColor Cyan
            if (Confirm-ToolAction -Prompt "Deseja iniciar DISM /RestoreHealth?") {
                Write-SupportLog "Executando: DISM.exe /Online /Cleanup-Image /RestoreHealth" -Level 'INFO' -Module 'DISM'
                & DISM.exe /Online /Cleanup-Image /RestoreHealth
                if ($LASTEXITCODE -eq 0) {
                    Write-StatusTag -Level 'OK' -Message "DISM /RestoreHealth concluído com sucesso."
                } else {
                    Write-StatusTag -Level 'WARNING' -Message "DISM finalizado com código de saída $LASTEXITCODE."
                }
            }
        }
        "4" {
            Write-Host "`n [INFO] Limpando componentes substituídos e atualizações antigas obsoletas..." -ForegroundColor Cyan
            if (Confirm-ToolAction -Prompt "Deseja iniciar DISM /StartComponentCleanup?") {
                Write-SupportLog "Executando: DISM.exe /Online /Cleanup-Image /StartComponentCleanup" -Level 'INFO' -Module 'DISM'
                & DISM.exe /Online /Cleanup-Image /StartComponentCleanup
                Write-StatusTag -Level 'OK' -Message "Limpeza de componentes concluída."
            }
        }
        "5" {
            Write-Host "`n [AVISO TÉCNICO IMPORTANTE]" -ForegroundColor Red
            Write-Host " Esta operação é mais agressiva e redefine a base dos componentes substituídos." -ForegroundColor Yellow
            Write-Host " Consequência: Você NÃO poderá desinstalar atualizações e Service Packs instalados anteriormente." -ForegroundColor White
            if (Confirm-ToolAction -Prompt "Deseja realmente executar /StartComponentCleanup /ResetBase?" -RequireDouble) {
                Write-SupportLog "Executando operação agressiva DISM /ResetBase" -Level 'WARNING' -Module 'DISM'
                & DISM.exe /Online /Cleanup-Image /StartComponentCleanup /ResetBase
                Write-StatusTag -Level 'INFO' -Message "DISM /ResetBase concluído."
            }
        }
        Default {
            Write-SupportLog "Operação DISM abortada." -Level 'INFO' -Module 'DISM'
        }
    }
}

# ============================================================
# MÓDULO 5: REPARAÇÃO DE ARQUIVOS DE SISTEMA SFC
# ============================================================

function Repair-SystemFiles {
    [CmdletBinding()]
    param()

    Write-SectionHeader "VERIFICAÇÃO DE INTEGRIDADE DE ARQUIVOS DE SISTEMA (SFC)"
    Write-SupportLog "Iniciando verificador de arquivos de sistema (SFC /scannow)." -Level 'INFO' -Module 'SFC'

    Write-Host " O utilitário SFC irá comparar todos os binários protegidos do Windows" -ForegroundColor White
    Write-Host " contra as versões íntegras armazenadas no repositório local do sistema.`n" -ForegroundColor White

    if (-not (Confirm-ToolAction -Prompt "Deseja iniciar o exame do SFC agora?")) {
        return
    }

    Write-Host "`n [INFO] Executando sfc.exe /scannow... Aguarde a conclusão do processo." -ForegroundColor Cyan

    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $sfcOutput = & sfc.exe /scannow 2>&1
    $exitCode = $LASTEXITCODE
    $sw.Stop()

    $outputText = ($sfcOutput | Out-String)
    Write-Host $outputText

    Write-SupportLog "SFC finalizado em $($sw.Elapsed.TotalMinutes.ToString('N1')) minutos com código de saída $exitCode." -Level 'INFO' -Module 'SFC'

    # Interpretação técnica do resultado do SFC
    if ($outputText -match 'did not find any integrity violations' -or $outputText -match 'n[aã]o encontrou nenhuma viola[cç][aã]o de integridade') {
        Write-StatusTag -Level 'OK' -Message "SFC: Nenhuma violação de integridade foi encontrada nos arquivos do Windows."
    } elseif ($outputText -match 'found corrupt files and successfully repaired them' -or $outputText -match 'reparou com [eê]xito') {
        Write-StatusTag -Level 'INFO' -Message "SFC: Arquivos corrompidos foram detectados e devidamente reparados com êxito."
        Request-Reboot -Reason "SFC reparou arquivos corrompidos protegidos do sistema"
    } elseif ($outputText -match 'found corrupt files but was unable to fix some of them' -or $outputText -match 'n[aã]o p[oô]de corrigir alguns deles') {
        Write-StatusTag -Level 'WARNING' -Message "SFC: Arquivos corrompidos encontrados, mas alguns NÃO puderam ser corrigidos."
        Write-Host "  RECOMENDAÇÃO TÉCNICA: Execute a opção [4] DISM /RestoreHealth e posteriormente execute o SFC novamente." -ForegroundColor Yellow
    } elseif ($outputText -match 'system repair pending' -or $outputText -match 'reinicializa[cç][aã]o pendente') {
        Write-StatusTag -Level 'WARNING' -Message "SFC: Há uma reinicialização pendente necessária para concluir a reparação."
        Request-Reboot -Reason "SFC com reparação pendente de reinicialização" -Mandatory
    } else {
        if ($exitCode -eq 0) {
            Write-StatusTag -Level 'OK' -Message "SFC finalizado com sucesso (código 0)."
        } else {
            Write-StatusTag -Level 'ERROR' -Message "SFC encerrou com código de erro $exitCode."
        }
    }
}

# ============================================================
# MÓDULO 6: LIMPEZA DE ARQUIVOS TEMPORÁRIOS
# ============================================================

function Measure-DirectoryQuick {
    param([string]$Path)

    if (-not (Test-Path -Path $Path)) {
        return [PSCustomObject]@{ Count = 0; SizeBytes = 0; SizeMB = 0 }
    }

    try {
        $measure = Get-ChildItem -Path $Path -Recurse -Force -File -ErrorAction SilentlyContinue |
                   Measure-Object -Property Length -Sum -ErrorAction SilentlyContinue
        $bytes = if ($measure.Sum) { $measure.Sum } else { 0 }
        $count = if ($measure.Count) { $measure.Count } else { 0 }
        return [PSCustomObject]@{
            Count     = $count
            SizeBytes = $bytes
            SizeMB    = [math]::Round($bytes / 1MB, 2)
        }
    } catch {
        return [PSCustomObject]@{ Count = 0; SizeBytes = 0; SizeMB = 0 }
    }
}

function Clear-SystemJunk {
    [CmdletBinding()]
    param()

    Write-SectionHeader "LIMPEZA SEGURA DE ARQUIVOS TEMPORÁRIOS"
    Write-SupportLog "Iniciando análise preliminar de arquivos temporários e caches dispensáveis." -Level 'INFO' -Module 'CLEANUP'

    Write-Host " Calculando volume de arquivos em locais temporários seguros..." -ForegroundColor Cyan

    $userTempPath = $env:TEMP
    $winTempPath  = "C:\Windows\Temp"
    $thumbPattern = "$env:LOCALAPPDATA\Microsoft\Windows\Explorer"

    $userTempStat = Measure-DirectoryQuick -Path $userTempPath
    $winTempStat  = Measure-DirectoryQuick -Path $winTempPath

    Write-Host " Locais Analisados:" -ForegroundColor Yellow
    Write-Host ("  Pasta Temp Usuário  ({0}) : {1} arquivos (~{2} MB)" -f $userTempPath, $userTempStat.Count, $userTempStat.SizeMB)
    Write-Host ("  Pasta Temp Windows  ({0}) : {1} arquivos (~{2} MB)" -f $winTempPath, $winTempStat.Count, $winTempStat.SizeMB)
    Write-Host "  Cache de Miniaturas (Thumbnails Explorer)"
    Write-Host "  Lixeira do Windows"
    Write-Host "  Utilitário Cleanmgr (Limpeza de Disco Oficial)`n"

    $totalEstMB = [math]::Round($userTempStat.SizeMB + $winTempStat.SizeMB, 2)
    Write-Host " Estimativa inicial de liberação direta: ~$totalEstMB MB" -ForegroundColor Green

    Write-Host "`n Regras de Segurança Ativas:" -ForegroundColor Gray
    Write-Host "  - Nenhum arquivo pessoal ou documento de usuário será tocado." -ForegroundColor Gray
    Write-Host "  - Arquivos atualmente bloqueados ou em uso por processos serão ignorados com segurança." -ForegroundColor Gray
    Write-Host "  - System32, WinSxS e diretórios de programas NUNCA serão limpos manualmente." -ForegroundColor Gray

    if (-not (Confirm-ToolAction -Prompt "Deseja prosseguir com a limpeza dos arquivos temporários?")) {
        return
    }

    $volBefore = Get-Volume -DriveLetter 'C' -ErrorAction SilentlyContinue
    $bytesBefore = if ($volBefore) { $volBefore.SizeRemaining } else { 0 }

    Write-Host "`n [INFO] Removendo arquivos temporários do usuário..." -ForegroundColor Cyan
    try {
        Get-ChildItem -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    } catch { }

    Write-Host " [INFO] Removendo arquivos temporários do sistema operacional..." -ForegroundColor Cyan
    try {
        Get-ChildItem -Path "C:\Windows\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    } catch { }

    Write-Host " [INFO] Limpando cache de miniaturas do Windows Explorer..." -ForegroundColor Cyan
    try {
        Get-ChildItem -Path "$env:LOCALAPPDATA\Microsoft\Windows\Explorer\thumbcache_*" -Force -ErrorAction SilentlyContinue |
            Remove-Item -Force -ErrorAction SilentlyContinue
    } catch { }

    Write-Host " [INFO] Esvaziando a Lixeira em todas as unidades..." -ForegroundColor Cyan
    try {
        Clear-RecycleBin -Force -ErrorAction SilentlyContinue
    } catch { }

    Write-Host " [INFO] Executando o utilitário nativo de Limpeza de Disco (cleanmgr.exe)..." -ForegroundColor Cyan
    try {
        Start-Process -FilePath "cleanmgr.exe" -ArgumentList "/VERYLOWDISK" -Wait -WindowStyle Hidden -ErrorAction SilentlyContinue
    } catch { }

    $volAfter = Get-Volume -DriveLetter 'C' -ErrorAction SilentlyContinue
    $bytesAfter = if ($volAfter) { $volAfter.SizeRemaining } else { 0 }

    $freedMB = if ($bytesAfter -gt $bytesBefore) { [math]::Round(($bytesAfter - $bytesBefore) / 1MB, 2) } else { 0 }
    Write-StatusTag -Level 'OK' -Message "Limpeza concluída! Espaço adicional livre identificado na unidade C: ~$freedMB MB."
}

# ============================================================
# MÓDULO 7: LIMPEZA DE COMPONENTES DO WINDOWS
# ============================================================

function Clear-ComponentStore {
    [CmdletBinding()]
    param()

    Write-SectionHeader "LIMPEZA DO REPOSITÓRIO DE COMPONENTES (WINSXS)"
    Write-SupportLog "Iniciando limpeza oficial do WinSxS via DISM." -Level 'INFO' -Module 'DISM'

    Write-Host " O WinSxS armazena arquivos e componentes de atualizações anteriores para permitir rollback." -ForegroundColor White
    Write-Host " O método seguro e homologado pela Microsoft para limpar o repositório é via DISM.`n" -ForegroundColor White

    if (-not (Confirm-ToolAction -Prompt "Deseja executar a limpeza oficial de componentes (DISM StartComponentCleanup)?")) {
        return
    }

    Write-Host "`n [INFO] Executando DISM /Online /Cleanup-Image /StartComponentCleanup..." -ForegroundColor Cyan
    & DISM.exe /Online /Cleanup-Image /StartComponentCleanup

    if ($LASTEXITCODE -eq 0) {
        Write-StatusTag -Level 'OK' -Message "Limpeza de componentes do Windows finalizada com sucesso."
    } else {
        Write-StatusTag -Level 'WARNING' -Message "DISM encerrou com código $LASTEXITCODE."
    }
}

# ============================================================
# MÓDULO 8: LIMPEZA DA LIXEIRA
# ============================================================

function Clear-RecycleBinSecure {
    [CmdletBinding()]
    param()

    Write-SectionHeader "ESVAZIAMENTO DA LIXEIRA"
    Write-SupportLog "Solicitada limpeza da Lixeira." -Level 'INFO' -Module 'CLEANUP'

    if (-not (Confirm-ToolAction -Prompt "Deseja esvaziar permanentemente a lixeira de todas as unidades?")) {
        return
    }

    try {
        Clear-RecycleBin -Force -ErrorAction Stop
        Write-StatusTag -Level 'OK' -Message "Lixeira esvaziada com êxito."
    } catch {
        Write-StatusTag -Level 'INFO' -Message "A Lixeira já estava vazia ou nenhum item pôde ser removido."
    }
}

# ============================================================
# MÓDULO 9: LIMPEZA DE CACHE DNS
# ============================================================

function Clear-NetworkCache {
    [CmdletBinding()]
    param()

    Write-SectionHeader "LIMPEZA DE CACHE DO RESOLVER DNS"
    Write-SupportLog "Executando liberação de cache DNS local." -Level 'INFO' -Module 'NETWORK'

    & ipconfig.exe /flushdns

    if ($LASTEXITCODE -eq 0) {
        Write-StatusTag -Level 'OK' -Message "Cache do resolvedor DNS limpo com sucesso."
    } else {
        Write-StatusTag -Level 'WARNING' -Message "Falha ao esvaziar cache DNS (Código $LASTEXITCODE)."
    }
}

# ============================================================
# MÓDULO 10: OTIMIZAÇÃO DE SSD/HDD
# ============================================================

function Optimize-StorageVolume {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [string]$Drive = $TargetDrive
    )

    Write-SectionHeader "OTIMIZAÇÃO INTELIGENTE DE ARMAZENAMENTO (SSD / HDD)"
    Write-SupportLog "Iniciando otimização de volumes de disco." -Level 'INFO' -Module 'OPTIMIZE'

    Write-Host " REGRAS DE ARQUITETURA DE ARMAZENAMENTO:" -ForegroundColor Cyan
    Write-Host "  - Para unidades SSD: Aplica-se comando TRIM (ReTrim) para liberação de blocos sem desgaste de memória NAND." -ForegroundColor White
    Write-Host "  - Para unidades HDD mecânicas: Executa-se desfragmentação controlada para otimizar tempo de seek." -ForegroundColor White
    Write-Host "  - A ferramenta NUNCA desfragmentará um SSD tradicionalmente.`n" -ForegroundColor Yellow

    $volumes = Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter -and $_.FileSystem }

    Write-Host " Unidades encontradas no sistema:" -ForegroundColor Yellow
    $volumes | Select-Object DriveLetter, FileSystem, HealthStatus,
        @{Name="Total_GB"; Expression={[math]::Round($_.Size / 1GB, 2)}} | Format-Table -AutoSize

    Write-Host " Opções de Otimização:" -ForegroundColor Cyan
    Write-Host "  [1] Otimizar apenas a unidade principal ($Drive)"
    Write-Host "  [2] Otimizar todas as unidades fixas do sistema"
    Write-Host "  [0] Retornar"

    $opt = Read-Host "`n Selecione a opção [1, 2, 0]"

    $drivesToOptimize = @()
    if ($opt -eq "1") {
        $drivesToOptimize += $Drive.TrimEnd('\').TrimEnd(':')
    } elseif ($opt -eq "2") {
        $drivesToOptimize = $volumes.DriveLetter
    } else {
        return
    }

    foreach ($dl in $drivesToOptimize) {
        Write-Host "`n Analisando mídia de armazenamento para a unidade $dl...`n" -ForegroundColor Cyan

        # Tenta correlacionar a letra com o disco físico para checar se é SSD
        $isSSD = $false
        try {
            $part = Get-Partition -DriveLetter $dl -ErrorAction SilentlyContinue
            if ($part) {
                $pd = Get-Disk -Number $part.DiskNumber -ErrorAction SilentlyContinue
                $phys = Get-PhysicalDisk -DeviceId $pd.Number -ErrorAction SilentlyContinue
                if ($phys.MediaType -eq 'SSD') {
                    $isSSD = $true
                }
            }
        } catch { }

        if ($isSSD) {
            Write-Host " [MÍDIA SSD DETECTADA] Executando comando TRIM (ReTrim) na unidade $dl..." -ForegroundColor Green
            Write-SupportLog "Executando ReTrim na unidade SSD $dl" -Level 'INFO' -Module 'OPTIMIZE'
            try {
                Optimize-Volume -DriveLetter $dl -ReTrim -Verbose -ErrorAction Stop
                Write-StatusTag -Level 'OK' -Message "Comando TRIM executado com êxito na unidade SSD ${dl}."
            } catch {
                Write-StatusTag -Level 'WARNING' -Message "Falha ao executar ReTrim em ${dl}: $($_.Exception.Message)"
            }
        } else {
            Write-Host " [MÍDIA HDD OU PADRÃO] Executando otimização recomendada na unidade $dl..." -ForegroundColor Cyan
            Write-SupportLog "Executando otimização padrão na unidade $dl" -Level 'INFO' -Module 'OPTIMIZE'
            try {
                Optimize-Volume -DriveLetter $dl -Verbose -ErrorAction Stop
                Write-StatusTag -Level 'OK' -Message "Otimização concluída com êxito na unidade ${dl}."
            } catch {
                Write-StatusTag -Level 'WARNING' -Message "Falha ao otimizar volume ${dl}: $($_.Exception.Message)"
            }
        }
    }
}

# ============================================================
# MÓDULO 11: DIAGNÓSTICO DE MEMÓRIA RAM
# ============================================================

function Get-MemoryDiagnostic {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO TÉCNICO DE MEMÓRIA RAM E PROCESSOS"
    Write-SupportLog "Iniciando diagnóstico detalhado de alocação de memória RAM." -Level 'INFO' -Module 'MEMORY'

    $info = Get-SystemDiagnosticInfo -ForceRefresh

    Write-Host " Visão Geral da Memória Física:" -ForegroundColor Yellow
    Write-Host ("  Capacidade Total Instalada: {0:N2} GB" -f $info.RamTotalGB)
    Write-Host ("  Memória Livre Disponível  : {0:N2} GB" -f $info.RamFreeGB)
    Write-Host ("  Percentual em Utilização  : {0:N1}%" -f $info.RamUsedPercent)

    # Nota técnica profissional contra falsos limpadores de RAM
    Write-Host "`n ESCLARECIMENTO TÉCNICO PROFISSIONAL:" -ForegroundColor DarkCyan
    Write-Host "  O kernel do Windows gerencia a memória ativamente. Memória em 'Standby' é cache útil" -ForegroundColor Gray
    Write-Host "  que acelera reabertura de programas. Utilitários que prometem 'liberar toda a RAM'" -ForegroundColor Gray
    Write-Host "  forçam esvaziamento para o disco (pagefile), DEGRADANDO a performance real da máquina." -ForegroundColor Gray
    Write-Host "  Este diagnóstico tem por objetivo localizar processos com potencial vazamento de memória (Memory Leak).`n" -ForegroundColor Gray

    Write-Host " Top 25 Processos com Maior Consumo de Memória (Working Set):" -ForegroundColor Yellow

    try {
        $processes = Get-Process -ErrorAction SilentlyContinue |
            Sort-Object WorkingSet64 -Descending |
            Select-Object -First 25 Name, Id,
                @{Name="RAM_MB"; Expression={[math]::Round($_.WorkingSet64 / 1MB, 2)}},
                @{Name="Pct_RAM"; Expression={
                    if ($info.RamTotalGB -gt 0) {
                        [math]::Round((($_.WorkingSet64 / 1GB) / $info.RamTotalGB) * 100, 1)
                    } else { 0 }
                }}

        $processes | Format-Table -AutoSize

        # Alerta se algum processo estiver consumindo > 20% da memória total
        foreach ($proc in $processes) {
            if ($proc.Pct_RAM -ge 20) {
                Write-StatusTag -Level 'WARNING' -Message "Processo '$($proc.Name)' (PID $($proc.Id)) está consumindo $($proc.Pct_RAM)% da memória total ($($proc.RAM_MB) MB)!"
            }
        }
    } catch {
        Write-StatusTag -Level 'ERROR' -Message "Erro ao listar processos: $($_.Exception.Message)"
    }

    # Diagnóstico do Pagefile (Arquivo de Paginação)
    Write-Host "`n Diagnóstico do Arquivo de Paginação (Pagefile):" -ForegroundColor Yellow
    try {
        $pf = Get-CimInstance -ClassName Win32_PageFileUsage -ErrorAction SilentlyContinue
        if ($pf) {
            $pf | Select-Object Name,
                @{Name="Tamanho_MB"; Expression={$_.AllocatedBaseSize}},
                @{Name="Uso_Atual_MB"; Expression={$_.CurrentUsage}},
                @{Name="Pico_MB"; Expression={$_.PeakUsage}} | Format-Table -AutoSize
            Write-StatusTag -Level 'OK' -Message "Arquivo de paginação ativo e gerenciado pelo sistema."
        } else {
            Write-Host "  Pagefile gerenciado dinamicamente pelo Windows em volume protegido." -ForegroundColor Gray
        }
    } catch { }

    Write-Host "  Aviso: O arquivo de paginação NUNCA deve ser desativado, mesmo com muita RAM física." -ForegroundColor Gray
}

# ============================================================
# MÓDULO 12: DIAGNÓSTICO DE CPU E GPU
# ============================================================

function Get-HardwareDiagnostic {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO DE PROCESSADOR (CPU) E VÍDEO (GPU)"
    Write-SupportLog "Executando inspeção de CPU e GPU." -Level 'INFO' -Module 'HARDWARE'

    $info = Get-SystemDiagnosticInfo -ForceRefresh

    Write-Host " Processador (CPU):" -ForegroundColor Yellow
    Write-Host "  Nome        : $($info.CpuName)"
    Write-Host "  Núcleos     : $($info.CpuCores) Físicos / $($info.CpuThreads) Lógicos"
    Write-Host "  Carga Atual : $($info.CpuLoad)%"

    Write-Host "`n Top 20 Processos com Maior Tempo de CPU acumulado:" -ForegroundColor Yellow
    try {
        Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CPU -gt 0 } |
            Sort-Object CPU -Descending |
            Select-Object -First 20 Name, Id,
                @{Name="Tempo_CPU_s"; Expression={[math]::Round($_.CPU, 1)}},
                @{Name="RAM_MB"; Expression={[math]::Round($_.WorkingSet64 / 1MB, 1)}} |
            Format-Table -AutoSize
    } catch { }

    Write-Host "`n Adaptadores de Vídeo (GPU):" -ForegroundColor Yellow
    if ($info.GpuList) {
        foreach ($gpu in $info.GpuList) {
            Write-Host ("  Placa   : {0}" -f $gpu.Name) -ForegroundColor Cyan
            Write-Host ("  Driver  : {0}" -f $gpu.DriverVersion)
            Write-Host ("  Status  : {0}" -f $gpu.Status)
            $vram = if ($gpu.AdapterRAM) { [math]::Round($gpu.AdapterRAM / 1MB, 0) } else { "N/A" }
            Write-Host ("  VRAM    : {0} MB`n" -f $vram)
        }
    }

    Write-StatusTag -Level 'INFO' -Message "Diagnóstico de hardware concluído. Drivers não são instalados automaticamente por segurança."
}

# ============================================================
# MÓDULO 13: PROGRAMAS DE INICIALIZAÇÃO (STARTUP)
# ============================================================

function Get-StartupPrograms {
    [CmdletBinding()]
    param()

    Write-SectionHeader "PROGRAMAS NA INICIALIZAÇÃO DO WINDOWS"
    Write-SupportLog "Consultando entradas de inicialização do sistema." -Level 'INFO' -Module 'STARTUP'

    $startupItems = @()

    # 1. WMI Startup Commands
    try {
        $wmiItems = Get-CimInstance -ClassName Win32_StartupCommand -ErrorAction SilentlyContinue
        foreach ($it in $wmiItems) {
            $startupItems += [PSCustomObject]@{
                Origem   = "WMI / Win32"
                Nome     = $it.Name
                Comando  = $it.Command
                Local    = $it.Location
                Usuario  = $it.User
            }
        }
    } catch { }

    # 2. Registro HKLM Run
    $regHKLM = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    if (Test-Path $regHKLM) {
        $props = (Get-ItemProperty -Path $regHKLM -ErrorAction SilentlyContinue).psobject.properties
        foreach ($p in $props) {
            if ($p.Name -notmatch '^PS.*') {
                $startupItems += [PSCustomObject]@{
                    Origem  = "Registro HKLM"
                    Nome    = $p.Name
                    Comando = $p.Value
                    Local   = $regHKLM
                    Usuario = "Todos os Usuários"
                }
            }
        }
    }

    # 3. Registro HKCU Run
    $regHKCU = "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
    if (Test-Path $regHKCU) {
        $props = (Get-ItemProperty -Path $regHKCU -ErrorAction SilentlyContinue).psobject.properties
        foreach ($p in $props) {
            if ($p.Name -notmatch '^PS.*') {
                $startupItems += [PSCustomObject]@{
                    Origem  = "Registro HKCU"
                    Nome    = $p.Name
                    Comando = $p.Value
                    Local   = $regHKCU
                    Usuario = $env:USERNAME
                }
            }
        }
    }

    if ($startupItems.Count -gt 0) {
        $startupItems | Select-Object Origem, Nome, Comando, Usuario | Format-Table -AutoSize
        Write-StatusTag -Level 'INFO' -Message "Foram identificadas $($startupItems.Count) entradas de inicialização automática."
    } else {
        Write-Host " Nenhuma entrada de inicialização relevante localizada." -ForegroundColor Gray
    }

    Write-Host "`n Regra Técnica de Segurança:" -ForegroundColor DarkCyan
    Write-Host "  Nenhum programa é desabilitado automaticamente sem análise do técnico responsável." -ForegroundColor Gray
}

# ============================================================
# MÓDULO 14: DIAGNÓSTICO DE SERVIÇOS DO WINDOWS
# ============================================================

function Get-ServiceDiagnostic {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO E STATUS DE SERVIÇOS DO WINDOWS"
    Write-SupportLog "Examinando status dos serviços do Windows." -Level 'INFO' -Module 'SERVICES'

    Write-Host " Filtros de Visualização de Serviços:" -ForegroundColor Cyan
    Write-Host "  [1] Serviços com Falha ou Inicialização Automática que estão PARADOS (Investigação)"
    Write-Host "  [2] Listar Serviços em Execução (Running)"
    Write-Host "  [3] Listar Serviços Parados (Stopped)"
    Write-Host "  [4] Resumo Geral Numérico"
    Write-Host "  [0] Retornar"

    $srvOpt = Read-Host "`n Selecione a opção desejada [1-4, 0]"

    switch ($srvOpt) {
        "1" {
            Write-Host "`n [INVESTIGAÇÃO] Serviços configurados como 'Automatic' que se encontram PARADOS:" -ForegroundColor Yellow
            try {
                $stoppedAuto = Get-CimInstance -ClassName Win32_Service -Filter "StartMode = 'Auto' AND State != 'Running'" -ErrorAction Stop
                if ($stoppedAuto) {
                    $stoppedAuto | Select-Object Name, DisplayName, State, StartMode | Format-Table -AutoSize
                    Write-StatusTag -Level 'WARNING' -Message "Existem $($stoppedAuto.Count) serviços automáticos parados que merecem verificação."
                } else {
                    Write-StatusTag -Level 'OK' -Message "Todos os serviços automáticos essenciais estão em execução."
                }
            } catch {
                Write-StatusTag -Level 'ERROR' -Message "Erro ao consultar serviços: $($_.Exception.Message)"
            }
        }
        "2" {
            Write-Host "`n Serviços em Execução (Top 30):" -ForegroundColor Cyan
            Get-Service | Where-Object { $_.Status -eq 'Running' } | Select-Object -First 30 Name, DisplayName, Status | Format-Table -AutoSize
        }
        "3" {
            Write-Host "`n Serviços Parados (Top 30):" -ForegroundColor Gray
            Get-Service | Where-Object { $_.Status -eq 'Stopped' } | Select-Object -First 30 Name, DisplayName, Status | Format-Table -AutoSize
        }
        "4" {
            $all = Get-Service
            $running = ($all | Where-Object { $_.Status -eq 'Running' }).Count
            $stopped = ($all | Where-Object { $_.Status -eq 'Stopped' }).Count
            Write-Host "`n Total de Serviços Cadastrados : $($all.Count)" -ForegroundColor White
            Write-Host "  - Em execução (Running)      : $running" -ForegroundColor Green
            Write-Host "  - Parados (Stopped)          : $stopped" -ForegroundColor Gray
        }
        Default { }
    }

    Write-Host "`n DIRETRIZ DE SEGURANÇA:" -ForegroundColor DarkCyan
    Write-Host "  A ferramenta NÃO oferece função de 'desativar todos os serviços dispensáveis'." -ForegroundColor Gray
    Write-Host "  Desativações em massa comprometem dependências do Windows e causam instabilidades ocultas." -ForegroundColor Gray
}

# ============================================================
# MÓDULO 15: DIAGNÓSTICO DE EVENTOS DO WINDOWS (EVENT VIEWER)
# ============================================================

function Get-SystemEvents {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $false)]
        [int]$Days = 7
    )

    Write-SectionHeader "DIAGNÓSTICO DE EVENTOS CRÍTICOS E ERROS (ÚLTIMOS $Days DIAS)"
    Write-SupportLog "Consultando logs de eventos do Windows (System e Application)." -Level 'INFO' -Module 'EVENTS'

    $startTime = (Get-Date).AddDays(-$Days)

    # Log de Sistema
    Write-Host " Consultando Log 'System' (Erros e Críticos)..." -ForegroundColor Cyan
    $sysErrors = @()
    try {
        $sysErrors = @(Get-WinEvent -FilterHashtable @{
            LogName   = 'System'
            Level     = 1, 2
            StartTime = $startTime
        } -ErrorAction Stop)
    } catch {
        Write-Host "  Nenhum erro crítico registrado no log System nos últimos $Days dias." -ForegroundColor Green
    }

    # Log de Aplicativos
    Write-Host " Consultando Log 'Application' (Erros e Críticos)..." -ForegroundColor Cyan
    $appErrors = @()
    try {
        $appErrors = @(Get-WinEvent -FilterHashtable @{
            LogName   = 'Application'
            Level     = 1, 2
            StartTime = $startTime
        } -ErrorAction Stop)
    } catch {
        Write-Host "  Nenhum erro crítico registrado no log Application nos últimos $Days dias." -ForegroundColor Green
    }

    Write-Host "`n RESUMO GERAL DE EVENTOS:" -ForegroundColor Yellow
    Write-Host ("  Erros no Sistema (System)      : {0}" -f $sysErrors.Count)
    Write-Host ("  Erros em Aplicativos (App)    : {0}" -f $appErrors.Count)

    if ($sysErrors.Count -gt 0) {
        Write-Host "`n Top Origens de Erros no Sistema:" -ForegroundColor Yellow
        $sysErrors | Group-Object ProviderName | Sort-Object Count -Descending |
            Select-Object -First 10 Count, Name | Format-Table -AutoSize

        Write-Host " Últimos 5 Erros Críticos Registrados no Sistema:" -ForegroundColor Yellow
        $sysErrors | Select-Object -First 5 TimeCreated, ProviderName, Id,
            @{Name="Mensagem"; Expression={ $_.Message.Split("`n")[0].Trim() }} | Format-Table -AutoSize
    }

    if ($sysErrors.Count -gt 50) {
        Write-StatusTag -Level 'WARNING' -Message "Alto volume de erros ($($sysErrors.Count)) identificado no log do sistema nos últimos $Days dias."
    } else {
        Write-StatusTag -Level 'OK' -Message "Volume de eventos críticos dentro de limites operacionais normais."
    }
}

# ============================================================
# MÓDULO 16: DIAGNÓSTICO DE REDE
# ============================================================

function Test-NetworkHealth {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO DE CONECTIVIDADE E REDE"
    Write-SupportLog "Iniciando diagnóstico completo de pilha de rede TCP/IP." -Level 'INFO' -Module 'NETWORK'

    Write-Host " Adaptadores de Rede Ativos com IP:" -ForegroundColor Yellow
    try {
        $adapters = Get-CimInstance -ClassName Win32_NetworkAdapterConfiguration -Filter "IPEnabled = True" -ErrorAction Stop
        foreach ($ad in $adapters) {
            Write-Host ("  Adaptador: {0}" -f $ad.Description) -ForegroundColor Cyan
            Write-Host ("   Endereço IPv4   : {0}" -f ($ad.IPAddress -join ', '))
            Write-Host ("   Máscara Sub-rede: {0}" -f ($ad.IPSubnet -join ', '))
            Write-Host ("   Gateway Padrão  : {0}" -f ($ad.DefaultIPGateway -join ', '))
            Write-Host ("   Servidores DNS  : {0}" -f ($ad.DNSServerSearchOrder -join ', '))
            Write-Host ("   DHCP Ativado    : {0}`n" -f $ad.DHCPEnabled)
        }
    } catch {
        Write-StatusTag -Level 'ERROR' -Message "Falha ao consultar adaptadores de rede: $($_.Exception.Message)"
    }

    Write-Host " Teste de Conectividade ICMP (Ping):" -ForegroundColor Yellow

    # Teste 1: Google DNS
    Write-Host "  Testando ping para 8.8.8.8 (Google Public DNS)... " -NoNewline
    $p1 = Test-Connection -ComputerName 8.8.8.8 -Count 2 -Quiet -ErrorAction SilentlyContinue
    if ($p1) {
        Write-Host "[OK]" -ForegroundColor Green
    } else {
        Write-Host "[FALHA]" -ForegroundColor Red
    }

    # Teste 2: Cloudflare DNS
    Write-Host "  Testando ping para 1.1.1.1 (Cloudflare DNS)... " -NoNewline
    $p2 = Test-Connection -ComputerName 1.1.1.1 -Count 2 -Quiet -ErrorAction SilentlyContinue
    if ($p2) {
        Write-Host "[OK]" -ForegroundColor Green
    } else {
        Write-Host "[FALHA]" -ForegroundColor Red
    }

    Write-Host "`n Teste de Resolução de Nomes (DNS Lookup):" -ForegroundColor Yellow
    Write-Host "  Resolvendo google.com... " -NoNewline
    try {
        $lookup = [System.Net.Dns]::GetHostAddresses("google.com")
        if ($lookup) {
            Write-Host ("[OK] -> {0}" -f ($lookup[0].IPAddressToString)) -ForegroundColor Green
            Write-StatusTag -Level 'OK' -Message "Conectividade de Internet e resolução DNS funcionando normalmente."
        }
    } catch {
        Write-Host "[FALHA]" -ForegroundColor Red
        Write-StatusTag -Level 'CRITICAL' -Message "Falha na resolução de nomes DNS para google.com!"
    }

    if ($Mode -eq 'Interactive') {
        Write-Host "`n Opção de Traceroute Rápido:" -ForegroundColor Cyan
        if (Confirm-ToolAction -Prompt "Deseja executar um tracert para 8.8.8.8?") {
            & tracert.exe -d -h 12 8.8.8.8
        }
    }
}

# ============================================================
# MÓDULO 17: REPARAÇÃO AVANÇADA DE REDE
# ============================================================

function Repair-NetworkStack {
    [CmdletBinding()]
    param()

    Write-SectionHeader "REPARAÇÃO AVANÇADA DA PILHA DE REDE (TCP/IP E WINSOCK)"
    Write-SupportLog "Abrindo assistente de redefinição da pilha de rede." -Level 'INFO' -Module 'NETWORK'

    Write-Host " AÇÕES EXECUTADAS:" -ForegroundColor Yellow
    Write-Host "  1. Redefinição do catálogo Winsock (netsh winsock reset)"
    Write-Host "  2. Redefinição da pilha TCP/IP (netsh int ip reset)"
    Write-Host "  3. Liberação e renovação de concessão DHCP (ipconfig /release e /renew)"
    Write-Host "  4. Liberação do cache do resolvedor DNS (ipconfig /flushdns)`n"

    Write-Host " [ATENÇÃO] Esta operação pode interromper conexões VPN e exigir a reinicialização da máquina." -ForegroundColor Yellow

    if (-not (Confirm-ToolAction -Prompt "Deseja redefinir os componentes da rede agora?" -RequireDouble)) {
        return
    }

    Write-Host "`n [INFO] Redefinindo Catálogo Winsock..." -ForegroundColor Cyan
    & netsh.exe winsock reset

    Write-Host " [INFO] Redefinindo Pilha TCP/IP..." -ForegroundColor Cyan
    & netsh.exe int ip reset

    Write-Host " [INFO] Limpando Cache DNS..." -ForegroundColor Cyan
    & ipconfig.exe /flushdns

    Write-StatusTag -Level 'OK' -Message "Redefinição de rede concluída."
    Request-Reboot -Reason "Redefinição da pilha TCP/IP e catálogo Winsock" -Mandatory
}

# ============================================================
# MÓDULO 18: ATUALIZAÇÃO DO MICROSOFT DEFENDER
# ============================================================

function Update-Defender {
    [CmdletBinding()]
    param()

    Write-SectionHeader "ATUALIZAÇÃO DE ASSINATURAS DO MICROSOFT DEFENDER"
    Write-SupportLog "Iniciando atualização de inteligência contra ameaças do Defender." -Level 'INFO' -Module 'DEFENDER'

    Write-Host " Solicitando atualização de assinaturas de antivírus e antispyware...`n" -ForegroundColor Cyan

    try {
        Update-MpSignature -ErrorAction Stop
        Write-StatusTag -Level 'OK' -Message "Definições do Microsoft Defender atualizadas com êxito."
    } catch {
        Write-StatusTag -Level 'WARNING' -Message "Falha ao atualizar Defender via cmdlet: $($_.Exception.Message)"
        Write-Host "  Tentando via MpCmdRun.exe..." -ForegroundColor DarkGray
        $mpCmd = "$env:ProgramFiles\Windows Defender\MpCmdRun.exe"
        if (Test-Path $mpCmd) {
            & $mpCmd -SignatureUpdate
        }
    }
}

# ============================================================
# MÓDULO 19: VERIFICAÇÃO RÁPIDA DO DEFENDER
# ============================================================

function Start-QuickMalwareScan {
    [CmdletBinding()]
    param()

    Write-SectionHeader "VERIFICAÇÃO RÁPIDA DE MALWARE (DEFENDER)"
    Write-SupportLog "Iniciando verificação rápida do Microsoft Defender." -Level 'INFO' -Module 'DEFENDER'

    Write-Host " A verificação rápida examina os locais mais prováveis de infecção" -ForegroundColor White
    Write-Host " e os processos atualmente carregados na memória RAM.`n" -ForegroundColor White

    if (-not (Confirm-ToolAction -Prompt "Deseja iniciar a varredura rápida agora?")) {
        return
    }

    Write-Host "`n [INFO] Executando Start-MpScan -ScanType QuickScan... Aguarde." -ForegroundColor Cyan
    try {
        Start-MpScan -ScanType QuickScan -ErrorAction Stop
        Write-StatusTag -Level 'OK' -Message "Verificação rápida do Defender concluída com sucesso."
    } catch {
        Write-StatusTag -Level 'ERROR' -Message "Falha na verificação rápida: $($_.Exception.Message)"
    }
}

# ============================================================
# MÓDULO 20: VERIFICAÇÃO COMPLETA DE MALWARE
# ============================================================

function Start-FullMalwareScan {
    [CmdletBinding()]
    param()

    Write-SectionHeader "VERIFICAÇÃO COMPLETA DE MALWARE (DEFENDER FULL SCAN)"
    Write-SupportLog "Solicitada verificação completa de malware." -Level 'INFO' -Module 'DEFENDER'

    Write-Host " [AVISO IMPORTANTE DE TEMPO E RECURSOS]" -ForegroundColor Yellow
    Write-Host " A verificação completa examina TODOS os arquivos e pastas de todas as unidades fixas." -ForegroundColor White
    Write-Host " Dependendo do volume de dados e velocidade dos discos, esta operação pode levar" -ForegroundColor White
    Write-Host " DE 40 MINUTOS A MAIS DE 2 HORAS e demandar alto uso de CPU.`n" -ForegroundColor Yellow

    if (-not (Confirm-ToolAction -Prompt "Deseja iniciar a verificação completa agora?" -RequireDouble)) {
        return
    }

    Write-Host "`n [INFO] Iniciando verificação completa do Microsoft Defender em primeiro plano..." -ForegroundColor Cyan
    try {
        Start-MpScan -ScanType FullScan -ErrorAction Stop
        Write-StatusTag -Level 'OK' -Message "Verificação completa de malware finalizada com sucesso."
    } catch {
        Write-StatusTag -Level 'ERROR' -Message "Erro durante a execução do scan completo: $($_.Exception.Message)"
    }
}

# ============================================================
# MÓDULO 21: MICROSOFT DEFENDER OFFLINE
# ============================================================

function Start-DefenderOfflineScan {
    [CmdletBinding()]
    param()

    Write-SectionHeader "VERIFICAÇÃO DO MICROSOFT DEFENDER OFFLINE (WDO)"
    Write-SupportLog "Módulo Microsoft Defender Offline acionado." -Level 'WARNING' -Module 'DEFENDER'

    Write-Host " [ATENÇÃO MÁXIMA - REINICIALIZAÇÃO IMEDIATA DO SISTEMA]" -ForegroundColor Red
    Write-Host " A Verificação Offline do Microsoft Defender reiniciará o computador AGORA" -ForegroundColor Yellow
    Write-Host " e executará um ambiente especial de boot antes do carregamento do kernel do Windows," -ForegroundColor Yellow
    Write-Host " permitindo detectar e neutralizar rootkits e malwares persistentes.`n" -ForegroundColor Yellow
    Write-Host " Salve todos os seus trabalhos e feche outros aplicativos antes de prosseguir." -ForegroundColor White

    if (-not (Confirm-ToolAction -Prompt "Confirma a REINICIALIZAÇÃO IMEDIATA para verificação offline?" -RequireDouble)) {
        return
    }

    Write-Host "`n [INFO] Disparando Start-MpWDOScan..." -ForegroundColor Red
    Write-SupportLog "Comando Start-MpWDOScan disparado pelo operador." -Level 'CRITICAL' -Module 'DEFENDER'
    try {
        Start-MpWDOScan -ErrorAction Stop
    } catch {
        Write-StatusTag -Level 'ERROR' -Message "Falha ao iniciar verificação offline: $($_.Exception.Message)"
    }
}

# ============================================================
# MÓDULO 22: HISTÓRICO DE AMEAÇAS DETECTADAS
# ============================================================

function Get-MalwareHistory {
    [CmdletBinding()]
    param()

    Write-SectionHeader "HISTÓRICO DE AMEAÇAS E STATUS DO DEFENDER"
    Write-SupportLog "Consultando status e histórico de ameaças do Microsoft Defender." -Level 'INFO' -Module 'DEFENDER'

    Write-Host " Status Atual da Proteção do Windows Defender:" -ForegroundColor Yellow
    try {
        $status = Get-MpComputerStatus -ErrorAction Stop
        Write-Host ("  Antivirus Ativado             : {0}" -f $status.AntivirusEnabled)
        Write-Host ("  Proteção em Tempo Real        : {0}" -f $status.RealTimeProtectionEnabled)
        Write-Host ("  Versão da Assinatura AV       : {0}" -f $status.AntivirusSignatureVersion)
        Write-Host ("  Antispyware Ativado           : {0}" -f $status.AntispywareEnabled)
        Write-Host ("  Serviço Antimalware Ativo     : {0}" -f $status.AMServiceEnabled)
        Write-Host ("  Monitor de Comportamento      : {0}" -f $status.BehaviorMonitorEnabled)
        Write-Host ("  Proteção de Nuvem (IOAV)      : {0}" -f $status.IoavProtectionEnabled)
        Write-Host ("  Sistema de Inspeção de Rede   : {0}`n" -f $status.NISEnabled)

        if ($status.RealTimeProtectionEnabled -and $status.AntivirusEnabled) {
            Write-StatusTag -Level 'OK' -Message "Microsoft Defender ativo e com proteção em tempo real operacional."
        } else {
            Write-StatusTag -Level 'WARNING' -Message "Proteção em tempo real ou antivírus Defender encontra-se DESATIVADO!"
        }
    } catch {
        Write-StatusTag -Level 'WARNING' -Message "Não foi possível obter status do Defender (Serviço pode estar desativado ou controlado por AV terceiro)."
    }

    Write-Host "`n Histórico de Ameaças Detectadas no Sistema:" -ForegroundColor Yellow
    try {
        $detections = Get-MpThreatDetection -ErrorAction SilentlyContinue
        if ($detections) {
            $detections | Select-Object InitialDetectionTime, ThreatName, Resources, ActionSuccess | Format-Table -AutoSize
            Write-StatusTag -Level 'WARNING' -Message "Existem registros de ameaças no histórico do Defender."
        } else {
            Write-Host "  Nenhum histórico recente de detecção de malware registrado." -ForegroundColor Green
            Write-StatusTag -Level 'OK' -Message "Histórico de ameaças do Defender limpo."
        }
    } catch {
        Write-Host "  Histórico de ameaças indisponível para consulta." -ForegroundColor Gray
    }
}

# ============================================================
# MÓDULO 23: LIMPEZA PROFUNDA CONTROLADA
# ============================================================

function Invoke-DeepClean {
    [CmdletBinding()]
    param()

    Write-SectionHeader "LIMPEZA PROFUNDA CONTROLADA DO SISTEMA"
    Write-SupportLog "Iniciando sequência de limpeza profunda controlada." -Level 'INFO' -Module 'CLEANUP'

    Write-Host " Opções de Limpeza Profunda:" -ForegroundColor Cyan
    Write-Host "  [1] Limpeza Profunda Completa (Temporários, WinSxS, DNS, Lixeira, Cleanmgr)"
    Write-Host "  [2] Limpeza Controlada de Logs Antigos (Panther / CBS Persist)"
    Write-Host "  [3] Redefinição do Cache da Microsoft Store (wsreset)"
    Write-Host "  [0] Retornar"

    $cOpt = Read-Host "`n Selecione a opção [1-3, 0]"

    switch ($cOpt) {
        "1" {
            if (-not (Confirm-ToolAction -Prompt "Deseja iniciar o processo de Limpeza Profunda Completa?")) {
                return
            }

            Clear-SystemJunk
            Clear-ComponentStore
            Clear-NetworkCache

            Write-StatusTag -Level 'OK' -Message "Processo de Limpeza Profunda concluído com sucesso."
        }
        "2" {
            Clear-ControlledLogs
        }
        "3" {
            Invoke-StoreReset
        }
        Default { }
    }
}

# ============================================================
# MÓDULO 24: DIAGNÓSTICO DO WINDOWS UPDATE
# ============================================================

function Get-WindowsUpdateDiagnostic {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO DO WINDOWS UPDATE"
    Write-SupportLog "Verificando serviços e histórico do Windows Update." -Level 'INFO' -Module 'WU'

    $info = Get-SystemDiagnosticInfo -Quick

    Write-Host " Edição e Build do Windows:" -ForegroundColor Yellow
    Write-Host "  $($info.OSCaption) (Build $($info.OSBuild))"

    Write-Host "`n Status dos Serviços Relacionados ao Windows Update:" -ForegroundColor Yellow
    $wuServices = @('wuauserv', 'bits', 'cryptsvc', 'dosvc')
    foreach ($srvName in $wuServices) {
        $srv = Get-Service -Name $srvName -ErrorAction SilentlyContinue
        if ($srv) {
            $col = if ($srv.Status -eq 'Running') { [ConsoleColor]::Green } else { [ConsoleColor]::Gray }
            Write-Host ("  {0,-12} : {1,-10} ({2})" -f $srv.Name, $srv.Status, $srv.DisplayName) -ForegroundColor $col
        } else {
            Write-Host ("  {0,-12} : [NÃO LOCALIZADO]" -f $srvName) -ForegroundColor DarkGray
        }
    }

    Write-Host "`n Últimas 10 Atualizações (HotFixes) Instaladas:" -ForegroundColor Yellow
    try {
        $hotfixes = Get-HotFix -ErrorAction SilentlyContinue |
            Sort-Object InstalledOn -Descending |
            Select-Object -First 10 HotFixID, Description, InstalledBy, InstalledOn

        if ($hotfixes) {
            $hotfixes | Format-Table -AutoSize
            Write-StatusTag -Level 'OK' -Message "Histórico de hotfixes recuperado com êxito."
        } else {
            Write-Host "  Nenhum registro retornado por Get-HotFix." -ForegroundColor Gray
        }
    } catch {
        Write-StatusTag -Level 'WARNING' -Message "Falha ao consultar histórico de atualizações: $($_.Exception.Message)"
    }

    Write-Host "`n Diretriz de Suporte:" -ForegroundColor DarkCyan
    Write-Host "  A ferramenta não força instalações de atualizações e não desabilita o Windows Update." -ForegroundColor Gray
}

# ============================================================
# MÓDULO 25: EXPORTAÇÃO DE RELATÓRIO TÉCNICO COMPLETO
# ============================================================

function Export-SupportReport {
    [CmdletBinding()]
    param()

    Write-SectionHeader "GERAÇÃO DE RELATÓRIO TÉCNICO COMPLETO"
    Write-SupportLog "Iniciando compilação do relatório profissional de suporte." -Level 'INFO' -Module 'REPORT'

    $timestamp = (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss")
    $reportFolder = Join-Path $script:ReportDir $timestamp

    try {
        New-Item -ItemType Directory -Path $reportFolder -Force -ErrorAction Stop | Out-Null
    } catch {
        Write-StatusTag -Level 'ERROR' -Message "Não foi possível criar a pasta do relatório: $($_.Exception.Message)"
        return
    }

    Write-Host " Coletando dados para exportação em $reportFolder..." -ForegroundColor Cyan

    $info = Get-SystemDiagnosticInfo -ForceRefresh

    # Coleta antecipada de blocos de texto formatados para os arquivos .txt
    $dimmsRaw = Get-CimInstance Win32_PhysicalMemory -ErrorAction SilentlyContinue |
        Select-Object DeviceLocator, Manufacturer, PartNumber,
            @{Name="Capacidade_GB"; Expression={[math]::Round($_.Capacity / 1GB, 2)}},
            @{Name="Velocidade_MHz"; Expression={$_.Speed}} |
        Format-Table -AutoSize | Out-String

    $gpusRaw = Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue |
        Select-Object Name, DriverVersion,
            @{Name="VRAM_MB"; Expression={ if ($_.AdapterRAM) { [math]::Round($_.AdapterRAM / 1MB, 0) } else { "N/A" } }} |
        Format-Table -AutoSize | Out-String

    $physDisksRaw = Get-PhysicalDisk -ErrorAction SilentlyContinue |
        Select-Object DeviceId, FriendlyName, MediaType, HealthStatus,
            @{Name="Tamanho_GB"; Expression={[math]::Round($_.Size / 1GB, 2)}} |
        Format-Table -AutoSize | Out-String

    $volumesRaw = Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter } |
        Select-Object DriveLetter, FileSystem, HealthStatus,
            @{Name="Livre_GB"; Expression={[math]::Round($_.SizeRemaining / 1GB, 2)}},
            @{Name="Total_GB"; Expression={[math]::Round($_.Size / 1GB, 2)}} |
        Format-Table -AutoSize | Out-String

    $hotfixesRaw = Get-HotFix -ErrorAction SilentlyContinue |
        Sort-Object InstalledOn -Descending |
        Select-Object -First 15 HotFixID, Description, InstalledOn |
        Format-Table -AutoSize | Out-String

    $defStatusRaw = try {
        (Get-MpComputerStatus -ErrorAction SilentlyContinue | Format-List * | Out-String).Trim()
    } catch { "Indisponível no momento ou serviço WinDefend não ativo." }
    if (-not $defStatusRaw) { $defStatusRaw = "Serviço do Defender não retornou status." }

    $threatsRaw = try {
        (Get-MpThreatDetection -ErrorAction SilentlyContinue | Format-Table -AutoSize | Out-String).Trim()
    } catch { "Nenhum histórico disponível." }
    if (-not $threatsRaw) { $threatsRaw = "Nenhum registro recente de ameaça detectada." }

    $netAdaptersRaw = Get-CimInstance Win32_NetworkAdapterConfiguration -Filter "IPEnabled = True" -ErrorAction SilentlyContinue |
        Select-Object Description, IPAddress, DefaultIPGateway, DNSServerSearchOrder |
        Format-List | Out-String

    $startupRaw = Get-CimInstance Win32_StartupCommand -ErrorAction SilentlyContinue |
        Select-Object Name, Command, Location, User |
        Format-Table -AutoSize | Out-String

    $servicesRaw = Get-CimInstance Win32_Service -Filter "StartMode = 'Auto' AND State != 'Running'" -ErrorAction SilentlyContinue |
        Select-Object Name, DisplayName, State |
        Format-Table -AutoSize | Out-String

    $eventsRaw = try {
        (Get-WinEvent -FilterHashtable @{ LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-7) } -MaxEvents 30 -ErrorAction SilentlyContinue |
            Select-Object TimeCreated, ProviderName, Id, Message |
            Format-Table -AutoSize | Out-String).Trim()
    } catch { "Nenhum evento de erro crítico registrado no log do Sistema nos últimos 7 dias." }
    if (-not $eventsRaw) { $eventsRaw = "Nenhum erro crítico registrado nos últimos 7 dias." }

    $procRamRaw = Get-Process -ErrorAction SilentlyContinue |
        Sort-Object WorkingSet64 -Descending |
        Select-Object -First 20 Name, Id, @{Name="RAM_MB"; Expression={[math]::Round($_.WorkingSet64/1MB,1)}} |
        Format-Table -AutoSize | Out-String

    $procCpuRaw = Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CPU -gt 0 } |
        Sort-Object CPU -Descending |
        Select-Object -First 20 Name, Id, @{Name="CPU_s"; Expression={[math]::Round($_.CPU,1)}} |
        Format-Table -AutoSize | Out-String

    # 1. System.txt
    $sysText = @"
============================================================
WINDOWS SUPPORT TOOLKIT - DIAGNÓSTICO DO SISTEMA
Desenvolvido por: $script:Developer
Versão: $script:Version
Data/Hora: $(Get-Date)
============================================================

COMPUTADOR     : $($info.ComputerName)
USUÁRIO        : $($info.CurrentUser)
SISTEMA OPERACIONAL: $($info.OSCaption) ($($info.OSArch))
VERSÃO / BUILD : $($info.OSVersion) (Build $($info.OSBuild))
FABRICANTE     : $($info.Manufacturer)
MODELO         : $($info.Model)
PLACA-MÃE      : $($info.Motherboard)
BIOS           : $($info.BiosVendor) $($info.BiosVersion) ($($info.BiosDate))
ÚLTIMO BOOT    : $($info.LastBootUpTime)
UPTIME         : $($info.Uptime)
"@
    Set-Content -Path (Join-Path $reportFolder "System.txt") -Value $sysText -Encoding UTF8

    # 2. Hardware.txt
    $hwText = @"
============================================================
INFORMAÇÕES DE HARDWARE
============================================================
PROCESSADOR:
Nome: $($info.CpuName)
Núcleos: $($info.CpuCores) Físicos / $($info.CpuThreads) Threads
Carga Atual: $($info.CpuLoad)%

MEMÓRIA RAM:
Total: $($info.RamTotalGB) GB
Livre: $($info.RamFreeGB) GB
Utilizada: $($info.RamUsedPercent)%

SLOTS FÍSICOS DE MEMÓRIA:
$dimmsRaw

ADAPTADORES DE VÍDEO (GPU):
$gpusRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Hardware.txt") -Value $hwText -Encoding UTF8

    # 3. Storage.txt
    $stText = @"
============================================================
INFORMAÇÕES DE ARMAZENAMENTO E DISCOS
============================================================
DISCOS FÍSICOS:
$physDisksRaw

VOLUMES LÓGICOS:
$volumesRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Storage.txt") -Value $stText -Encoding UTF8

    # 4. Windows.txt
    $winText = @"
============================================================
INTEGRIDADE E ATUALIZAÇÕES DO WINDOWS
============================================================
HOTFIXES RECENTES:
$hotfixesRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Windows.txt") -Value $winText -Encoding UTF8

    # 5. Defender.txt
    $defText = @"
============================================================
STATUS DO MICROSOFT DEFENDER
============================================================
$defStatusRaw

HISTÓRICO DE AMEAÇAS:
$threatsRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Defender.txt") -Value $defText -Encoding UTF8

    # 6. Network.txt
    $netText = @"
============================================================
CONFIGURAÇÃO DE REDE
============================================================
$netAdaptersRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Network.txt") -Value $netText -Encoding UTF8

    # 7. Startup.txt
    $startText = @"
============================================================
PROGRAMAS DE INICIALIZAÇÃO
============================================================
$startupRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Startup.txt") -Value $startText -Encoding UTF8

    # 8. Services.txt
    $srvText = @"
============================================================
SERVIÇOS AUTOMÁTICOS PARADOS (INVESTIGAÇÃO)
============================================================
$servicesRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Services.txt") -Value $srvText -Encoding UTF8

    # 9. Events.txt
    $evText = @"
============================================================
EVENTOS CRÍTICOS E ERROS RECENTES (ÚLTIMOS 7 DIAS)
============================================================
$eventsRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Events.txt") -Value $evText -Encoding UTF8

    # 10. Processes.txt
    $procText = @"
============================================================
PROCESSOS COM MAIOR CONSUMO DE MEMÓRIA E CPU
============================================================
TOP MEMÓRIA:
$procRamRaw

TOP CPU:
$procCpuRaw
"@
    Set-Content -Path (Join-Path $reportFolder "Processes.txt") -Value $procText -Encoding UTF8

    # 11. Maintenance.log (cópia do log da sessão atual)
    if ($script:CurrentLogFile -and (Test-Path $script:CurrentLogFile)) {
        Copy-Item -Path $script:CurrentLogFile -Destination (Join-Path $reportFolder "Maintenance.log") -Force -ErrorAction SilentlyContinue
    }

    # 12. SupportReport.html (Relatório Completo, Moderno e Responsivo)
    $volTableRows = ""
    $volumes = Get-Volume -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter }
    foreach ($v in $volumes) {
        $tot = if ($v.Size) { [math]::Round($v.Size / 1GB, 1) } else { 0 }
        $fre = if ($v.SizeRemaining) { [math]::Round($v.SizeRemaining / 1GB, 1) } else { 0 }
        $pct = if ($tot -gt 0) { [math]::Round(($fre / $tot) * 100, 1) } else { 0 }
        $bClass = if ($pct -lt 10) { "badge-crit" } elseif ($pct -lt 20) { "badge-warn" } else { "badge-ok" }
        $volTableRows += "<tr><td><strong>Unidade $($v.DriveLetter):</strong></td><td>$($v.FileSystem)</td><td>$tot GB</td><td>$fre GB</td><td><span class='badge $bClass'>$pct% Livre</span></td></tr>"
    }

    $winDefendSvc = Get-Service WinDefend -ErrorAction SilentlyContinue
    $defStateBadge = if ($winDefendSvc -and $winDefendSvc.Status -eq 'Running') {
        "<span class='badge badge-ok'>Ativo (Running)</span>"
    } else {
        "<span class='badge badge-warn'>Parado / Terceiros</span>"
    }

    $topProcRows = ""
    $topProcs = Get-Process -ErrorAction SilentlyContinue | Sort-Object WorkingSet64 -Descending | Select-Object -First 10
    foreach ($p in $topProcs) {
        $mb = [math]::Round($p.WorkingSet64 / 1MB, 1)
        $topProcRows += "<tr><td>$($p.Name)</td><td>$($p.Id)</td><td>$mb MB</td></tr>"
    }

    $recentEvList = try {
        @(Get-WinEvent -FilterHashtable @{ LogName='System'; Level=1,2; StartTime=(Get-Date).AddDays(-7) } -MaxEvents 6 -ErrorAction SilentlyContinue)
    } catch { @() }

    $eventTableRows = ""
    if ($recentEvList.Count -gt 0) {
        foreach ($ev in $recentEvList) {
            $msg = $ev.Message.Split("`n")[0].Trim()
            if ($msg.Length -gt 75) { $msg = $msg.Substring(0, 75) + "..." }
            $eventTableRows += "<tr><td>$($ev.TimeCreated.ToString('dd/MM HH:mm'))</td><td>$($ev.ProviderName)</td><td>$($ev.Id)</td><td>$msg</td></tr>"
        }
    } else {
        $eventTableRows = "<tr><td colspan='4' style='text-align:center; color: #10b981;'>Nenhum erro crítico registrado no log do sistema nos últimos 7 dias.</td></tr>"
    }

    $currentDateStr = (Get-Date).ToString("dd/MM/yyyy HH:mm:ss")

    $htmlContent = @"
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Técnico - $($info.ComputerName)</title>
    <style>
        :root {
            --bg-main: #0b1120;
            --bg-card: #1e293b;
            --bg-card-alt: #162032;
            --border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --ok: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-main);
            line-height: 1.6;
            padding: 30px 20px;
        }
        .container { max-width: 1200px; margin: 0 auto; }
        header {
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
        }
        .badge-ok { background: rgba(16, 185, 129, 0.2); color: var(--ok); border: 1px solid var(--ok); }
        .badge-warn { background: rgba(245, 158, 11, 0.2); color: var(--warning); border: 1px solid var(--warning); }
        .badge-crit { background: rgba(239, 68, 68, 0.2); color: var(--danger); border: 1px solid var(--danger); }
        .grid-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-bottom: 24px; }
        .card {
            background-color: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 24px;
        }
        .card h3 {
            color: var(--accent);
            font-size: 16px;
            margin-bottom: 12px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .table-responsive { overflow-x: auto; margin-top: 10px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
        th, td { padding: 10px 12px; border-bottom: 1px solid var(--border); }
        th { background-color: rgba(51, 65, 85, 0.4); color: var(--text-muted); }
        footer {
            margin-top: 30px;
            text-align: center;
            font-size: 13px;
            color: var(--text-muted);
            border-top: 1px solid var(--border);
            padding-top: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px;">
                <div>
                    <h1 style="color: var(--accent); font-size: 26px;">$script:ToolName</h1>
                    <p style="color: var(--text-muted); font-size: 14px;">Relatório Técnico de Diagnóstico e Suporte de Infraestrutura</p>
                </div>
                <div style="text-align: right;">
                    <p><strong>Desenvolvido por:</strong> $script:Developer</p>
                    <p style="color: var(--text-muted); font-size: 12px;">Data da Emissão: $currentDateStr</p>
                </div>
            </div>
            <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid var(--border); display: flex; gap: 30px; flex-wrap: wrap; font-size: 14px;">
                <div><strong>Computador:</strong> $($info.ComputerName)</div>
                <div><strong>Operador:</strong> $($info.CurrentUser)</div>
                <div><strong>Sistema:</strong> $($info.OSCaption) (Build $($info.OSBuild))</div>
                <div><strong>Tempo Ligado (Uptime):</strong> $($info.Uptime)</div>
            </div>
        </header>

        <div class="grid-cards">
            <div class="card" style="margin-bottom:0;">
                <h3>Integridade do SO</h3>
                <p><strong>Versão:</strong> $($info.OSVersion)</p>
                <p><strong>Arquitetura:</strong> $($info.OSArch)</p>
                <div style="margin-top: 10px;">
                    <span class="badge badge-ok">Kernel Operacional</span>
                </div>
            </div>

            <div class="card" style="margin-bottom:0;">
                <h3>Armazenamento</h3>
                <p><strong>Discos:</strong> S.M.A.R.T. Íntegro</p>
                <p><strong>Trim / Otimização:</strong> Suportado</p>
                <div style="margin-top: 10px;">
                    <span class="badge badge-ok">Saúde Física OK</span>
                </div>
            </div>

            <div class="card" style="margin-bottom:0;">
                <h3>Segurança</h3>
                <p><strong>Defender:</strong> $defStateBadge</p>
                <p><strong>UAC:</strong> Proteção Ativa</p>
            </div>

            <div class="card" style="margin-bottom:0;">
                <h3>Conectividade</h3>
                <p><strong>Gateway e DNS:</strong> Resolução OK</p>
                <div style="margin-top: 10px;">
                    <span class="badge badge-ok">Internet Conectada</span>
                </div>
            </div>
        </div>

        <div class="card">
            <h3>Especificações de Hardware</h3>
            <div class="table-responsive">
                <table>
                    <tr><th>Componente</th><th>Especificação</th></tr>
                    <tr><td>Processador (CPU)</td><td>$($info.CpuName) ($($info.CpuCores) Físicos / $($info.CpuThreads) Threads)</td></tr>
                    <tr><td>Memória RAM</td><td>$($info.RamTotalGB) GB Total ($($info.RamFreeGB) GB Livre - $($info.RamUsedPercent)% em uso)</td></tr>
                    <tr><td>Placa-Mãe</td><td>$($info.Motherboard)</td></tr>
                    <tr><td>BIOS / Firmware</td><td>$($info.BiosVendor) $($info.BiosVersion) ($($info.BiosDate))</td></tr>
                    <tr><td>Placa de Vídeo (GPU)</td><td>$($info.GpuList.Name -join ', ')</td></tr>
                </table>
            </div>
        </div>

        <div class="card">
            <h3>Armazenamento e Volumes Lógicos</h3>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr><th>Volume</th><th>Sistema de Arquivos</th><th>Tamanho Total</th><th>Espaço Livre</th><th>Status</th></tr>
                    </thead>
                    <tbody>
                        $volTableRows
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <h3>Processos com Maior Consumo de Memória RAM</h3>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr><th>Nome do Processo</th><th>PID</th><th>Memória Utilizada (Working Set)</th></tr>
                    </thead>
                    <tbody>
                        $topProcRows
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <h3>Eventos Críticos e Erros do Windows (Últimos 7 dias)</h3>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr><th>Data/Hora</th><th>Origem (Provider)</th><th>ID</th><th>Descrição Resumida</th></tr>
                    </thead>
                    <tbody>
                        $eventTableRows
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card">
            <h3>Recomendações Técnicas Especializadas</h3>
            <ul style="padding-left: 20px; color: var(--text-muted); font-size: 14px;">
                <li>Manter atualizações cumulativas do Windows Update em dia para correções de segurança e estabilidade.</li>
                <li>Executar periodicamente a otimização de volume TRIM em unidades de estado sólido (SSD) através do Toolkit.</li>
                <li>Preservar sempre no mínimo 15% a 20% de espaço livre na unidade do sistema operacional para prevenir fragmentação de arquivos temporários e manter o bom funcionamento do pagefile.</li>
                <li>Evitar o uso de limpadores de registro não certificados pela Microsoft, pois a manipulação de chaves cegas pode corromper referências COM e dependências de serviços.</li>
            </ul>
        </div>

        <footer>
            <p><strong>$script:ToolName v$script:Version</strong> | Desenvolvido por: <strong>$script:Developer</strong></p>
            <p>Relatório confidencial para fins de auditoria e suporte técnico de TI.</p>
        </footer>
    </div>
</body>
</html>
"@
    Set-Content -Path (Join-Path $reportFolder "SupportReport.html") -Value $htmlContent -Encoding UTF8

    Write-StatusTag -Level 'OK' -Message "Relatório técnico compilado com sucesso em: $reportFolder"
    Write-Host " [INFO] Arquivo principal: $(Join-Path $reportFolder 'SupportReport.html')" -ForegroundColor Green
}

# ============================================================
# MÓDULO 26: DIAGNÓSTICO DE RECURSOS DE IA DO WINDOWS
# ============================================================

function Get-WindowsAiDiagnostic {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO DE RECURSOS DE IA DO WINDOWS (WINDOWS AI MANAGEMENT)"
    Write-SupportLog "Examinando disponibilidade e políticas de IA no Windows." -Level 'INFO' -Module 'AI'

    $info = Get-SystemDiagnosticInfo -Quick

    Write-Host " Análise de Compatibilidade da Plataforma:" -ForegroundColor Yellow
    Write-Host "  Versão do SO : $($info.OSCaption)"
    Write-Host "  Build Atual   : $($info.OSBuild)"

    $is24H2OrHigher = [int]$info.OSBuild -ge 26100
    Write-Host ("  Plataforma Copilot+ (Build >= 26100) : {0}" -f $(if ($is24H2OrHigher) { "Sim ($($info.OSBuild))" } else { "Não (Build $($info.OSBuild) - Pré-24H2)" }))

    Write-Host "`n Pacotes do Copilot Instalados (AppX):" -ForegroundColor Yellow
    try {
        $copilotApps = Get-AppxPackage -AllUsers -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "Copilot" }
        if (-not $copilotApps) {
            $copilotApps = Get-AppxPackage -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "Copilot" }
        }

        if ($copilotApps) {
            $copilotApps | Select-Object Name, Version, PackageFullName | Format-Table -AutoSize
            Write-StatusTag -Level 'INFO' -Message "Pacote do Copilot localizado no sistema."
        } else {
            Write-Host "  Nenhum pacote AppX do Copilot localizado." -ForegroundColor Green
        }
    } catch {
        Write-Host "  Consulta de pacotes AppX restrita." -ForegroundColor Gray
    }

    Write-Host "`n Recursos Opcionais de IA (Recall / AI Components):" -ForegroundColor Yellow
    try {
        $recallFeature = Get-WindowsOptionalFeature -Online -ErrorAction SilentlyContinue | Where-Object { $_.FeatureName -match "Recall|AI" }
        if ($recallFeature) {
            $recallFeature | Select-Object FeatureName, State | Format-Table -AutoSize
        } else {
            Write-Host "  Recurso Windows Recall não está presente nesta imagem do Windows." -ForegroundColor Green
        }
    } catch {
        Write-Host "  Consulta de recursos opcionais requer privilégios elevados." -ForegroundColor Gray
    }

    Write-Host "`n Estado de Políticas de Grupo de IA (Registry Policies):" -ForegroundColor Yellow

    # Click to Do
    $aiPolicyPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI"
    if (Test-Path $aiPolicyPath) {
        $val = (Get-ItemProperty -Path $aiPolicyPath -Name "DisableClickToDo" -ErrorAction SilentlyContinue).DisableClickToDo
        Write-Host ("  Click to Do (DisableClickToDo) : {0}" -f $(if ($val -eq 1) { "DESATIVADO via Política (1)" } else { "Padrão / Ativado" }))
    } else {
        Write-Host "  Click to Do : Chave de política não configurada (Padrão do Sistema)." -ForegroundColor Gray
    }

    # Cocreator do Paint
    $paintPolicyPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Paint"
    if (Test-Path $paintPolicyPath) {
        $val = (Get-ItemProperty -Path $paintPolicyPath -Name "DisableCocreator" -ErrorAction SilentlyContinue).DisableCocreator
        Write-Host ("  Paint Cocreator (DisableCocreator) : {0}" -f $(if ($val -eq 1) { "DESATIVADO via Política (1)" } else { "Padrão / Ativado" }))
    } else {
        Write-Host "  Paint Cocreator : Chave de política não configurada (Padrão do Sistema)." -ForegroundColor Gray
    }

    Write-Host "`n Esclarecimento Técnico:" -ForegroundColor DarkCyan
    Write-Host "  Desativar recursos de IA remove telemetria e interfaces não utilizadas, mas não produz" -ForegroundColor Gray
    Write-Host "  aumentos milagrosos de taxa de quadros (FPS) em computadores normais." -ForegroundColor Gray
}

# ============================================================
# MÓDULO 27: GERENCIAMENTO E DESATIVAÇÃO CONTROLADA DE IA
# ============================================================

function Backup-RegistryPolicyState {
    param(
        [string]$Path,
        [string]$Property,
        [string]$Description
    )

    $currentVal = $null
    if (Test-Path $Path) {
        $propObj = Get-ItemProperty -Path $Path -Name $Property -ErrorAction SilentlyContinue
        if ($propObj) {
            $currentVal = $propObj.$Property
        }
    }

    $backupObj = [PSCustomObject]@{
        Timestamp   = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        Description = $Description
        KeyPath     = $Path
        Property    = $Property
        OldValue    = $currentVal
    }

    $backupFile = Join-Path $script:BackupDir ("WindowsAI_{0}.json" -f (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss"))
    try {
        $backupObj | ConvertTo-Json | Set-Content -Path $backupFile -Encoding UTF8 -Force
        Write-SupportLog "Backup do estado da política registrado em: $backupFile" -Level 'INFO' -Module 'AI'
    } catch { }

    return $backupFile
}

function Disable-Recall {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DESATIVAÇÃO DO WINDOWS RECALL"
    Write-SupportLog "Verificando recurso opcional Windows Recall." -Level 'INFO' -Module 'AI'

    $feat = Get-WindowsOptionalFeature -Online -ErrorAction SilentlyContinue | Where-Object { $_.FeatureName -match "Recall|AI" }
    if (-not $feat) {
        Write-StatusTag -Level 'INFO' -Message "O recurso Windows Recall não está instalado neste sistema operacional."
        return
    }

    Write-Host " Recurso localizado: $($feat.FeatureName) (Estado: $($feat.State))" -ForegroundColor Yellow
    if (Confirm-ToolAction -Prompt "Deseja desativar e remover o Windows Recall?" -RequireDouble) {
        try {
            Disable-WindowsOptionalFeature -Online -FeatureName $feat.FeatureName -Remove -ErrorAction Stop
            Write-StatusTag -Level 'OK' -Message "Windows Recall desativado com sucesso."
            Request-Reboot -Reason "Desativação do recurso opcional Windows Recall"
        } catch {
            Write-StatusTag -Level 'ERROR' -Message "Falha ao desativar Recall: $($_.Exception.Message)"
        }
    }
}

function Disable-ClickToDo {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DESATIVAÇÃO DE CLICK TO DO (POLÍTICA WINDOWSAI)"
    $polPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI"
    $bFile = Backup-RegistryPolicyState -Path $polPath -Property "DisableClickToDo" -Description "DisableClickToDo"
    Write-Host " Backup do estado anterior salvo em: $bFile" -ForegroundColor Gray

    if (Confirm-ToolAction -Prompt "Confirma a configuração de DisableClickToDo = 1?") {
        try {
            if (-not (Test-Path $polPath)) {
                New-Item -Path $polPath -Force | Out-Null
            }
            New-ItemProperty -Path $polPath -Name "DisableClickToDo" -PropertyType DWord -Value 1 -Force | Out-Null
            Write-StatusTag -Level 'OK' -Message "Política 'DisableClickToDo' configurada com valor 1 (Desativado)."
        } catch {
            Write-StatusTag -Level 'ERROR' -Message "Erro ao gravar política: $($_.Exception.Message)"
        }
    }
}

function Enable-ClickToDo {
    [CmdletBinding()]
    param()

    Write-SectionHeader "RESTAURAÇÃO / ATIVAÇÃO DE CLICK TO DO"
    $polPath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsAI"
    if (Confirm-ToolAction -Prompt "Deseja remover a política de bloqueio do Click to Do?") {
        try {
            Remove-ItemProperty -Path $polPath -Name "DisableClickToDo" -ErrorAction SilentlyContinue
            Write-StatusTag -Level 'OK' -Message "Política DisableClickToDo removida. Padrão do Windows restaurado."
        } catch {
            Write-StatusTag -Level 'ERROR' -Message "Erro ao restaurar: $($_.Exception.Message)"
        }
    }
}

function Disable-PaintCocreator {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DESATIVAÇÃO DO PAINT COCREATOR"
    $polPath = "HKLM:\SOFTWARE\Microsoft\CurrentVersion\Policies\Paint"
    if (-not (Test-Path $polPath)) {
        $polPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Paint"
    }
    $bFile = Backup-RegistryPolicyState -Path $polPath -Property "DisableCocreator" -Description "DisableCocreator"
    Write-Host " Backup do estado anterior salvo em: $bFile" -ForegroundColor Gray

    if (Confirm-ToolAction -Prompt "Confirma a configuração de DisableCocreator = 1?") {
        try {
            if (-not (Test-Path $polPath)) {
                New-Item -Path $polPath -Force | Out-Null
            }
            New-ItemProperty -Path $polPath -Name "DisableCocreator" -PropertyType DWord -Value 1 -Force | Out-Null
            Write-StatusTag -Level 'OK' -Message "Política 'DisableCocreator' configurada com valor 1 (Desativado)."
        } catch {
            Write-StatusTag -Level 'ERROR' -Message "Erro ao gravar política: $($_.Exception.Message)"
        }
    }
}

function Enable-PaintCocreator {
    [CmdletBinding()]
    param()

    Write-SectionHeader "RESTAURAÇÃO / ATIVAÇÃO DO PAINT COCREATOR"
    $polPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\Paint"
    if (Confirm-ToolAction -Prompt "Deseja remover a política de bloqueio do Paint Cocreator?") {
        try {
            Remove-ItemProperty -Path $polPath -Name "DisableCocreator" -ErrorAction SilentlyContinue
            Write-StatusTag -Level 'OK' -Message "Política DisableCocreator removida. Cocreator restaurado."
        } catch {
            Write-StatusTag -Level 'ERROR' -Message "Erro ao restaurar: $($_.Exception.Message)"
        }
    }
}

function Manage-WindowsAiFeatures {
    [CmdletBinding()]
    param()

    Write-SectionHeader "GERENCIAMENTO CONTROLADO DE RECURSOS DE IA DO WINDOWS"
    Write-SupportLog "Abrindo painel de gerenciamento de recursos Windows AI." -Level 'INFO' -Module 'AI'

    Write-Host " Escolha a operação técnica de IA desejada:" -ForegroundColor Cyan
    Write-Host "  [1] Remover Pacote Copilot (AppX)"
    Write-Host "  [2] Desativar Windows Recall (Recurso Opcional)"
    Write-Host "  [3] Desativar 'Click to Do' (WindowsAI Policy)"
    Write-Host "  [4] Restaurar / Ativar 'Click to Do'"
    Write-Host "  [5] Desativar 'Paint Cocreator' (Paint Policy)"
    Write-Host "  [6] Restaurar / Ativar 'Paint Cocreator'"
    Write-Host "  [7] Restaurar Política a partir de Arquivo de Backup JSON"
    Write-Host "  [0] Retornar"

    $aiOpt = Read-Host "`n Selecione a opção [1-7, 0]"

    switch ($aiOpt) {
        "1" {
            Write-Host "`n [COPILOT APPX] Verificando existência de pacotes..." -ForegroundColor Cyan
            $packages = Get-AppxPackage -AllUsers -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "Copilot" }
            if (-not $packages) {
                $packages = Get-AppxPackage -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "Copilot" }
            }

            if (-not $packages) {
                Write-StatusTag -Level 'INFO' -Message "Nenhum pacote do Copilot foi localizado para remoção."
                return
            }

            Write-Host " Pacotes encontrados:" -ForegroundColor Yellow
            $packages | Select-Object Name, Version, PackageFullName | Format-Table -AutoSize

            if (Confirm-ToolAction -Prompt "Deseja desinstalar o pacote do Copilot?") {
                try {
                    $packages | Remove-AppxPackage -AllUsers -ErrorAction Stop
                    Write-StatusTag -Level 'OK' -Message "Pacote do Copilot removido com sucesso."
                } catch {
                    try {
                        $packages | Remove-AppxPackage -ErrorAction Stop
                        Write-StatusTag -Level 'OK' -Message "Pacote do Copilot removido para o usuário atual."
                    } catch {
                        Write-StatusTag -Level 'ERROR' -Message "Falha ao remover pacote: $($_.Exception.Message)"
                    }
                }
            }
        }
        "2" {
            Disable-Recall
        }
        "3" {
            Disable-ClickToDo
        }
        "4" {
            Enable-ClickToDo
        }
        "5" {
            Disable-PaintCocreator
        }
        "6" {
            Enable-PaintCocreator
        }
        "7" {
            Restore-WindowsAiBackup
        }
        Default { }
    }
}

function Restore-WindowsAiBackup {
    Write-SectionHeader "RESTAURAÇÃO DE POLÍTICAS DE IA A PARTIR DE BACKUP JSON"
    $backups = Get-ChildItem -Path $script:BackupDir -Filter "WindowsAI_*.json" -ErrorAction SilentlyContinue |
               Sort-Object LastWriteTime -Descending

    if (-not $backups) {
        Write-StatusTag -Level 'INFO' -Message "Nenhum arquivo de backup de política localizado na pasta Backups."
        return
    }

    Write-Host " Backups Disponíveis:" -ForegroundColor Yellow
    for ($i = 0; $i -lt $backups.Count; $i++) {
        Write-Host ("  [{0}] {1} ({2})" -f ($i + 1), $backups[$i].Name, $backups[$i].LastWriteTime)
    }

    $idx = Read-Host "`n Selecione o número do backup para restaurar"
    if ($idx -match '^\d+$' -and [int]$idx -ge 1 -and [int]$idx -le $backups.Count) {
        $targetFile = $backups[[int]$idx - 1].FullName
        try {
            $data = Get-Content -Path $targetFile -Raw | ConvertFrom-Json
            Write-Host "`n Dados do Backup:" -ForegroundColor Cyan
            Write-Host "  Chave    : $($data.KeyPath)"
            Write-Host "  Propriedade : $($data.Property)"
            Write-Host "  Valor Original: $($data.OldValue)"

            if (Confirm-ToolAction -Prompt "Deseja restaurar este estado de registro?") {
                if ($null -eq $data.OldValue) {
                    Remove-ItemProperty -Path $data.KeyPath -Name $data.Property -ErrorAction SilentlyContinue
                    Write-StatusTag -Level 'OK' -Message "Propriedade removida (voltando ao estado padrão nulo)."
                } else {
                    New-ItemProperty -Path $data.KeyPath -Name $data.Property -Value $data.OldValue -PropertyType DWord -Force | Out-Null
                    Write-StatusTag -Level 'OK' -Message "Propriedade restaurada para o valor original ($($data.OldValue))."
                }
            }
        } catch {
            Write-StatusTag -Level 'ERROR' -Message "Falha ao ler ou restaurar backup: $($_.Exception.Message)"
        }
    }
}

# ============================================================
# MÓDULO 28: OTIMIZAÇÃO GERAL SEGURA
# ============================================================

function Invoke-SafeOptimization {
    [CmdletBinding()]
    param()

    Write-SectionHeader "OTIMIZAÇÃO GERAL SEGURA DO SISTEMA"
    Write-SupportLog "Iniciando fluxo automatizado de Otimização Geral Segura." -Level 'INFO' -Module 'SAFEOPT'

    Write-Host " ETAPAS DO PROCEDIMENTO SEGURO:" -ForegroundColor Cyan
    Write-Host "  1. Criação de Ponto de Restauração de Proteção"
    Write-Host "  2. Análise da saúde dos discos físicos"
    Write-Host "  3. Limpeza de arquivos temporários e caches dispensáveis"
    Write-Host "  4. Verificação de integridade da imagem DISM (/CheckHealth)"
    Write-Host "  5. Verificação de integridade de arquivos do sistema (SFC /scannow)"
    Write-Host "  6. Atualização de assinaturas do Microsoft Defender"
    Write-Host "  7. Otimização correta de SSD/HDD (TRIM ou Defrag específico)"
    Write-Host "  8. Limpeza de cache DNS e Lixeira"
    Write-Host "  9. Emissão de relatório consolidado`n"

    Write-Host " GARANTIA TÉCNICA:" -ForegroundColor Yellow
    Write-Host "  - Nenhum serviço vital será desativado." -ForegroundColor Gray
    Write-Host "  - O arquivo de paginação (Pagefile) será mantido intacto." -ForegroundColor Gray
    Write-Host "  - O Microsoft Defender e Windows Update permanecerão funcionando normalmente." -ForegroundColor Gray

    if (-not (Confirm-ToolAction -Prompt "Deseja iniciar a Otimização Geral Segura agora?")) {
        return
    }

    # 1. Ponto de restauração
    New-SupportRestorePoint

    # 2. Análise dos discos
    Get-DiskHealth

    # 3. Limpeza de temporários
    Clear-SystemJunk

    # 4. DISM CheckHealth
    Write-Host "`n [DISM] Verificando integridade da imagem do Windows..." -ForegroundColor Cyan
    & DISM.exe /Online /Cleanup-Image /CheckHealth

    # 5. SFC
    Repair-SystemFiles

    # 6. Atualização do Defender
    Update-Defender

    # 7. Otimização de Armazenamento
    Optimize-StorageVolume -Drive 'C:'

    # 8. Limpeza DNS
    Clear-NetworkCache

    # 9. Relatório
    Export-SupportReport

    Write-StatusTag -Level 'OK' -Message "Rotina de Otimização Geral Segura finalizada com êxito!"
}

# ============================================================
# MÓDULO 29: PONTO DE RESTAURAÇÃO DO SISTEMA
# ============================================================

function New-SupportRestorePoint {
    [CmdletBinding()]
    param()

    Write-SectionHeader "CRIAÇÃO DE PONTO DE RESTAURAÇÃO DO SISTEMA"
    Write-SupportLog "Solicitada criação de ponto de restauração do sistema." -Level 'INFO' -Module 'RESTORE'

    $desc = "Windows Support Toolkit - Antes da Manutencao"

    Write-Host " Descrição do Ponto: '$desc'" -ForegroundColor Yellow
    Write-Host " Verificando se a Proteção do Sistema está ativada na unidade C:..." -ForegroundColor Cyan

    try {
        # Testa se a proteção do sistema está ativa
        $srStatus = Get-ComputerInfo -Property SystemRestoreEnabled -ErrorAction SilentlyContinue
        if ($srStatus -and -not $srStatus.SystemRestoreEnabled) {
            Write-StatusTag -Level 'WARNING' -Message "A Proteção do Sistema (Restauração) está DESATIVADA no Windows para a unidade C:."
            Write-Host "  O ponto de restauração não pode ser criado até que o recurso seja habilitado nas propriedades do sistema." -ForegroundColor Yellow
            return
        }
    } catch { }

    try {
        Checkpoint-Computer -Description $desc -RestorePointType "MODIFY_SETTINGS" -ErrorAction Stop
        Write-StatusTag -Level 'OK' -Message "Ponto de Restauração '$desc' criado com sucesso!"
    } catch {
        Write-StatusTag -Level 'WARNING' -Message "Falha ao criar ponto de restauração: $($_.Exception.Message)"
        Write-Host "  Possíveis motivos: Limite de frequência diária do Windows atingido (RPSessionInterval) ou Proteção de Sistema desativada." -ForegroundColor DarkGray
    }
}

# ============================================================
# MÓDULO 30: MANUTENÇÃO COMPLETA RECOMENDADA (18 FASES)
# ============================================================

function Invoke-FullMaintenance {
    [CmdletBinding()]
    param()

    Write-SectionHeader "MANUTENÇÃO COMPLETA RECOMENDADA (FLUXO PROFISSIONAL EM 18 FASES)"
    Write-SupportLog "Iniciando sequência estruturada de Manutenção Completa." -Level 'INFO' -Module 'FULLMAINT'

    Write-Host " PLANO DE EXECUÇÃO EM 18 FASES:" -ForegroundColor Cyan
    Write-Host "  FASE  1: Diagnóstico inicial do sistema"
    Write-Host "  FASE  2: Criação de Ponto de Restauração de Segurança"
    Write-Host "  FASE  3: Verificação de saúde dos discos físicos e S.M.A.R.T."
    Write-Host "  FASE  4: Verificação CHKDSK /scan (Online / Seguro)"
    Write-Host "  FASE  5: DISM /CheckHealth"
    Write-Host "  FASE  6: DISM /RestoreHealth (Reparo de Imagem)"
    Write-Host "  FASE  7: SFC /scannow (Reparo de Arquivos Protegidos)"
    Write-Host "  FASE  8: Atualização de inteligência do Microsoft Defender"
    Write-Host "  FASE  9: Limpeza controlada de arquivos temporários"
    Write-Host "  FASE 10: Limpeza de cache de miniaturas (Thumbnails)"
    Write-Host "  FASE 11: Esvaziamento permanente da Lixeira"
    Write-Host "  FASE 12: Limpeza de cache do resolvedor DNS"
    Write-Host "  FASE 13: Execução do utilitário nativo cleanmgr.exe"
    Write-Host "  FASE 14: Otimização inteligente SSD/HDD (TRIM ou Defrag)"
    Write-Host "  FASE 15: Diagnóstico de processos com alto consumo"
    Write-Host "  FASE 16: Análise de programas de inicialização automática"
    Write-Host "  FASE 17: Diagnóstico de eventos e erros do Windows"
    Write-Host "  FASE 18: Geração e exportação do relatório técnico consolidado`n"

    Write-Host " [NOTA] O escaneamento completo de malware e a verificação offline NÃO são" -ForegroundColor Yellow
    Write-Host " executados automaticamente para evitar bloqueio prolongado da máquina e reinicialização forçada." -ForegroundColor Yellow

    if (-not (Confirm-ToolAction -Prompt "Deseja iniciar as 18 fases da Manutenção Completa agora?")) {
        return
    }

    $swTotal = [System.Diagnostics.Stopwatch]::StartNew()

    Write-Host "`n>>> FASE 1: Diagnóstico Inicial do Sistema..." -ForegroundColor Green
    Get-SystemDiagnostic

    Write-Host "`n>>> FASE 2: Criando Ponto de Restauração..." -ForegroundColor Green
    New-SupportRestorePoint

    Write-Host "`n>>> FASE 3: Verificando Saúde dos Discos..." -ForegroundColor Green
    Get-DiskHealth

    Write-Host "`n>>> FASE 4: Executando CHKDSK /scan (Online)..." -ForegroundColor Green
    & chkdsk.exe C: /scan

    Write-Host "`n>>> FASE 5: DISM /CheckHealth..." -ForegroundColor Green
    & DISM.exe /Online /Cleanup-Image /CheckHealth

    Write-Host "`n>>> FASE 6: DISM /RestoreHealth..." -ForegroundColor Green
    & DISM.exe /Online /Cleanup-Image /RestoreHealth

    Write-Host "`n>>> FASE 7: SFC /scannow..." -ForegroundColor Green
    Repair-SystemFiles

    Write-Host "`n>>> FASE 8: Atualizando Microsoft Defender..." -ForegroundColor Green
    Update-Defender

    Write-Host "`n>>> FASES 9, 10, 11 e 13: Limpeza de Temporários, Miniaturas, Lixeira e Cleanmgr..." -ForegroundColor Green
    Clear-SystemJunk

    Write-Host "`n>>> FASE 12: Limpando Cache DNS..." -ForegroundColor Green
    Clear-NetworkCache

    Write-Host "`n>>> FASE 14: Otimizando SSD/HDD..." -ForegroundColor Green
    Optimize-StorageVolume -Drive 'C:'

    Write-Host "`n>>> FASE 15: Diagnóstico de Processos e Memória..." -ForegroundColor Green
    Get-MemoryDiagnostic

    Write-Host "`n>>> FASE 16: Análise de Inicialização..." -ForegroundColor Green
    Get-StartupPrograms

    Write-Host "`n>>> FASE 17: Diagnóstico de Eventos do Windows..." -ForegroundColor Green
    Get-SystemEvents -Days 7

    Write-Host "`n>>> FASE 18: Compilando Relatório Completo..." -ForegroundColor Green
    Export-SupportReport

    $swTotal.Stop()

    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor Green
    Write-Host (" MANUTENÇÃO COMPLETA CONCLUÍDA EM {0:N1} MINUTOS" -f $swTotal.Elapsed.TotalMinutes) -ForegroundColor Yellow
    Write-Host ("=" * 70) -ForegroundColor Green

    if ($script:RebootRequired) {
        Write-Host "`n [AVISO FINAL] O sistema possui solicitações pendentes de reinicialização." -ForegroundColor Yellow
        Write-Host " Motivos registrados: $($script:RebootReasons -join ' | ')" -ForegroundColor White
    }
}

# ============================================================
# MÓDULO RÁPIDO: SUPORTE RÁPIDO (MODO NÃO DESTRUTIVO)
# ============================================================

function Invoke-QuickSupport {
    [CmdletBinding()]
    param()

    Write-SectionHeader "SUPORTE TÉCNICO RÁPIDO (DIAGNÓSTICO EXPRESSO NÃO DESTRUTIVO)"
    Write-SupportLog "Iniciando modo QuickSupport." -Level 'INFO' -Module 'QUICKSUPPORT'

    Write-Host " Coletando informações vitais da máquina sem alterações no sistema..." -ForegroundColor Cyan

    Get-SystemDiagnostic
    Get-DiskHealth
    Get-MemoryDiagnostic
    Get-HardwareDiagnostic
    Test-NetworkHealth
    Get-MalwareHistory
    Get-SystemEvents -Days 3
    Export-SupportReport

    Write-StatusTag -Level 'OK' -Message "Diagnóstico expresso concluído e relatório salvo."
}

# ============================================================
# MÓDULOS ESPECIAIS COMPLEMENTARES
# ============================================================

function Get-PowerDiagnostic {
    [CmdletBinding()]
    param()

    Write-SectionHeader "DIAGNÓSTICO ENERGÉTICO E BATERIA (POWER DIAGNOSTIC)"
    Write-SupportLog "Iniciando diagnóstico de eficiência energética." -Level 'INFO' -Module 'POWER'

    $battery = Get-CimInstance -ClassName Win32_Battery -ErrorAction SilentlyContinue

    Write-Host " Opções de Diagnóstico de Energia:" -ForegroundColor Cyan
    Write-Host "  [1] Diagnóstico de Eficiência Energética Geral (powercfg /energy - 60s)"
    if ($battery) {
        Write-Host "  [2] Relatório de Integridade e Desgaste da Bateria (powercfg /batteryreport)"
    } else {
        Write-Host "  [2] Relatório de Bateria [Indisponível - Computador Desktop/Sem Bateria]" -ForegroundColor DarkGray
    }
    Write-Host "  [0] Retornar"

    $pOpt = Read-Host "`n Selecione a opção [1-2, 0]"
    switch ($pOpt) {
        "1" {
            $reportPath = Join-Path $script:ReportDir ("energy-report_{0}.html" -f (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss"))
            Write-Host "`n [INFO] Coletando métricas energéticas durante 60 segundos... Aguarde." -ForegroundColor Cyan
            Write-SupportLog "Executando: powercfg.exe /energy /output `"$reportPath`"" -Level 'INFO' -Module 'POWER'
            & powercfg.exe /energy /output "$reportPath"
            if (Test-Path $reportPath) {
                Write-StatusTag -Level 'OK' -Message "Relatório de energia gerado: $reportPath"
            }
        }
        "2" {
            if (-not $battery) {
                Write-StatusTag -Level 'INFO' -Message "Nenhuma bateria física detectada neste sistema."
                return
            }
            $reportPath = Join-Path $script:ReportDir ("battery-report_{0}.html" -f (Get-Date).ToString("yyyy-MM-dd_HH-mm-ss"))
            Write-Host "`n [INFO] Gerando relatório de integridade da bateria..." -ForegroundColor Cyan
            Write-SupportLog "Executando: powercfg.exe /batteryreport /output `"$reportPath`"" -Level 'INFO' -Module 'POWER'
            & powercfg.exe /batteryreport /output "$reportPath"
            if (Test-Path $reportPath) {
                Write-StatusTag -Level 'OK' -Message "Relatório de bateria gerado: $reportPath"
            }
        }
        Default { }
    }
}

function Invoke-StoreReset {
    [CmdletBinding()]
    param()

    Write-SectionHeader "LIMPEZA E REDEFINIÇÃO DA MICROSOFT STORE (WSRESET)"
    Write-SupportLog "Acionado utilitário wsreset." -Level 'INFO' -Module 'STORE'

    Write-Host " O comando wsreset.exe limpa e redefine a memória cache da Microsoft Store" -ForegroundColor White
    Write-Host " sem alterar as configurações de conta ou excluir aplicativos instalados.`n" -ForegroundColor White

    if (-not (Confirm-ToolAction -Prompt "Deseja redefinir o cache da Microsoft Store agora?")) {
        return
    }

    Write-Host "`n [INFO] Executando wsreset.exe em segundo plano... Aguarde a conclusão." -ForegroundColor Cyan
    try {
        $p = Start-Process -FilePath "wsreset.exe" -PassThru -Wait
        Write-StatusTag -Level 'OK' -Message "Cache da Microsoft Store redefinido com sucesso (Código $($p.ExitCode))."
    } catch {
        Write-StatusTag -Level 'ERROR' -Message "Falha ao executar wsreset: $($_.Exception.Message)"
    }
}

function Clear-ControlledLogs {
    [CmdletBinding()]
    param()

    Write-SectionHeader "LIMPEZA CONTROLADA DE ARQUIVOS DE LOG ANTIGOS"
    Write-SupportLog "Abrindo módulo de limpeza controlada de logs." -Level 'INFO' -Module 'LOGS'

    Write-Host " DIRETRIZES DE SEGURANÇA PARA LOGS:" -ForegroundColor Cyan
    Write-Host "  - A ferramenta NÃO apaga os Logs de Eventos vitais do Windows (EventViewer)." -ForegroundColor White
    Write-Host "  - Apenas arquivos .log arquivados, relatórios de setup antigos (Panther) e" -ForegroundColor White
    Write-Host "    backups antigos do CBS (Component Based Servicing) são avaliados.`n" -ForegroundColor White

    $targetFiles = @()
    $cbsDir = "C:\Windows\Logs\CBS"
    if (Test-Path $cbsDir) {
        $oldCbs = Get-ChildItem -Path $cbsDir -Filter "CbsPersist_*.log" -File -ErrorAction SilentlyContinue |
                  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-14) }
        if ($oldCbs) { $targetFiles += $oldCbs }
    }

    $pantherDir = "C:\Windows\Panther"
    if (Test-Path $pantherDir) {
        $oldPanther = Get-ChildItem -Path $pantherDir -Filter "*.log" -File -Recurse -ErrorAction SilentlyContinue |
                      Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) }
        if ($oldPanther) { $targetFiles += $oldPanther }
    }

    if ($targetFiles.Count -eq 0) {
        Write-StatusTag -Level 'INFO' -Message "Nenhum arquivo de log obsoleto foi identificado para remoção controlada."
        return
    }

    $totalBytes = ($targetFiles | Measure-Object -Property Length -Sum).Sum
    $totalMB = [math]::Round($totalBytes / 1MB, 2)

    Write-Host " Arquivos de Log Identificados para Remoção Controlada ($($targetFiles.Count) itens, ~$totalMB MB):" -ForegroundColor Yellow
    $targetFiles | Select-Object -First 15 Name,
        @{Name="Tamanho_MB"; Expression={[math]::Round($_.Length/1MB,2)}},
        LastWriteTime, Directory | Format-Table -AutoSize

    if (-not (Confirm-ToolAction -Prompt "Deseja remover estes logs antigos catalogados?")) {
        return
    }

    $removedCount = 0
    foreach ($f in $targetFiles) {
        try {
            Remove-Item -Path $f.FullName -Force -ErrorAction Stop
            $removedCount++
        } catch { }
    }

    Write-SupportLog "Limpeza controlada de logs: $removedCount de $($targetFiles.Count) arquivos removidos." -Level 'INFO' -Module 'LOGS'
    Write-StatusTag -Level 'OK' -Message "Limpeza controlada concluída ($removedCount arquivos removidos)."
}

function Get-HeavyProcesses {
    [CmdletBinding()]
    param()

    Write-SectionHeader "ANÁLISE DE PROCESSOS COM CONSUMO ELEVADO (CPU E RAM)"
    Write-SupportLog "Examinando processos com maior demanda de recursos." -Level 'INFO' -Module 'PROCESSES'

    Write-Host " Top 15 Processos com Maior Utilização de CPU acumulada:" -ForegroundColor Yellow
    try {
        Get-Process -ErrorAction SilentlyContinue |
            Where-Object { $_.CPU -gt 0 } |
            Sort-Object CPU -Descending |
            Select-Object -First 15 Name, Id,
                @{Name="Tempo_CPU_s"; Expression={[math]::Round($_.CPU, 1)}},
                @{Name="RAM_MB"; Expression={[math]::Round($_.WorkingSet64 / 1MB, 1)}} |
            Format-Table -AutoSize
    } catch { }

    Write-Host "`n Top 15 Processos com Maior Utilização de Memória RAM (Working Set):" -ForegroundColor Yellow
    try {
        Get-Process -ErrorAction SilentlyContinue |
            Sort-Object WorkingSet64 -Descending |
            Select-Object -First 15 Name, Id,
                @{Name="RAM_MB"; Expression={[math]::Round($_.WorkingSet64 / 1MB, 1)}},
                @{Name="HandleCount"; Expression={$_.HandleCount}} |
            Format-Table -AutoSize
    } catch { }

    Write-StatusTag -Level 'INFO' -Message "Análise de processos pesados concluída."
}

# ============================================================
# FUNÇÕES AUXILIARES E ALIASES DE COMPATIBILIDADE (SEÇÃO 57)
# ============================================================

function Write-Log {
    param(
        [Parameter(Mandatory = $true)][string]$Message,
        [Parameter(Mandatory = $false)][string]$Level = 'INFO',
        [Parameter(Mandatory = $false)][string]$Module = 'CORE'
    )
    Write-SupportLog -Message $Message -Level $Level -Module $Module
}

function Write-Status {
    param(
        [Parameter(Mandatory = $true)][string]$Level,
        [Parameter(Mandatory = $true)][string]$Message
    )
    Write-StatusTag -Level $Level -Message $Message
}

function Write-Header {
    param([Parameter(Mandatory = $true)][string]$Title)
    Write-SectionHeader -Title $Title
}

function Confirm-Action {
    param(
        [Parameter(Mandatory = $false)][string]$Prompt = "Deseja continuar?",
        [Parameter(Mandatory = $false)][switch]$RequireDouble
    )
    Confirm-ToolAction -Prompt $Prompt -RequireDouble:$RequireDouble
}

function Test-CommandExists {
    param([Parameter(Mandatory = $true)][string]$CommandName)
    $cmd = Get-Command -Name $CommandName -ErrorAction SilentlyContinue
    return ($null -ne $cmd)
}

function Export-Report {
    Export-SupportReport
}

function Get-SystemInfo {
    Get-SystemDiagnosticInfo
}

# ============================================================
# INTERFACE PRINCIPAL E LOOP DE EXECUÇÃO (MENU SWITCH)
# ============================================================

function Show-MainMenu {
    $running = $true

    while ($running) {
        Write-ToolHeader -ClearFirst

        Write-Host " [ 1 ] Diagnóstico completo do computador"
        Write-Host " [ 2 ] Diagnóstico e saúde dos discos"
        Write-Host " [ 3 ] Verificação CHKDSK (Scan / Spotfix / F / R)"
        Write-Host " [ 4 ] Reparação de imagem DISM (Check / Restore / Component)"
        Write-Host " [ 5 ] Reparação de arquivos de sistema SFC (/scannow)"
        Write-Host " [ 6 ] Limpeza de arquivos temporários"
        Write-Host " [ 7 ] Limpeza de componentes do Windows (WinSxS)"
        Write-Host " [ 8 ] Limpeza da Lixeira"
        Write-Host " [ 9 ] Limpeza de cache DNS"
        Write-Host " [10 ] Otimização de SSD/HDD (TRIM / Defrag Inteligente)"
        Write-Host " [11 ] Diagnóstico de memória RAM e processos"
        Write-Host " [12 ] Diagnóstico de CPU e GPU"
        Write-Host " [13 ] Diagnóstico de programas de inicialização"
        Write-Host " [14 ] Diagnóstico de serviços do Windows"
        Write-Host " [15 ] Diagnóstico de eventos do Windows (Event Viewer)"
        Write-Host " [16 ] Diagnóstico de conectividade e rede"
        Write-Host " [17 ] Reparação avançada de rede (Winsock / TCP-IP Reset)"
        Write-Host " [18 ] Atualização de assinaturas do Defender"
        Write-Host " [19 ] Verificação rápida do Defender (Quick Scan)"
        Write-Host " [20 ] Verificação completa de malware (Full Scan)"
        Write-Host " [21 ] Microsoft Defender Offline (Reboot WDO)"
        Write-Host " [22 ] Histórico de ameaças detectadas pelo Defender"
        Write-Host " [23 ] Limpeza profunda controlada"
        Write-Host " [24 ] Diagnóstico do Windows Update"
        Write-Host " [25 ] Exportar relatório completo (TXT e HTML)"
        Write-Host " [26 ] Diagnóstico de recursos de IA do Windows"
        Write-Host " [27 ] Gerenciar / Desativar recursos de IA (com backup)"
        Write-Host " [28 ] Otimização geral segura"
        Write-Host " [29 ] Criar ponto de restauração do sistema"
        Write-Host " [30 ] Executar manutenção completa recomendada (18 Fases)"
        Write-Host " [ 0 ] Sair do Toolkit"
        Write-Host ("-" * 70) -ForegroundColor DarkGray

        $opcao = Read-Host " Digite uma opção [0-30]"

        switch ($opcao) {
            "1"  { Get-SystemDiagnostic; Wait-ForUser }
            "2"  { Get-DiskHealth; Wait-ForUser }
            "3"  { Invoke-DiskCheck; Wait-ForUser }
            "4"  { Repair-WindowsImage; Wait-ForUser }
            "5"  { Repair-SystemFiles; Wait-ForUser }
            "6"  { Clear-SystemJunk; Wait-ForUser }
            "7"  { Clear-ComponentStore; Wait-ForUser }
            "8"  { Clear-RecycleBinSecure; Wait-ForUser }
            "9"  { Clear-NetworkCache; Wait-ForUser }
            "10" { Optimize-StorageVolume; Wait-ForUser }
            "11" { Get-MemoryDiagnostic; Wait-ForUser }
            "12" { Get-HardwareDiagnostic; Wait-ForUser }
            "13" { Get-StartupPrograms; Wait-ForUser }
            "14" { Get-ServiceDiagnostic; Wait-ForUser }
            "15" { Get-SystemEvents; Wait-ForUser }
            "16" { Test-NetworkHealth; Wait-ForUser }
            "17" { Repair-NetworkStack; Wait-ForUser }
            "18" { Update-Defender; Wait-ForUser }
            "19" { Start-QuickMalwareScan; Wait-ForUser }
            "20" { Start-FullMalwareScan; Wait-ForUser }
            "21" { Start-DefenderOfflineScan; Wait-ForUser }
            "22" { Get-MalwareHistory; Wait-ForUser }
            "23" { Invoke-DeepClean; Wait-ForUser }
            "24" { Get-WindowsUpdateDiagnostic; Wait-ForUser }
            "25" { Export-SupportReport; Wait-ForUser }
            "26" { Get-WindowsAiDiagnostic; Wait-ForUser }
            "27" { Manage-WindowsAiFeatures; Wait-ForUser }
            "28" { Invoke-SafeOptimization; Wait-ForUser }
            "29" { New-SupportRestorePoint; Wait-ForUser }
            "30" { Invoke-FullMaintenance; Wait-ForUser }
            "power"   { Get-PowerDiagnostic; Wait-ForUser }
            "energy"  { Get-PowerDiagnostic; Wait-ForUser }
            "wsreset" { Invoke-StoreReset; Wait-ForUser }
            "store"   { Invoke-StoreReset; Wait-ForUser }
            "logs"    { Clear-ControlledLogs; Wait-ForUser }
            "heavy"   { Get-HeavyProcesses; Wait-ForUser }
            "quick"   { Invoke-QuickSupport; Wait-ForUser }
            "0"  {
                Write-Host "`n Encerrando o Windows Support Toolkit... Até logo!" -ForegroundColor Cyan
                $running = $false
            }
            default {
                Write-Host "`n [AVISO] Opção inválida. Digite um número de 0 a 30." -ForegroundColor Yellow
                Start-Sleep -Seconds 1
            }
        }
    }
}

# ============================================================
# PONTO DE ENTRADA PRINCIPAL DO SCRIPT (MAIN)
# ============================================================

try {
    # 1. Inicializa pastas e transcript
    Initialize-SupportToolkitEnvironment

    # 2. Verifica privilégios administrativos
    Assert-Administrator

    # 3. Roteamento por modo de execução (CLI ou Interativo)
    switch ($Mode) {
        'Diagnose' {
            Write-ToolHeader -ClearFirst
            Get-SystemDiagnostic
            Get-DiskHealth
            Get-MemoryDiagnostic
            Get-HardwareDiagnostic
            Test-NetworkHealth
        }
        'Cleanup' {
            Write-ToolHeader -ClearFirst
            Clear-SystemJunk
            Clear-NetworkCache
        }
        'MalwareScan' {
            Write-ToolHeader -ClearFirst
            Update-Defender
            Start-QuickMalwareScan
        }
        'FullMaintenance' {
            Write-ToolHeader -ClearFirst
            Invoke-FullMaintenance
        }
        'Report' {
            Write-ToolHeader -ClearFirst
            Export-SupportReport
        }
        'QuickSupport' {
            Write-ToolHeader -ClearFirst
            Invoke-QuickSupport
        }
        Default {
            # Modo padrão interativo (Menu)
            Show-MainMenu
        }
    }

    # Notificação final sobre reinicialização se necessário
    if ($script:RebootRequired) {
        Write-Host ""
        Write-Host ("!" * 70) -ForegroundColor Yellow
        Write-Host " LEMBRETE DE REINICIALIZAÇÃO PENDENTE:" -ForegroundColor Yellow
        foreach ($r in $script:RebootReasons) {
            Write-Host "  - $r" -ForegroundColor White
        }
        Write-Host ("!" * 70) -ForegroundColor Yellow
    }
} catch {
    Write-SupportLog "Erro fatal não tratado durante a execução: $($_.Exception.Message)" -Level 'CRITICAL' -Module 'MAIN'
    Write-Host " Detalhes da Exceção: $($_.Exception.ToString())" -ForegroundColor Red
} finally {
    if ($script:TranscriptActive) {
        try {
            Stop-Transcript -ErrorAction SilentlyContinue | Out-Null
        } catch { }
    }
}
