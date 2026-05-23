param(
  [ValidateSet("company-dev", "company-jimmy", "both")]
  [string]$Target,
  [string]$SourceRoot,
  [switch]$DryRun,
  [switch]$SkipCache
)

$ErrorActionPreference = "Stop"

$PrivateWedocConfigFileNames = @(
  "wedoc-smartsheet-targets.json",
  "wedoc-smartsheet-targets.local.json"
)
$PrivateWedocDirectoryNames = @(
  "wedoc-smartsheet-receipts"
)
$PackageExcludedFilePatterns = @("*.bak", "*.tmp", "*.log", "*.pyc") + $PrivateWedocConfigFileNames

function Get-FullPath {
  param([string]$Path)
  return [System.IO.Path]::GetFullPath($Path)
}

function Get-PluginRoot {
  if ($SourceRoot) {
    return (Resolve-Path -LiteralPath $SourceRoot).Path
  }
  $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
  $skillRoot = Split-Path -Parent $scriptDir
  $skillsRoot = Split-Path -Parent $skillRoot
  return Split-Path -Parent $skillsRoot
}

function Read-Utf8Text {
  param([string]$Path)
  $resolvedPath = (Resolve-Path -LiteralPath $Path).Path
  $encoding = New-Object System.Text.UTF8Encoding($false, $true)
  return [System.IO.File]::ReadAllText($resolvedPath, $encoding)
}

function Assert-JsonFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    throw "Missing JSON file: $Path"
  }
  return Read-Utf8Text $Path | ConvertFrom-Json
}

function Resolve-PluginRelativePath {
  param(
    [string]$PluginRoot,
    [string]$Path
  )
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return $Path
  }
  return Join-Path $PluginRoot $Path
}

function Get-AgentBundleInfo {
  param(
    [string]$PluginRoot,
    [object]$PackageTargets
  )
  $agentBundle = $PackageTargets.agentBundle
  if (-not $agentBundle -or -not [bool]$agentBundle.enabled) {
    return $null
  }

  $workspaceConfigPath = [string]$agentBundle.workspaceConfigPath
  if ([string]::IsNullOrWhiteSpace($workspaceConfigPath)) {
    throw "agentBundle.workspaceConfigPath is required when agentBundle is enabled"
  }
  $workspaceConfigPath = Resolve-PluginRelativePath -PluginRoot $PluginRoot -Path $workspaceConfigPath
  $workspaceConfig = Assert-JsonFile $workspaceConfigPath

  $workspaceKey = [string]$agentBundle.workspaceKey
  if ([string]::IsNullOrWhiteSpace($workspaceKey)) {
    $workspaceKey = [string]$workspaceConfig.defaultWorkspace
  }
  if ([string]::IsNullOrWhiteSpace($workspaceKey)) {
    throw "agentBundle.workspaceKey or local-workspaces.defaultWorkspace is required"
  }

  $workspace = $workspaceConfig.workspaces.$workspaceKey
  if (-not $workspace) {
    throw "Workspace '$workspaceKey' not found in $workspaceConfigPath"
  }
  $agentRoot = [string]$workspace.agentRoot
  if ([string]::IsNullOrWhiteSpace($agentRoot)) {
    throw "Workspace '$workspaceKey' does not define agentRoot"
  }
  if (-not (Test-Path -LiteralPath $agentRoot)) {
    throw "agentBundle source .agent does not exist: $agentRoot"
  }

  $targetRelativePath = [string]$agentBundle.targetRelativePath
  if ([string]::IsNullOrWhiteSpace($targetRelativePath)) {
    $targetRelativePath = ".agent"
  }
  if ([System.IO.Path]::IsPathRooted($targetRelativePath)) {
    throw "agentBundle.targetRelativePath must be relative: $targetRelativePath"
  }

  return [PSCustomObject]@{
    WorkspaceKey = $workspaceKey
    SourceAgentRoot = (Resolve-Path -LiteralPath $agentRoot).Path
    TargetRelativePath = $targetRelativePath
    PluginAgentRoot = Join-Path $PluginRoot $targetRelativePath
  }
}

