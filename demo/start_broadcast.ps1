$ErrorActionPreference = 'Stop'
$demoPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $demoPath
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "가상환경 Python을 찾을 수 없습니다: $pythonExe"
}
if (-not $env:ELECTION_REVIEW_KEY) {
    $env:ELECTION_REVIEW_KEY = 'demo-local-only'
}
Set-Location -LiteralPath $demoPath

# Do not start a second Uvicorn instance on the fixed broadcast port.
$portInUse = $false
$tcpProbe = [System.Net.Sockets.TcpClient]::new()
try {
    $pendingConnect = $tcpProbe.BeginConnect('127.0.0.1', 8000, $null, $null)
    if ($pendingConnect.AsyncWaitHandle.WaitOne(500)) {
        try {
            $tcpProbe.EndConnect($pendingConnect)
            $portInUse = $true
        } catch {
            $portInUse = $false
        }
        $pendingConnect.AsyncWaitHandle.Close()
    }
} finally {
    $tcpProbe.Close()
}

if ($portInUse) {
    $healthOk = $false
    try {
        $healthResponse = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 2
        $healthOk = $healthResponse.StatusCode -eq 200
    } catch {
        $healthOk = $false
    }

    if ($healthOk) {
        Write-Host '8000번에서 서버가 이미 응답 중입니다. 중복 실행은 하지 않았습니다.'
        Write-Host '수정 내용을 적용하려면 기존 서버 터미널에서 Ctrl+C로 종료한 뒤 이 스크립트를 다시 실행하세요.'
    } else {
        Write-Host '8000번 포트가 사용 중입니다. 충돌 방지를 위해 새 서버를 시작하지 않았습니다.'
        Write-Host '기존 프로그램을 확인한 뒤, 개표 서버가 맞다면 종료하고 다시 실행하세요.'
    }
    return
}

& $pythonExe -m uvicorn app:app --host 127.0.0.1 --port 8000
