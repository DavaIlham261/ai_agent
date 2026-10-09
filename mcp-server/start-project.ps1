param(
    [Parameter(Mandatory=$true)][string]$ProjectId,
    [Parameter(Mandatory=$true)][string]$ProjectPath,
    [int]$Port = 8100
)

docker rm -f $ProjectId 2>$null

docker run -d --name $ProjectId `
    -p ${Port}:8100 `
    -v "${ProjectPath}:/app/workspace" `
    -e ROOT_PATH="/app/workspace" `
    mcp-server-image

Write-Host "MCP Server '$ProjectId' jalan di port $Port -> $ProjectPath"
Write-Host ""
Write-Host "Tambahkan ke projects.yaml di backend (sekali saja per project):"
Write-Host "  ${ProjectId}:"
Write-Host "    tailscale_ip: 100.121.100.110"
Write-Host "    port: $Port"
Write-Host "    root_path: `"/app/workspace`""