function Assert-BundledDiagramAssets {
  param([string]$PluginRoot)
  $diagramRoot = Join-Path $PluginRoot "skills\plugin-packager\assets\diagrams"
  $requiredDiagrams = @(
    "专案交付中枢_主流程图.svg",
    "专案交付中枢_技能与agent架构图.svg",
    "专案交付中枢_工作区与agent结构树.svg"
  )
  foreach ($diagramName in $requiredDiagrams) {
    $diagramPath = Join-Path $diagramRoot $diagramName
    if (-not (Test-Path -LiteralPath $diagramPath)) {
      throw "Missing bundled diagram asset: $diagramPath"
    }
    $diagramText = Read-Utf8Text $diagramPath
    if (-not $diagramText.Contains("<svg")) {
      throw "Bundled diagram asset is not a readable SVG: $diagramPath"
    }
  }
  Write-Host "[ok] bundled diagrams verified"
}

function Assert-UsageGuide {
  param([string]$PluginRoot)
  $usagePath = Join-Path $PluginRoot "USAGE.md"
  if (-not (Test-Path -LiteralPath $usagePath)) {
    throw "Missing usage guide: $usagePath"
  }
  $usageText = Read-Utf8Text $usagePath
  $requiredTokens = @(
    "项目工作区",
    "<workspaceRoot>\.agent",
    "local-workspaces.json"
  )
  foreach ($token in $requiredTokens) {
    if (-not $usageText.Contains($token)) {
      throw "Usage guide missing required content '$token': $usagePath"
    }
  }
  Write-Host "[ok] usage guide verified"
}

function Remove-PackagingExclusions {
  param([string]$Destination)
  if (-not (Test-Path -LiteralPath $Destination)) {
    return
  }
  Get-ChildItem -LiteralPath $Destination -Recurse -Directory -Force |
    Where-Object { $_.Name -eq "__pycache__" -or $PrivateWedocDirectoryNames -contains $_.Name } |
    Sort-Object FullName -Descending |
    Remove-Item -Recurse -Force
  Get-ChildItem -LiteralPath $Destination -Recurse -File -Force |
    Where-Object { $_.Name -like "*.bak" -or $_.Name -like "*.tmp" -or $_.Name -like "*.log" -or $_.Name -like "*.pyc" -or $PrivateWedocConfigFileNames -contains $_.Name } |
    Remove-Item -Force
  Get-ChildItem -LiteralPath $Destination -Recurse -Directory -Force |
    Sort-Object FullName -Descending |
    Where-Object { -not (Get-ChildItem -LiteralPath $_.FullName -Force) } |
    Remove-Item -Force
}

