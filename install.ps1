param(
    [Parameter(Mandatory = $true)]
    [string]$CustomNodesPath
)
$ErrorActionPreference = 'Stop'
$taskSource = $PSScriptRoot
$taskCustomNodes = (Resolve-Path -LiteralPath $CustomNodesPath).Path
$taskDestination = Join-Path $taskCustomNodes 'comfyui_emotional_gallery'
if (Test-Path -LiteralPath $taskDestination) {
    throw "Destination already exists: $taskDestination. Update its files explicitly to preserve local changes."
}
New-Item -ItemType Directory -Path $taskDestination | Out-Null
foreach ($taskItem in @('__init__.py', 'emotions.py', 'gallery.py', 'model_profiles.py', 'nodes.py', 'routes.py', 'triggers.py', 'web', 'README.md', 'README.ru.md', 'CHANGELOG.md', 'LICENSE', 'pyproject.toml')) {
    Copy-Item -LiteralPath (Join-Path $taskSource $taskItem) -Destination $taskDestination -Recurse
}
Write-Output "Installed: $taskDestination"
Write-Output 'Restart ComfyUI and refresh the browser with Ctrl+F5.'
