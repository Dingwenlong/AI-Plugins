param(
  [string]$LibraryDir = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($LibraryDir)) {
  $LibraryDir = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\references\native-shape-library'))
}

$manifestPath = Join-Path $LibraryDir 'manifest.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
  throw "Native shape library manifest not found: $manifestPath"
}

$manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
$required = @(
  'page-title',
  'user-participant-head',
  'actor-head',
  'participant-head-box',
  'object-participant-lifeline',
  'clipped-header-tab',
  'uml-fragment-frame',
  'section-divider',
  'orange-pointer-strip',
  'alt-condition-label',
  'note-card',
  'ref-common-svg-block'
)

$seen = @{}
$errors = New-Object System.Collections.Generic.List[string]

foreach ($entry in @($manifest.templates)) {
  $name = [string]$entry.name
  $file = [string]$entry.file
  if ([string]::IsNullOrWhiteSpace($name)) {
    $errors.Add('Template entry missing name')
    continue
  }
  if ([string]::IsNullOrWhiteSpace($file)) {
    $errors.Add("Template '$name' missing file")
    continue
  }

  $path = Join-Path $LibraryDir $file
  if (-not (Test-Path -LiteralPath $path)) {
    $errors.Add("Template '$name' file not found: $path")
    continue
  }

  try {
    $template = Get-Content -Raw -Encoding UTF8 -LiteralPath $path | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace([string]$template.name)) {
      $errors.Add("Template '$name' JSON missing name")
    }
    if ([string]::IsNullOrWhiteSpace([string]$template.type)) {
      $errors.Add("Template '$name' JSON missing type")
    }
    $seen[$name] = $true
  }
  catch {
    $errors.Add("Template '$name' JSON parse failed: $($_.Exception.Message)")
  }
}

foreach ($name in $required) {
  if (-not $seen.ContainsKey($name)) {
    $errors.Add("Required template missing from manifest: $name")
  }
}

if ($errors.Count -gt 0) {
  $errors | ForEach-Object { Write-Error $_ }
  throw "Native shape library validation failed with $($errors.Count) error(s)."
}

Write-Output "Native shape library validation passed: $($seen.Count) template(s) in $LibraryDir"
