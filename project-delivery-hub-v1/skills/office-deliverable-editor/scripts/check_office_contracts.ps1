$ErrorActionPreference = "Stop"

$PluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$Errors = New-Object 'System.Collections.Generic.List[string]'
$Checks = 0

function Get-SkillText {
  param([Parameter(Mandatory = $true)][string]$RelativePath)
  $path = Join-Path $PluginRoot $RelativePath
  return Get-Content -LiteralPath $path -Raw -Encoding UTF8
}

function Add-Error {
  param([Parameter(Mandatory = $true)][string]$Message)
  $Errors.Add($Message) | Out-Null
}

function Test-ForbiddenRegex {
  param(
    [Parameter(Mandatory = $true)][string]$RelativePath,
    [Parameter(Mandatory = $true)][object[]]$Patterns
  )
  $text = Get-SkillText -RelativePath $RelativePath
  foreach ($entry in $Patterns) {
    $script:Checks += 1
    $label = $entry[0]
    $pattern = $entry[1]
    if ([regex]::IsMatch($text, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
      Add-Error "$RelativePath`: forbidden pattern still present: $label"
    }
  }
}

function Test-RequiredTokens {
  param(
    [Parameter(Mandatory = $true)][string]$RelativePath,
    [Parameter(Mandatory = $true)][string[]]$Tokens
  )
  $text = Get-SkillText -RelativePath $RelativePath
  foreach ($token in $Tokens) {
    $script:Checks += 1
    if (-not $text.Contains($token)) {
      Add-Error "$RelativePath`: missing required token '$token'"
    }
  }
}

$backupWritePatterns = @(
  @('Copy-Item to .bak', 'Copy-Item[^\r\n]+\.bak'),
  @('path plus .bak', '\+\s*[''"]\.bak[''"]'),
  @('output backup variable', '\$backup\s*=\s*\$outputFull\s*\+\s*[''"]\.bak[''"]')
)

@(
  'skills/delivery-format-checker/scripts/rebuild_api_xlsx_api_list_from_text.ps1',
  'skills/delivery-format-checker/scripts/rebuild_api_xlsx_detail_sheets_from_text.ps1',
  'skills/native-vsdx-sequence-writer/scripts/build_native_visio_sequence.ps1'
) | ForEach-Object {
  Test-ForbiddenRegex -RelativePath $_ -Patterns $backupWritePatterns
}

$refreshSameNameBak = -join @([char]0x5237, [char]0x65B0, [char]0x540C, [char]0x540D)
$backupCopyLoop = (-join @([char]0x5099, [char]0x4EFD)) + '/' + (-join @([char]0x8907, [char]0x88FD))
$adjacentBak = -join @([char]0x76F8, [char]0x90BB)
$backupPromisePatterns = @(
  @('refresh same-name .bak', ([regex]::Escape($refreshSameNameBak) + '\s*`?\.bak`?')),
  @('backup/copy repair loop', [regex]::Escape($backupCopyLoop)),
  @('adjacent .bak promise', ([regex]::Escape($adjacentBak) + '\s*`?\.bak`?')),
  @('at most one adjacent backup', 'at most one adjacent backup')
)

@(
  'skills/delivery-format-checker/USAGE.md',
  'skills/api-detail-tsd-sync/USAGE.md',
  'skills/native-vsdx-sequence-writer/SKILL.md',
  'skills/native-vsdx-sequence-writer/references/native-vsdx-deep-rules.md'
) | ForEach-Object {
  Test-ForbiddenRegex -RelativePath $_ -Patterns $backupPromisePatterns
}

Test-RequiredTokens -RelativePath 'skills/office-deliverable-editor/SKILL.md' -Tokens @(
  '"schemaVersion": "1.0.0"',
  '"claimId":',
  '"modifiedFiles":',
  '"changeSummary":',
  '"validationCommands":',
  '"blockers":',
  '"risks":',
  'worker-results.json'
)

$planTokens = @(
  'schemaVersion: "1.0.0"',
  'claimId',
  'targetFiles[]',
  'allowedOperations[]',
  'forbiddenOperations[]',
  'validation[]',
  'modifiedFiles',
  'validationCommands'
)

@(
  'skills/delivery-format-checker/SKILL.md',
  'skills/api-detail-tsd-sync/SKILL.md'
) | ForEach-Object {
  Test-RequiredTokens -RelativePath $_ -Tokens $planTokens
}

if ($Errors.Count -gt 0) {
  [pscustomobject]@{
    status = 'failed'
    errors = @($Errors)
  } | ConvertTo-Json -Depth 4
  exit 1
}

[pscustomobject]@{
  status = 'passed'
  checks = $Checks
} | ConvertTo-Json -Depth 4
