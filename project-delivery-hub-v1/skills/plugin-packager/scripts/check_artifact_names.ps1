param(
    [string]$AgentRoot,
    [string]$StandardPath,
    [switch]$Json,
    [switch]$FailOnHits
)

$ErrorActionPreference = "Stop"

function Get-PluginRoot {
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $skillDir = Split-Path -Parent $scriptDir
    $skillsDir = Split-Path -Parent $skillDir
    return Split-Path -Parent $skillsDir
}

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required JSON file not found: $Path"
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Resolve-AgentRoot {
    param([string]$PluginRoot)

    if ($AgentRoot) {
        return (Resolve-Path -LiteralPath $AgentRoot).Path
    }

    $workspaceConfigPath = Join-Path $PluginRoot "references\local-workspaces.json"
    $workspaceConfig = Read-JsonFile -Path $workspaceConfigPath
    $workspaceKey = $workspaceConfig.defaultWorkspace
    if (-not $workspaceKey) {
        throw "defaultWorkspace is missing in $workspaceConfigPath. Pass -AgentRoot explicitly."
    }

    $workspace = $workspaceConfig.workspaces.$workspaceKey
    if (-not $workspace -or -not $workspace.agentRoot) {
        throw "agentRoot is missing for workspace '$workspaceKey'. Pass -AgentRoot explicitly."
    }

    return (Resolve-Path -LiteralPath $workspace.agentRoot).Path
}

function Get-RelativePath {
    param(
        [string]$Root,
        [string]$Path
    )
    $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\', '/')
    $pathFull = [System.IO.Path]::GetFullPath($Path)
    $rootWithSlash = $rootFull + [System.IO.Path]::DirectorySeparatorChar
    $rootUri = New-Object System.Uri($rootWithSlash)
    $pathUri = New-Object System.Uri($pathFull)
    $relative = [System.Uri]::UnescapeDataString($rootUri.MakeRelativeUri($pathUri).ToString())
    return $relative.Replace('\', '/')
}

function Test-ExcludedFile {
    param([System.IO.FileInfo]$File)

    if ($File.Name.EndsWith(".bak", [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
    if ($File.Extension -in @(".tmp", ".log", ".pyc")) { return $true }
    if ($File.FullName -match "\\__pycache__\\") { return $true }
    return $false
}

$pluginRoot = Get-PluginRoot
if (-not $StandardPath) {
    $StandardPath = Join-Path $pluginRoot "references\artifact-naming-standard.json"
}

$resolvedAgentRoot = Resolve-AgentRoot -PluginRoot $pluginRoot
$standard = Read-JsonFile -Path $StandardPath
$mappings = @($standard.mappings | Where-Object { $_.action -eq "rename_later" })
$files = Get-ChildItem -LiteralPath $resolvedAgentRoot -Recurse -File -Force | Where-Object { -not (Test-ExcludedFile -File $_) }

$hits = New-Object System.Collections.Generic.List[object]
$seen = New-Object "System.Collections.Generic.HashSet[string]"

foreach ($file in $files) {
    $relativePath = Get-RelativePath -Root $resolvedAgentRoot -Path $file.FullName

    foreach ($mapping in $mappings) {
        $matched = $false

        if ($mapping.currentFileName -and ($file.Name -ieq $mapping.currentFileName)) {
            $matched = $true
        }

        if ($mapping.currentRegex -and ($relativePath -match $mapping.currentRegex)) {
            $matched = $true
        }

        if (-not $matched) {
            continue
        }

        $dedupeKey = "$($mapping.id)|$relativePath"
        if (-not $seen.Add($dedupeKey)) {
            continue
        }

        $hits.Add([pscustomobject]@{
            mappingId = $mapping.id
            stage = $mapping.stage
            ownerSkill = $mapping.ownerSkill
            currentPath = $relativePath
            proposedPattern = $mapping.proposedPattern
            reason = $mapping.reason
        })
    }
}

if ($Json) {
    [pscustomobject]@{
        agentRoot = $resolvedAgentRoot
        standardPath = (Resolve-Path -LiteralPath $StandardPath).Path
        oldNameCount = $hits.Count
        oldNames = $hits
    } | ConvertTo-Json -Depth 8
} else {
    Write-Host "[artifact naming] agentRoot: $resolvedAgentRoot"
    Write-Host "[artifact naming] standard:  $((Resolve-Path -LiteralPath $StandardPath).Path)"
    Write-Host "[artifact naming] old-name hits: $($hits.Count)"

    if ($hits.Count -gt 0) {
        Write-Host ""
        Write-Host "Summary by mapping:"
        $hits |
            Group-Object mappingId, stage, ownerSkill |
            ForEach-Object {
                $parts = $_.Name -split ', '
                [pscustomobject]@{
                    mappingId = $parts[0]
                    stage = $parts[1]
                    ownerSkill = $parts[2]
                    count = $_.Count
                }
            } |
            Sort-Object stage, mappingId |
            Format-Table -AutoSize

        Write-Host ""
        Write-Host "Old-name files:"
        $hits |
            Sort-Object currentPath, mappingId |
            Select-Object currentPath, mappingId, proposedPattern |
            Format-Table -AutoSize -Wrap
    }
}

if ($FailOnHits -and $hits.Count -gt 0) {
    exit 2
}
