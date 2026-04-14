# Cross-system LAN health checks (MAS, MINDEX, Sandbox, Voice Legion, Earth-2 Legion)
# Apr 13, 2026 — run from a PC on 192.168.0.0/24

$ErrorActionPreference = "Continue"
$targets = @(
    @{ Name = "MAS orchestrator"; Url = "http://192.168.0.188:8001/health" },
    @{ Name = "MINDEX API"; Url = "http://192.168.0.189:8000/health" },
    @{ Name = "Sandbox website"; Url = "http://192.168.0.187:3000/api/health" },
    @{ Name = "PersonaPlex bridge"; Url = "http://192.168.0.241:8999/health" },
    @{ Name = "Earth-2 API"; Url = "http://192.168.0.249:8220/health" }
)

foreach ($t in $targets) {
    try {
        $r = Invoke-WebRequest -Uri $t.Url -UseBasicParsing -TimeoutSec 6
        Write-Host ("OK  {0,-24} {1} -> {2}" -f $t.Name, $t.Url, $r.StatusCode)
    }
    catch {
        Write-Host ("FAIL {0,-24} {1} -> {2}" -f $t.Name, $t.Url, $_.Exception.Message)
    }
}
