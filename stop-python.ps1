$existing = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if (-not $existing) {
  Write-Output 'no_listener'
  exit 0
}
foreach ($procId in $existing) {
  Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
  Write-Output ("stopped_pid=" + $procId)
}
