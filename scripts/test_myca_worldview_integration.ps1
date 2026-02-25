# MYCA Worldview Integration Test
# Run when MAS (192.168.0.188:8001) and optionally website (localhost:3010) are up.
# Created: Feb 17, 2026

$MAS = "http://192.168.0.188:8001"
$Web = "http://localhost:3010"
$results = @()

# 1. MAS health
try {
    $h = Invoke-RestMethod "$MAS/health" -TimeoutSec 5
    $results += "[PASS] MAS health: $($h.status)"
} catch {
    $results += "[FAIL] MAS health: $($_.Exception.Message)"
    $results
    exit 1
}

# 2. MAS world - check for new fields
try {
    $w = Invoke-RestMethod "$MAS/api/myca/world" -TimeoutSec 10
    $keys = ($w.PSObject.Properties).Name
    $hasNlm = $keys -contains "nlm"
    $hasEarthlive = $keys -contains "earthlive"
    $hasPresence = $keys -contains "presence"
    if ($hasNlm -and $hasEarthlive -and $hasPresence) {
        $results += "[PASS] MAS world has nlm, earthlive, presence"
    } else {
        $results += "[WARN] MAS world missing new fields (nlm=$hasNlm earthlive=$hasEarthlive presence=$hasPresence). Deploy updated MAS."
    }
} catch {
    $results += "[FAIL] MAS world: $($_.Exception.Message)"
}

# 3. Website world proxy (optional)
try {
    $rw = Invoke-RestMethod "$Web/api/myca/consciousness/world" -TimeoutSec 15
    $rkeys = ($rw.PSObject.Properties).Name
    $results += "[PASS] Website world proxy returned: $($rkeys -join ', ')"
} catch {
    $results += "[SKIP] Website world: $($_.Exception.Message) (dev server may be down)"
}

$results -join "`n"
