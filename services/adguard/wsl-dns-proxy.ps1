#Requires -RunAsAdministrator
# WSL2 DNS Relay Setup — starts a Python UDP+TCP relay on Windows to AdGuard Home in WSL2
# Run once as Administrator. Registers a boot task to auto-start on every login.
param([switch]$SkipTaskRegistration)

$ErrorActionPreference = "Stop"
$TaskName    = "WSL2-DNS-Relay"
$RelayScript = "\\wsl$\Ubuntu\home\enzo\ai-lab\services\adguard\wsl-dns-relay.py"

function Get-WinLanIp {
    $raw = ipconfig
    foreach ($line in $raw) {
        if ($line -match 'IPv4 Address.*?:\s*(192\.168\.\d+\.\d+)') {
            return $Matches[1]
        }
    }
    throw "Could not detect Windows LAN IP from ipconfig."
}

function Get-PythonW {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cmd2 = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd2) {
        $pw = Join-Path (Split-Path $cmd2.Source) "pythonw.exe"
        if (Test-Path $pw) { return $pw }
    }
    throw "pythonw.exe not found. Is Python installed on Windows?"
}

function Set-Firewall {
    $port = 53
    $ruleName = "AdGuardHome-DNS-WSL2"
    netsh advfirewall firewall delete rule name="$ruleName" 2>$null
    netsh advfirewall firewall delete rule name="${ruleName}-UDP" 2>$null
    netsh advfirewall firewall add rule name="$ruleName" dir=in action=allow protocol=TCP localport=$port | Out-Null
    netsh advfirewall firewall add rule name="${ruleName}-UDP" dir=in action=allow protocol=UDP localport=$port | Out-Null
    Write-Host "Firewall: TCP+UDP port $port opened."
}

function Clear-OldPortProxy {
    $lines = netsh interface portproxy show v4tov4 2>$null
    foreach ($line in $lines) {
        if ($line -match '^\s*(\S+)\s+53\s+') {
            $addr = $Matches[1]
            netsh interface portproxy delete v4tov4 listenaddress=$addr listenport=53 2>$null
            Write-Host "Removed old portproxy rule for ${addr}:53"
        }
    }
}

function Start-Relay {
    $pythonw = Get-PythonW
    Write-Host "Starting DNS relay via: $pythonw"
    Start-Process -FilePath $pythonw -ArgumentList "`"$RelayScript`"" -WindowStyle Hidden
    Write-Host "DNS relay started (background, no window)."
}

function Register-BootTask {
    $existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Boot task '$TaskName' already exists. Updating..."
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    $pythonw  = Get-PythonW
    $action   = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$RelayScript`""
    $trigger  = New-ScheduledTaskTrigger -AtLogOn
    $trigger.Delay = "PT30S"
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
    $principal = New-ScheduledTaskPrincipal -UserId (whoami) -RunLevel Highest
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "WSL2 DNS relay for AdGuard Home" | Out-Null
    Write-Host "Boot task '$TaskName' registered -- auto-starts 30s after login."
}

# Entry point
Clear-OldPortProxy
Set-Firewall
Start-Relay

if (-not $SkipTaskRegistration) {
    Register-BootTask
    $winIp = Get-WinLanIp
    $webUi = "http://" + $winIp + ":3000"
    Write-Host ""
    Write-Host "=== Setup complete ==="
    Write-Host "Set DNS on your devices to: $winIp"
    Write-Host "AdGuard Home web UI: $webUi"
}
