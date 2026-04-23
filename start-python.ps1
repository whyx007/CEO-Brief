$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$logDir = Join-Path $root 'logs'
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }
$outLog = Join-Path $logDir 'ceo-brief-python.stdout.log'
$errLog = Join-Path $logDir 'ceo-brief-python.stderr.log'

$existing = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($procId in $existing) {
  Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
}

$pythonExe = 'D:\ProgramData\miniconda3\envs\ceo-brief-py310\python.exe'
$proc = Start-Process -FilePath $pythonExe -ArgumentList '-m uvicorn app:app --host 127.0.0.1 --port 8000' -WorkingDirectory $root -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru -WindowStyle Hidden
Write-Output ("python_exe=" + $pythonExe)
Write-Output ("started_pid=" + $proc.Id)
