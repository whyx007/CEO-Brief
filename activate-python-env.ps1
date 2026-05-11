$envRoot = 'D:\ProgramData\miniconda3\envs\ceo-brief-py310'
$env:Path = "$envRoot;$envRoot\Scripts;$env:Path"
$env:CONDA_PREFIX = $envRoot
$env:CONDA_DEFAULT_ENV = 'ceo-brief-py310'
Write-Output "activated_env=ceo-brief-py310"
Write-Output ("python=" + (Get-Command python).Source)
python --version
