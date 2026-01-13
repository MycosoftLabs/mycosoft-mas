# MINDEX Database Status Check Script
# Run this to monitor the progress of ETL syncs

Write-Host "=============================================="
Write-Host "       MINDEX DATABASE STATUS CHECK"
Write-Host "=============================================="
Write-Host ""

# Get current taxa count by source
Write-Host "Taxa by Source:"
Write-Host "---------------"
docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT source, count(*) as count FROM core.taxon GROUP BY source ORDER BY count DESC;"

Write-Host ""
Write-Host "Total Taxa:"
Write-Host "-----------"
docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT count(*) as total_taxa FROM core.taxon;"

Write-Host ""
Write-Host "Taxa by Rank:"
Write-Host "-------------"
docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT rank, count(*) as count FROM core.taxon GROUP BY rank ORDER BY count DESC LIMIT 10;"

Write-Host ""
Write-Host "Taxa by Fungi Type:"
Write-Host "-------------------"
docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT fungi_type, count(*) as count FROM core.taxon WHERE fungi_type IS NOT NULL GROUP BY fungi_type ORDER BY count DESC;"

Write-Host ""
Write-Host "Recent Taxa (Last 10 Added):"
Write-Host "----------------------------"
docker exec mindex-postgres psql -U mindex -d mindex -c "SELECT canonical_name, source, created_at FROM core.taxon ORDER BY created_at DESC LIMIT 10;"

Write-Host ""
Write-Host "=============================================="
Write-Host "Target: 575,000+ species"
Write-Host ""
Write-Host "ETL Sync Jobs Running in Background:"
Write-Host "  - MycoBank A-E: Terminal 10"
Write-Host "  - MycoBank F-M: Terminal 11"
Write-Host "  - MycoBank N-Z: Terminal 12"
Write-Host "  - iNaturalist: Terminal 8 (rate limited)"
Write-Host ""
Write-Host "Run this script again to check progress."
Write-Host "=============================================="
