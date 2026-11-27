# Runs the four load runs for POST /api/leave-requests and saves raw output.
#   1 user  x 2 runs, 5 users x 2 runs, 60 s steady phase each (plus 10 s warm-up).
# The API must be running on http://127.0.0.1:5001. The database is reset before every run
# so each run starts from the same data.
#
#   powershell -ExecutionPolicy Bypass -File tests\team\perf\run_perf.ps1

# k6 exits with 99 when a threshold is crossed; that is a result to record, not a reason to stop,
# so errors from the native command do not stop the script.
$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Resolve-Path (Join-Path $here "..\..\..")
$python = Join-Path $repo "backend\.venv\Scripts\python.exe"
$k6 = "C:\Program Files\k6\k6.exe"
if (-not (Test-Path $k6)) { $k6 = "k6" }
$results = Join-Path $here "results"
New-Item -ItemType Directory -Force $results | Out-Null

# environment details for the report
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$os = Get-CimInstance Win32_OperatingSystem
$commit = (git -C $repo rev-parse HEAD) 2>$null
$env_lines = @(
  "date: $(Get-Date -Format s)",
  "os: $($os.Caption) $($os.Version)",
  "cpu: $($cpu.Name) ($($cpu.NumberOfCores) cores, $($cpu.NumberOfLogicalProcessors) threads)",
  "ram_gb: $([math]::Round($os.TotalVisibleMemorySize / 1MB, 1))",
  "python: $(& $python --version)",
  "flask: $(& $python -c 'import importlib.metadata as m; print(m.version(\"flask\"), \"werkzeug\", m.version(\"werkzeug\"), \"sqlalchemy\", m.version(\"sqlalchemy\"))')",
  "node: $(node --version)",
  "k6: $(& $k6 version)",
  "server: flask run (werkzeug development server, threaded), SQLite file backend/leave.db",
  "git_commit: $commit"
)
$env_lines | Set-Content (Join-Path $results "environment.txt")

function Invoke-Baseline($label, $seconds) {
  # calibration: the cheapest request the server can answer, 1 user; shows how busy the machine is
  $out = Join-Path $results "baseline_$label.txt"
  & $k6 run --quiet --no-color -e "BASELINE_SECONDS=$seconds" --summary-export (Join-Path $results "baseline_$label.json") (Join-Path $here "baseline_health.js") 2>&1 |
    ForEach-Object { "$_" } | Out-File -FilePath $out -Encoding utf8
  Write-Host "== baseline $label done"
}

Invoke-Baseline "start" 30
foreach ($vus in 1, 5) {
  foreach ($run in 1, 2) {
    $name = "vus${vus}_run${run}"
    Write-Host "== $name : reset database"
    & $python (Join-Path $repo "tests\team\scripts\reset_db.py") | Out-Null
    Invoke-Baseline "pre_$name" 10
    Write-Host "== $name : k6"
    $out = Join-Path $results "$name.txt"
    & $k6 run --quiet --no-color -e "VUS=$vus" --summary-export (Join-Path $results "$name.json") (Join-Path $here "leave_requests.js") 2>&1 |
      ForEach-Object { "$_" } | Out-File -FilePath $out -Encoding utf8
    "k6 exit code: $LASTEXITCODE (0 = all thresholds met, 99 = a threshold was crossed)" | Add-Content -Path $out -Encoding utf8
    Get-Content $out | Select-Object -Last 40
  }
}

Invoke-Baseline "end" 30
