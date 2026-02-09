$ErrorActionPreference = "Continue"

$containerName = "physicsnemo-service"

Write-Host "[*] Stopping $containerName..."
$running = docker ps --filter "name=^$containerName$" --format "{{.Names}}"
if ($running -eq $containerName) {
    docker stop $containerName | Out-Null
}

Write-Host "[*] Removing $containerName..."
$existing = docker ps -a --filter "name=^$containerName$" --format "{{.Names}}"
if ($existing -eq $containerName) {
    docker rm $containerName | Out-Null
}

Write-Host "[+] PhysicsNeMo service stopped"