function Invoke-Mirror {
  param(
    [string]$Source,
    [string]$Destination,
    [string]$Label
  )
  $sourcePath = (Resolve-Path -LiteralPath $Source).Path.TrimEnd('\')
  $destinationPath = Get-FullPath $Destination
  if ($sourcePath.Equals($destinationPath.TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host "[skip] $Label already points to source: $destinationPath"
    return
  }
  if ($DryRun) {
    Write-Host "[dry-run] mirror $Label`: $sourcePath -> $destinationPath"
    return
  }
  New-Item -ItemType Directory -Force -Path $destinationPath | Out-Null
  robocopy $sourcePath $destinationPath /MIR /XD __pycache__ .git $PrivateWedocDirectoryNames /XF $PackageExcludedFilePatterns | Out-Null
  if ($LASTEXITCODE -gt 7) {
    throw "robocopy failed for $Label with exit code $LASTEXITCODE"
  }
  Remove-PackagingExclusions -Destination $destinationPath
  Write-Host "[ok] mirrored $Label`: $destinationPath"
}

function Test-NoOldRuntimeIds {
  param(
    [string[]]$Roots,
    [string]$BundledAgentRelativePath
  )
  $legacyPluginId = "new" + "dawho" + "-api-delivery-chain"
  $legacyMarketplace = "jimmy" + "-local"
  $tokens = @(
    ("{0}@{1}" -f $legacyPluginId, $legacyMarketplace),
    ("[marketplaces.{0}]" -f $legacyMarketplace),
    ('"name": "{0}"' -f $legacyPluginId),
    ('"name": "{0}"' -f $legacyMarketplace)
  )
  $extensions = @(".json", ".md", ".yaml", ".yml", ".ps1", ".py", ".txt", ".toml", ".mmd", ".svg")
  $hits = New-Object System.Collections.Generic.List[string]
  $normalizedAgentRelativePath = $null
  if (-not [string]::IsNullOrWhiteSpace($BundledAgentRelativePath)) {
    $normalizedAgentRelativePath = $BundledAgentRelativePath.Trim("\", "/")
  }
  foreach ($root in ($Roots | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    $rootPath = (Resolve-Path -LiteralPath $root).Path.TrimEnd('\')
    Get-ChildItem -LiteralPath $root -Recurse -File -Force |
      Where-Object {
        $relativePath = $_.FullName.Substring($rootPath.Length).TrimStart('\')
        $isBundledAgentFile = $false
        if ($normalizedAgentRelativePath) {
          $isBundledAgentFile =
            $relativePath.StartsWith($normalizedAgentRelativePath + "\", [System.StringComparison]::OrdinalIgnoreCase)
        }
        $_.Name -notlike "*.bak" -and
        $_.FullName -notmatch "\\__pycache__\\" -and
        -not $isBundledAgentFile -and
        $extensions -contains $_.Extension.ToLowerInvariant()
      } |
      ForEach-Object {
        $text = Read-Utf8Text $_.FullName
        foreach ($token in $tokens) {
          if ($text.Contains($token)) {
            $hits.Add("$($_.FullName): $token")
          }
        }
      }
  }
  if ($hits.Count -gt 0) {
    throw "Old runtime ids found:`n$($hits -join "`n")"
  }
}

function Test-NoAgentLegacyTokens {
  param([string[]]$Roots)
  $legacyDotDir = "." + "base"
  $tokens = @(
    $legacyDotDir,
    ("base" + "Root"),
    ("base" + "Bundle"),
    ("base" + "-root"),
    ("BASE" + "_ROOT"),
    ("--base" + "-root"),
    ("--base" + "-dir"),
    ("PROJECT_" + "BASE" + "_ROOT")
  )
  $extensions = @(".json", ".md", ".yaml", ".yml", ".ps1", ".py", ".txt", ".toml", ".svg", ".mmd")
  $hits = New-Object System.Collections.Generic.List[string]
  foreach ($root in ($Roots | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    Get-ChildItem -LiteralPath $root -Recurse -Directory -Force |
      Where-Object { $_.Name -eq $legacyDotDir } |
      ForEach-Object { $hits.Add("$($_.FullName): legacy directory") }
    Get-ChildItem -LiteralPath $root -Recurse -File -Force |
      Where-Object {
        $_.Name -notlike "*.bak" -and
        $_.FullName -notmatch "\\__pycache__\\" -and
        $extensions -contains $_.Extension.ToLowerInvariant()
      } |
      ForEach-Object {
        $text = Read-Utf8Text $_.FullName
        foreach ($token in $tokens) {
          if ($text.Contains($token)) {
            $hits.Add("$($_.FullName): $token")
          }
        }
      }
  }
  if ($hits.Count -gt 0) {
    throw "Legacy agent path tokens found:`n$($hits -join "`n")"
  }
  Write-Host "[ok] no legacy .agent predecessor paths found"
}

function Test-NoDeprecatedWorkspaceSnapshots {
  param([string[]]$Roots)
  $hits = New-Object System.Collections.Generic.List[string]
  foreach ($root in ($Roots | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    $workspaceSnapshotDir = Join-Path $root ".agent\workspaces"
    if (Test-Path -LiteralPath $workspaceSnapshotDir) {
      $hits.Add($workspaceSnapshotDir)
    }
  }
  if ($hits.Count -gt 0) {
    throw "Deprecated workspace snapshot directories found. Use .agent\config\chain-workspace.json only:`n$($hits -join "`n")"
  }
  Write-Host "[ok] no deprecated .agent workspace snapshot directories found"
}

function Test-NoWedocSecrets {
  param([string[]]$Roots)
  $webhookPattern = "https://qyapi\.weixin\.qq\.com/cgi-bin/wedoc/smartsheet/webhook\?key=[A-Za-z0-9_-]{8,}"
  $extensions = @(".json", ".jsonl", ".md", ".yaml", ".yml", ".ps1", ".py", ".txt", ".toml", ".mmd", ".svg")
  $hits = New-Object System.Collections.Generic.List[string]
  foreach ($root in ($Roots | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $root)) { continue }
    Get-ChildItem -LiteralPath $root -Recurse -Directory -Force |
      Where-Object { $PrivateWedocDirectoryNames -contains $_.Name } |
      ForEach-Object {
        $hits.Add("$($_.FullName): private WeDoc smartsheet receipt directory")
      }
    Get-ChildItem -LiteralPath $root -Recurse -File -Force |
      Where-Object {
        $_.Name -notlike "*.bak" -and
        $_.FullName -notmatch "\\__pycache__\\" -and
        $extensions -contains $_.Extension.ToLowerInvariant()
      } |
      ForEach-Object {
        if ($PrivateWedocConfigFileNames -contains $_.Name) {
          $hits.Add("$($_.FullName): private WeDoc smartsheet config file")
        } else {
          $text = Read-Utf8Text $_.FullName
          if ([regex]::IsMatch($text, $webhookPattern)) {
            $hits.Add("$($_.FullName): WeDoc smartsheet webhook URL")
          }
        }
      }
  }
  if ($hits.Count -gt 0) {
    throw "Private WeDoc smartsheet configuration or webhook URL found in package roots:`n$($hits -join "`n")"
  }
  Write-Host "[ok] no private WeDoc smartsheet config or webhook URLs found"
}

$pluginRoot = Get-PluginRoot
$targetConfigPath = Join-Path $pluginRoot "references\package-targets.json"
$packageTargets = Assert-JsonFile $targetConfigPath
$manifestPath = Join-Path $pluginRoot ".codex-plugin\plugin.json"
$manifest = Assert-JsonFile $manifestPath

if ($manifest.name -ne $packageTargets.pluginId) {
  throw "plugin.json name '$($manifest.name)' does not match package-targets pluginId '$($packageTargets.pluginId)'"
}

if (-not $Target) {
  $Target = [string]$packageTargets.defaultPackageTarget
}

Assert-UsageGuide -PluginRoot $pluginRoot
Assert-BundledDiagramAssets -PluginRoot $pluginRoot
$agentBundleInfo = Get-AgentBundleInfo -PluginRoot $pluginRoot -PackageTargets $packageTargets
if ($agentBundleInfo) {
  Invoke-Mirror -Source $agentBundleInfo.SourceAgentRoot -Destination $agentBundleInfo.PluginAgentRoot -Label "$($agentBundleInfo.WorkspaceKey) .agent bundle"
}

$targetNames = if ($Target -eq "both") { @("company-jimmy", "company-dev") } else { @($Target) }
$syncedRoots = New-Object System.Collections.Generic.List[string]

foreach ($targetName in $targetNames) {
  $targetInfo = $packageTargets.targets.$targetName
  if (-not $targetInfo) {
    throw "Target not found in package-targets.json: $targetName"
  }

  $marketplacePath = [string]$targetInfo.marketplacePath
  $marketplace = Assert-JsonFile $marketplacePath
  if ($marketplace.name -ne $targetName) {
    throw "Marketplace name '$($marketplace.name)' does not match target '$targetName'"
  }
  $pluginEntry = @($marketplace.plugins | Where-Object { $_.name -eq $packageTargets.pluginId })[0]
  if (-not $pluginEntry) {
    throw "Marketplace '$targetName' does not list plugin '$($packageTargets.pluginId)'"
  }

  $sourceRoot = [string]$targetInfo.sourceRoot
  $targetPluginRoot = Join-Path $sourceRoot ("plugins\" + [string]$packageTargets.pluginId)
  Invoke-Mirror -Source $pluginRoot -Destination $targetPluginRoot -Label "$targetName marketplace"
  $syncedRoots.Add($targetPluginRoot)

  if (-not $SkipCache) {
    $cacheRoot = Join-Path $env:USERPROFILE (".codex\plugins\cache\" + $targetName + "\" + [string]$packageTargets.pluginId + "\" + [string]$manifest.version)
    Invoke-Mirror -Source $pluginRoot -Destination $cacheRoot -Label "$targetName cache"
    $syncedRoots.Add($cacheRoot)
  }
}

if (-not $DryRun) {
  $rootsToScan = @($pluginRoot) + @($syncedRoots.ToArray())
  $bundledAgentRelativePath = if ($agentBundleInfo) { $agentBundleInfo.TargetRelativePath } else { $null }
  Test-NoOldRuntimeIds -Roots $rootsToScan -BundledAgentRelativePath $bundledAgentRelativePath
  Test-NoAgentLegacyTokens -Roots $rootsToScan
  Test-NoDeprecatedWorkspaceSnapshots -Roots $rootsToScan
  Test-NoWedocSecrets -Roots $rootsToScan
}

Write-Host "[done] package target: $Target"
Write-Host "[done] local URI: $($packageTargets.localMaintenanceUri)"
Write-Host "[done] default package URI: $($packageTargets.defaultPackageUri)"
