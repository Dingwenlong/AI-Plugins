param(
  [Parameter(Mandatory = $true)]
  [string]$SpecPath,

  [Parameter(Mandatory = $true)]
  [string]$TemplateVsdx,

  [Parameter(Mandatory = $true)]
  [string]$OutputVsdx,

  [string]$PreviewPng = '',

  [string]$ShapeLibraryDir = '',

  [string]$RulesRoot = '',

  [switch]$NoBackup
)

$ErrorActionPreference = 'Stop'

function New-UnicodeText([int[]]$CodePoints) {
  return -join ($CodePoints | ForEach-Object { [char]$_ })
}

function Write-NativeBuildStage([string]$Stage) {
  if ($env:VSDX_DEBUG_STAGES -eq '1') {
    Write-Host ("native-visio-stage: {0}" -f $Stage)
  }
}

$script:DefaultConditionPlaceholder = New-UnicodeText @(0x5B, 0x689D, 0x4EF6, 0x5D)
$script:NativeFragmentPlaceholderTexts = @(
  (New-UnicodeText @(0x9078, 0x7528)),
  (New-UnicodeText @(0x6A19, 0x984C)),
  $script:DefaultConditionPlaceholder,
  (New-UnicodeText @(0x8FF4, 0x5708)),
  (New-UnicodeText @(0x5B, 0x53C3, 0x6578, 0x5D))
)

function Resolve-FullPath([string]$Path) {
  $executionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Resolve-ProjectRulesRoot {
  param([string]$ExplicitRulesRoot)
  if (-not [string]::IsNullOrWhiteSpace($ExplicitRulesRoot)) {
    return [System.IO.Path]::GetFullPath($ExplicitRulesRoot)
  }
  if (-not [string]::IsNullOrWhiteSpace($env:PROJECT_RULES_ROOT)) {
    return [System.IO.Path]::GetFullPath($env:PROJECT_RULES_ROOT)
  }
  $pluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
  $configPath = Join-Path $pluginRoot 'references\local-workspaces.json'
  if (-not (Test-Path -LiteralPath $configPath)) { return '' }
  $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $workspaceKey = if (-not [string]::IsNullOrWhiteSpace($env:PROJECT_WORKSPACE_KEY)) { $env:PROJECT_WORKSPACE_KEY } else { $config.defaultWorkspace }
  if ([string]::IsNullOrWhiteSpace($workspaceKey)) { return '' }
  $workspace = $config.workspaces.$workspaceKey
  if ($null -eq $workspace) { return '' }
  if (-not [string]::IsNullOrWhiteSpace($workspace.rulesRoot)) {
    return [System.IO.Path]::GetFullPath($workspace.rulesRoot)
  }
  if (-not [string]::IsNullOrWhiteSpace($workspace.agentRoot)) {
    return [System.IO.Path]::GetFullPath((Join-Path $workspace.agentRoot "project-rules\$workspaceKey"))
  }
  return ''
}

function Resolve-ProjectRulesAsset {
  param(
    [string]$AssetKey,
    [string]$ExplicitRulesRoot
  )
  $root = Resolve-ProjectRulesRoot $ExplicitRulesRoot
  if ([string]::IsNullOrWhiteSpace($root)) { return '' }
  $catalogPath = Join-Path $root 'catalog.json'
  if (-not (Test-Path -LiteralPath $catalogPath)) { return '' }
  $catalog = Get-Content -LiteralPath $catalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $relative = $catalog.assets.$AssetKey
  if ([string]::IsNullOrWhiteSpace($relative)) { return '' }
  $candidate = [System.IO.Path]::GetFullPath((Join-Path $root $relative))
  if (Test-Path -LiteralPath $candidate) { return $candidate }
  return ''
}

function Test-VsdxHasProjectTheme([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction SilentlyContinue
  $zip = $null
  try {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($Path)
    $hasTheme = $false
    $hasThemeRelationship = $false
    foreach ($entry in $zip.Entries) {
      $name = $entry.FullName -replace '\\', '/'
      if ($name -eq 'visio/theme/theme1.xml') {
        $hasTheme = $true
      }
      elseif ($name -eq 'visio/_rels/document.xml.rels') {
        $reader = $null
        try {
          $reader = New-Object System.IO.StreamReader($entry.Open())
          $text = $reader.ReadToEnd()
          if ($text -match 'officeDocument/2006/relationships/theme') {
            $hasThemeRelationship = $true
          }
        }
        finally {
          if ($null -ne $reader) { $reader.Close() }
        }
      }
    }
    return ($hasTheme -and $hasThemeRelationship)
  }
  catch {
    return $false
  }
  finally {
    if ($null -ne $zip) { $zip.Dispose() }
  }
}

function Set-CellFormula($Shape, [string]$Cell, [string]$Formula) {
  try { $Shape.CellsU($Cell).FormulaU = $Formula } catch { }
}

function Set-CellFormulaForce($Shape, [string]$Cell, [string]$Formula) {
  try { $Shape.CellsU($Cell).FormulaForceU = $Formula } catch { Set-CellFormula $Shape $Cell $Formula }
}

function Disable-PageAutoResize($Page) {
  try { Set-CellFormula $Page.PageSheet 'DrawingResizeType' '0' } catch { }
  try { Set-CellFormula $Page.PageSheet 'ResizePage' 'FALSE' } catch { }
}

function Set-ShapeText($Shape, [string]$Text, [string]$Color = 'RGB(0,0,0)', [double]$SizePt = 9, [string]$Font = 'Microsoft JhengHei', [bool]$Bold = $false) {
  $Shape.Text = $Text
  $styleValue = if ($Bold) { '1' } else { '0' }
  Set-CellFormulaForce $Shape 'Char.Size' ("{0} pt" -f $SizePt)
  Set-CellFormulaForce $Shape 'Char.Color' $Color
  Set-CellFormulaForce $Shape 'Char.Font' ("FONT(`"{0}`")" -f $Font)
  Set-CellFormulaForce $Shape 'Char.Style' $styleValue
  try {
    $charRows = $Shape.RowCount(3)
    for ($row = 0; $row -lt $charRows; $row++) {
      try { $Shape.CellsSRC(3, $row, 0).FormulaForceU = ("FONT(`"{0}`")" -f $Font) } catch { }
      try { $Shape.CellsSRC(3, $row, 1).FormulaForceU = $Color } catch { }
      try { $Shape.CellsSRC(3, $row, 2).FormulaForceU = $styleValue } catch { }
      try { $Shape.CellsSRC(3, $row, 7).FormulaForceU = ("{0} pt" -f $SizePt) } catch { }
    }
  } catch { }
  Set-CellFormula $Shape 'Para.HorzAlign' '1'
  Set-CellFormula $Shape 'VerticalAlign' '1'
}

function Set-NativeShapeText($Shape, [string]$Text) {
  try { $Shape.Text = '' } catch { }
  try { $Shape.Text = $Text } catch { }
}

function Set-NativeShapeTextColor($Shape, [string]$Color) {
  if ([string]::IsNullOrWhiteSpace($Color)) { return }
  Set-CellFormulaForce $Shape 'Char.Color' $Color
  try {
    $charRows = $Shape.RowCount(3)
    for ($row = 0; $row -lt $charRows; $row++) {
      try { $Shape.CellsSRC(3, $row, 1).FormulaForceU = $Color } catch { }
    }
  } catch { }
}

function Set-NativeShapeTextTheme($Shape) {
  Set-CellFormulaForce $Shape 'Char.Color' 'THEMEVAL()'
  Set-CellFormulaForce $Shape 'Char.Font' 'THEMEVAL()'
  Set-CellFormulaForce $Shape 'Char.Style' 'THEMEVAL()'
  try {
    $charRows = $Shape.RowCount(3)
    for ($row = 0; $row -lt $charRows; $row++) {
      try { $Shape.CellsSRC(3, $row, 0).FormulaForceU = 'THEMEVAL()' } catch { }
      try { $Shape.CellsSRC(3, $row, 1).FormulaForceU = 'THEMEVAL()' } catch { }
      try { $Shape.CellsSRC(3, $row, 2).FormulaForceU = 'THEMEVAL()' } catch { }
    }
  } catch { }
}

function Hide-TextBoxBorder($Shape) {
  Set-CellFormula $Shape 'LinePattern' '0'
  Set-CellFormula $Shape 'LineColor' 'RGB(255,255,255)'
  Set-CellFormula $Shape 'FillPattern' '0'
}

function Style-GreenLine($Shape) {
  Set-CellFormula $Shape 'LineColor' 'RGB(30,80,84)'
  Set-CellFormula $Shape 'LineWeight' '1.25 pt'
  Set-CellFormula $Shape 'LinePattern' '1'
}

function Style-GreenDashedLine($Shape) {
  Style-GreenLine $Shape
  Set-CellFormula $Shape 'LinePattern' '2'
}

function Style-BlackLine($Shape) {
  Set-CellFormula $Shape 'LineColor' 'RGB(0,0,0)'
  Set-CellFormula $Shape 'LineWeight' '1 pt'
}

function Style-RedLine($Shape) {
  Set-CellFormula $Shape 'LineColor' 'RGB(176,21,19)'
  Set-CellFormula $Shape 'LineWeight' '1 pt'
}

function Style-GreenIconLine($Shape) {
  Set-CellFormula $Shape 'LineColor' 'RGB(30,80,84)'
  Set-CellFormula $Shape 'LineWeight' '2 pt'
  Set-CellFormula $Shape 'LinePattern' '1'
}

function Style-MessageLine($Shape, [bool]$Dashed = $false) {
  Style-RedLine $Shape
  if ($Dashed) {
    Set-CellFormula $Shape 'LinePattern' '2'
  }
  else {
    Set-CellFormula $Shape 'LinePattern' '1'
  }
}

function Style-MessageLineRecursive($Shape, [bool]$Dashed = $false) {
  Style-MessageLine $Shape $Dashed
  try {
    foreach ($child in @($Shape.Shapes)) {
      Style-MessageLineRecursive $child $Dashed
    }
  } catch { }
}

function Set-MessageLineColorRecursive($Shape, [string]$Color, [Nullable[bool]]$Dashed = $null) {
  if (-not [string]::IsNullOrWhiteSpace($Color)) {
    Set-CellFormula $Shape 'LineColor' $Color
  }
  if ($null -ne $Dashed) {
    if ($Dashed.Value) {
      Set-CellFormula $Shape 'LinePattern' '2'
    }
    else {
      Set-CellFormula $Shape 'LinePattern' '1'
    }
  }
  try {
    foreach ($child in @($Shape.Shapes)) {
      Set-MessageLineColorRecursive $child $Color $Dashed
    }
  } catch { }
}

function Clear-ShapeTextRecursive($Shape) {
  try { $Shape.Text = '' } catch { }
  try {
    foreach ($child in @($Shape.Shapes)) {
      Clear-ShapeTextRecursive $child
    }
  } catch { }
}

function Clear-PlaceholderTextRecursive($Shape) {
  try {
    $text = [string]$Shape.Text
    if ($text.Trim() -in $script:NativeFragmentPlaceholderTexts) {
      $Shape.Text = ''
    }
  } catch { }
  try {
    foreach ($child in @($Shape.Shapes)) {
      Clear-PlaceholderTextRecursive $child
    }
  } catch { }
}

function Hide-DashedHorizontalLinesRecursive($Shape, [bool]$InsideProtectedNativeShape = $false) {
  $thisInsideProtectedNativeShape = $InsideProtectedNativeShape
  try {
    $masterName = [string]$Shape.Master.NameU
    if ($masterName -match '(?i)(lifeline|message|fragment|operand)') {
      $thisInsideProtectedNativeShape = $true
    }
  } catch { }
  try {
    $linePattern = $Shape.CellsU('LinePattern').ResultIU
    $width = [Math]::Abs($Shape.CellsU('Width').ResultIU)
    $height = [Math]::Abs($Shape.CellsU('Height').ResultIU)
    $text = [string]$Shape.Text
    $lineColor = ''
    try { $lineColor = [string]$Shape.CellsU('LineColor').FormulaU } catch { }
    $beginX = $null
    $endX = $null
    $beginY = $null
    $endY = $null
    try { $beginX = [double]$Shape.CellsU('BeginX').ResultIU } catch { }
    try { $endX = [double]$Shape.CellsU('EndX').ResultIU } catch { }
    try { $beginY = [double]$Shape.CellsU('BeginY').ResultIU } catch { }
    try { $endY = [double]$Shape.CellsU('EndY').ResultIU } catch { }

    $isHorizontal = $width -gt 0.25 -and $height -lt 0.08
    $isVerticalOneD = $null -ne $beginX -and $null -ne $endX -and $null -ne $beginY -and $null -ne $endY -and [Math]::Abs($beginX - $endX) -lt 0.01 -and [Math]::Abs($beginY - $endY) -gt 0.25
    $isDashed = $linePattern -ne 1 -and $linePattern -ne 0
    $isMessage = $lineColor -match '176,21,19'
    if (-not $thisInsideProtectedNativeShape -and -not $isVerticalOneD -and $isHorizontal -and $isDashed -and -not $isMessage -and [string]::IsNullOrWhiteSpace($text)) {
      Set-CellFormula $Shape 'LinePattern' '0'
    }
  } catch { }
  try {
    foreach ($child in @($Shape.Shapes)) {
      Hide-DashedHorizontalLinesRecursive $child $thisInsideProtectedNativeShape
    }
  } catch { }
}

function Send-ToBack($Shape) {
  try { $Shape.SendToBack() } catch { }
}

function Bring-ToFront($Shape) {
  try { $Shape.BringToFront() } catch { }
}

function Get-Master($Doc, [string[]]$Names) {
  foreach ($name in $Names) {
    try { return $Doc.Masters.ItemU($name) } catch { }
    try { return $Doc.Masters.Item($name) } catch { }
  }
  throw "None of the required masters exists: $($Names -join ', ')"
}

$script:NativeShapeTemplates = @{}
$script:NativeShapeTemplateStatus = 'not loaded'

function Get-ObjectPropertyValue($Object, [string]$Name, $Default = $null) {
  if ($null -eq $Object) { return $Default }
  try {
    $prop = $Object.PSObject.Properties[$Name]
    if ($null -ne $prop -and $null -ne $prop.Value) { return $prop.Value }
  } catch { }
  return $Default
}

function Get-Template([string]$Name) {
  if ($script:NativeShapeTemplates.ContainsKey($Name)) {
    return $script:NativeShapeTemplates[$Name]
  }
  return $null
}

function Get-TemplateNumber($Template, [string]$Name, [double]$Default) {
  $value = Get-ObjectPropertyValue $Template $Name $null
  if ($null -ne $value) {
    try { return [double]$value } catch { }
  }
  return $Default
}

function Get-MessageStyleValue($Msg, [string]$Name, [string]$Default = '') {
  $value = Get-ObjectPropertyValue $Msg $Name $null
  if ($null -ne $value -and -not [string]::IsNullOrWhiteSpace([string]$value)) { return [string]$value }
  $style = $script:MessageStyleSpec
  $value = Get-ObjectPropertyValue $style $Name $null
  if ($null -ne $value -and -not [string]::IsNullOrWhiteSpace([string]$value)) { return [string]$value }
  return $Default
}

function Test-ProjectRedMessagePolicy($Msg) {
  $policy = Get-MessageStyleValue $Msg 'policy' ''
  return ($policy -match '(?i)^project-red$')
}

function Get-TemplateString($Template, [string]$Name, [string]$Default) {
  $value = Get-ObjectPropertyValue $Template $Name $null
  if ($null -ne $value) { return [string]$value }
  return $Default
}

function Get-TemplateStyleNumber($Template, [string]$Name, [double]$Default) {
  $style = Get-ObjectPropertyValue $Template 'style' $null
  return Get-TemplateNumber $style $Name $Default
}

function Get-TemplateStyleString($Template, [string]$Name, [string]$Default) {
  $style = Get-ObjectPropertyValue $Template 'style' $null
  return Get-TemplateString $style $Name $Default
}

function Get-TemplateStyleBool($Template, [string]$Name, [bool]$Default) {
  $style = Get-ObjectPropertyValue $Template 'style' $null
  $value = Get-ObjectPropertyValue $style $Name $null
  if ($null -ne $value) {
    try { return [System.Convert]::ToBoolean($value) } catch { }
  }
  return $Default
}

function Load-NativeShapeTemplates([string]$LibraryDir) {
  $script:NativeShapeTemplates = @{}
  if ([string]::IsNullOrWhiteSpace($LibraryDir)) {
    $script:NativeShapeTemplateStatus = 'disabled'
    return
  }

  $manifestPath = Join-Path $LibraryDir 'manifest.json'
  if (-not (Test-Path -LiteralPath $manifestPath)) {
    $script:NativeShapeTemplateStatus = "manifest not found: $manifestPath"
    return
  }

  try {
    $manifest = Get-Content -Raw -Encoding UTF8 -LiteralPath $manifestPath | ConvertFrom-Json
    foreach ($entry in @($manifest.templates)) {
      $name = [string]$entry.name
      $file = [string]$entry.file
      if ([string]::IsNullOrWhiteSpace($name) -or [string]::IsNullOrWhiteSpace($file)) { continue }
      $templatePath = Join-Path $LibraryDir $file
      if (-not (Test-Path -LiteralPath $templatePath)) { continue }
      $template = Get-Content -Raw -Encoding UTF8 -LiteralPath $templatePath | ConvertFrom-Json
      $script:NativeShapeTemplates[$name] = $template
    }
    $script:NativeShapeTemplateStatus = "loaded $($script:NativeShapeTemplates.Count) templates from $LibraryDir"
  }
  catch {
    $script:NativeShapeTemplates = @{}
    $script:NativeShapeTemplateStatus = "failed to load native shape templates: $($_.Exception.Message)"
  }
}

function Add-PrimitiveTemplate($Page, [string]$Name, [double]$X, [double]$Top, [double]$ScaleX = 1.0, [double]$ScaleY = 1.0) {
  $template = Get-Template $Name
  if ($null -eq $template -or [string](Get-ObjectPropertyValue $template 'type' '') -ne 'primitive-group') {
    return $false
  }

  $width = (Get-TemplateNumber $template 'defaultWidth' 0.0) * $ScaleX
  $origin = Get-TemplateString $template 'origin' 'top-left'
  $left = if ($origin -eq 'center-top') { $X - ($width / 2.0) } else { $X }
  $lineColor = Get-TemplateStyleString $template 'lineColor' 'RGB(30,80,84)'
  $lineWeight = Get-TemplateStyleString $template 'lineWeight' '1.25 pt'
  $linePattern = [string](Get-TemplateStyleNumber $template 'linePattern' 1)
  $fillPattern = [string](Get-TemplateStyleNumber $template 'fillPattern' 0)
  $created = $false

  foreach ($primitive in @($template.primitives)) {
    $kind = [string]$primitive.kind
    $shape = $null
    if ($kind -eq 'line') {
      $x1 = $left + ([double]$primitive.x1 * $ScaleX)
      $x2 = $left + ([double]$primitive.x2 * $ScaleX)
      $y1 = Convert-Y ($Top + ([double]$primitive.y1 * $ScaleY))
      $y2 = Convert-Y ($Top + ([double]$primitive.y2 * $ScaleY))
      $shape = $Page.DrawLine($x1, $y1, $x2, $y2)
    }
    elseif ($kind -eq 'oval') {
      $pLeft = $left + ([double]$primitive.left * $ScaleX)
      $pTop = $Top + ([double]$primitive.top * $ScaleY)
      $pWidth = [double]$primitive.width * $ScaleX
      $pHeight = [double]$primitive.height * $ScaleY
      $shape = $Page.DrawOval($pLeft, (Convert-Y ($pTop + $pHeight)), ($pLeft + $pWidth), (Convert-Y $pTop))
    }
    elseif ($kind -eq 'rectangle') {
      $pLeft = $left + ([double]$primitive.left * $ScaleX)
      $pTop = $Top + ([double]$primitive.top * $ScaleY)
      $pWidth = [double]$primitive.width * $ScaleX
      $pHeight = [double]$primitive.height * $ScaleY
      $shape = $Page.DrawRectangle($pLeft, (Convert-Y ($pTop + $pHeight)), ($pLeft + $pWidth), (Convert-Y $pTop))
    }

    if ($null -ne $shape) {
      Set-CellFormula $shape 'LineColor' $lineColor
      Set-CellFormula $shape 'LineWeight' $lineWeight
      Set-CellFormula $shape 'LinePattern' $linePattern
      Set-CellFormula $shape 'FillPattern' $fillPattern
      Bring-ToFront $shape
      $created = $true
    }
  }
  return $created
}

function Add-Text($Page, [double]$Left, [double]$Top, [double]$Width, [double]$Height, [string]$Text, [string]$Color, [double]$SizePt, [string]$Align = 'center', [string]$Font = 'Microsoft JhengHei', [bool]$Bold = $false) {
  $y1 = Convert-Y ($Top + $Height)
  $y2 = Convert-Y $Top
  $shape = $Page.DrawRectangle($Left, $y1, ($Left + $Width), $y2)
  Hide-TextBoxBorder $shape
  Set-ShapeText $shape $Text $Color $SizePt $Font $Bold
  switch ($Align) {
    'left' { Set-CellFormula $shape 'Para.HorzAlign' '0' }
    'right' { Set-CellFormula $shape 'Para.HorzAlign' '2' }
    default { Set-CellFormula $shape 'Para.HorzAlign' '1' }
  }
  Bring-ToFront $shape
  return $shape
}

function Format-CommonSvgReferenceText([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return $Text }
  $pointerPrefix = '循序圖請參考：'
  $formatted = [regex]::Replace($Text, '/?(\d+_(?:CommonFunc|CommonUtil)\.[A-Za-z0-9_]+)\.svg\b', {
    param($Match)
    return [string]$Match.Groups[1].Value
  }, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
  $displayMatch = [regex]::Match($formatted, '\d+_(?:CommonFunc|CommonUtil)\.[A-Za-z0-9_]+.*$')
  if ($displayMatch.Success) {
    $displayText = $displayMatch.Value.Trim()
    $displayText = [regex]::Replace($displayText, '^\s*循序圖請參考[:：]\s*', '')
    return ($pointerPrefix + $displayText)
  }
  return $formatted
}

function Test-CommonSvgPointerText([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match 'SVG' -or $Text -match '\d+_(?:CommonFunc|CommonUtil)\.')
}

function Test-CommonMethodMessageText([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match '(?m)^\s*(CommonFunc|CommonUtil)[/.][A-Za-z0-9_]+')
}

function Normalize-CommonMethodNotation([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return $Text }
  $normalized = [regex]::Replace($Text, '(?m)(^\s*)CommonFunc/([A-Za-z0-9_]+)', '${1}CommonFunc.${2}')
  $normalized = [regex]::Replace($normalized, '(?m)(^\s*)CommonUtil\.([A-Za-z0-9_]+)', '${1}CommonUtil/${2}')
  return $normalized
}

function Add-PageTitle($Page, $PageSpec, $TemplateShape = $null) {
  $titleSpec = Get-ObjectPropertyValue $PageSpec 'title' $null
  if ($null -eq $titleSpec) { return $null }

  $template = Get-Template 'page-title'
  $text = if ($titleSpec -is [string]) { [string]$titleSpec } else { [string](Get-ObjectPropertyValue $titleSpec 'text' '') }
  if ([string]::IsNullOrWhiteSpace($text)) { return $null }

  $left = if ($null -ne $template) { Get-TemplateNumber $template 'left' 0.25 } else { 0.25 }
  $top = if ($null -ne $template) { Get-TemplateNumber $template 'top' 0.78 } else { 0.78 }
  $width = if ($null -ne $template) { Get-TemplateNumber $template 'width' ([double]$PageSpec.width - 0.5) } else { [double]$PageSpec.width - 0.5 }
  $height = if ($null -ne $template) { Get-TemplateNumber $template 'height' 0.43 } else { 0.43 }
  $color = if ($null -ne $template) { Get-TemplateStyleString $template 'textColor' 'RGB(30,81,85)' } else { 'RGB(30,81,85)' }
  $font = if ($null -ne $template) { Get-TemplateStyleString $template 'font' 'Times New Roman' } else { 'Times New Roman' }
  $size = if ($null -ne $template) { Get-TemplateStyleNumber $template 'fontSize' 16 } else { 16 }
  $bold = if ($null -ne $template) { Get-TemplateStyleBool $template 'bold' $false } else { $false }
  $align = if ($null -ne $template) { Get-TemplateStyleString $template 'align' 'center' } else { 'center' }

  if (-not ($titleSpec -is [string])) {
    $left = [double](Get-ObjectPropertyValue $titleSpec 'left' $left)
    $top = [double](Get-ObjectPropertyValue $titleSpec 'top' $top)
    $width = [double](Get-ObjectPropertyValue $titleSpec 'width' $width)
    $height = [double](Get-ObjectPropertyValue $titleSpec 'height' $height)
    $color = [string](Get-ObjectPropertyValue $titleSpec 'color' $color)
    $font = [string](Get-ObjectPropertyValue $titleSpec 'font' $font)
    $size = [double](Get-ObjectPropertyValue $titleSpec 'size' $size)
    $align = [string](Get-ObjectPropertyValue $titleSpec 'align' $align)
    try { $bold = [System.Convert]::ToBoolean((Get-ObjectPropertyValue $titleSpec 'bold' $bold)) } catch { }
  }

  if ($null -ne $TemplateShape) {
    Resize-NativeShapeByTopLeft $TemplateShape $left $top $width $height
    try { $TemplateShape.NameU = 'page-title' } catch { }
    try {
      if (([string]$TemplateShape.Text).Trim() -ne $text) {
        Set-NativeShapeText $TemplateShape $text
      }
    } catch { }
    Bring-ToFront $TemplateShape
    return $TemplateShape
  }

  $shape = Add-Text $Page $left $top $width $height $text $color $size $align $font $bold
  try { $shape.NameU = 'page-title' } catch { }
  return $shape
}

function Add-TextWithBox($Page, [double]$Left, [double]$Top, [double]$Width, [double]$Height, [string]$Text, [string]$Color, [double]$SizePt, [string]$Align = 'center', [string]$Fill = 'RGB(255,255,255)', [string]$Border = 'RGB(30,80,84)', [string]$Font = 'Microsoft JhengHei') {
  $shape = $Page.DrawRectangle($Left, (Convert-Y ($Top + $Height)), ($Left + $Width), (Convert-Y $Top))
  Set-CellFormula $shape 'FillPattern' '1'
  Set-CellFormula $shape 'FillForegnd' $Fill
  if ([string]::IsNullOrWhiteSpace($Border) -or $Border -eq 'none') {
    Set-CellFormula $shape 'LinePattern' '0'
  }
  else {
    Set-CellFormula $shape 'LinePattern' '1'
    Set-CellFormula $shape 'LineColor' $Border
    Set-CellFormula $shape 'LineWeight' '1 pt'
  }
  Set-ShapeText $shape $Text $Color $SizePt $Font
  switch ($Align) {
    'left' { Set-CellFormula $shape 'Para.HorzAlign' '0' }
    'right' { Set-CellFormula $shape 'Para.HorzAlign' '2' }
    default { Set-CellFormula $shape 'Para.HorzAlign' '1' }
  }
  Bring-ToFront $shape
  return $shape
}

function Add-WhiteMask($Page, [double]$Left, [double]$Top, [double]$Width, [double]$Height) {
  $mask = $Page.DrawRectangle($Left, (Convert-Y ($Top + $Height)), ($Left + $Width), (Convert-Y $Top))
  Set-CellFormula $mask 'FillPattern' '1'
  Set-CellFormula $mask 'FillForegnd' 'RGB(255,255,255)'
  Set-CellFormula $mask 'LinePattern' '0'
  Set-CellFormula $mask 'LineColor' 'RGB(255,255,255)'
  Bring-ToFront $mask
  return $mask
}

function Add-LabelText($Page, [double]$Left, [double]$Top, [double]$Width, [double]$Height, [string]$Text, [string]$Color, [double]$SizePt, [string]$Align = 'center') {
  Add-WhiteMask $Page $Left $Top $Width $Height | Out-Null
  return Add-Text $Page $Left $Top $Width $Height $Text $Color $SizePt $Align
}

function Add-ClippedHeaderTab($Page, [double]$Left, [double]$Top, [double]$Width, [double]$Height) {
  $template = Get-Template 'clipped-header-tab'
  if ($null -ne $template) {
    $Height = Get-TemplateNumber $template 'defaultHeight' $Height
  }
  $yTop = Convert-Y $Top
  $yBottom = Convert-Y ($Top + $Height)
  $cutMin = if ($null -ne $template) { Get-TemplateNumber $template 'cutMin' 0.10 } else { 0.10 }
  $cutMax = if ($null -ne $template) { Get-TemplateNumber $template 'cutMax' 0.18 } else { 0.18 }
  $cutRatio = if ($null -ne $template) { Get-TemplateNumber $template 'cutWidthRatio' 0.08 } else { 0.08 }
  $fillColor = if ($null -ne $template) { Get-TemplateStyleString $template 'fillColor' 'RGB(255,255,255)' } else { 'RGB(255,255,255)' }
  $lineColor = if ($null -ne $template) { Get-TemplateStyleString $template 'lineColor' 'RGB(30,80,84)' } else { 'RGB(30,80,84)' }
  $lineWeight = if ($null -ne $template) { Get-TemplateStyleString $template 'lineWeight' '1.25 pt' } else { '1.25 pt' }
  $cut = [Math]::Min($cutMax, [Math]::Max($cutMin, $Width * $cutRatio))
  $right = $Left + $Width
  $fill = $Page.DrawRectangle($Left, $yBottom, $right, $yTop)
  Set-CellFormula $fill 'FillPattern' '1'
  Set-CellFormula $fill 'FillForegnd' $fillColor
  Set-CellFormula $fill 'LinePattern' '0'
  Bring-ToFront $fill

  $lines = @(
    $Page.DrawLine($Left, $yTop, $right, $yTop),
    $Page.DrawLine($right, $yTop, $right, ($yBottom + $cut)),
    $Page.DrawLine($right, ($yBottom + $cut), ($right - $cut), $yBottom),
    $Page.DrawLine(($right - $cut), $yBottom, $Left, $yBottom),
    $Page.DrawLine($Left, $yBottom, $Left, $yTop)
  )
  foreach ($line in $lines) {
    Set-CellFormula $line 'LineColor' $lineColor
    Set-CellFormula $line 'LineWeight' $lineWeight
    Set-CellFormula $line 'LinePattern' '1'
    Bring-ToFront $line
  }
  return $fill
}

function Add-UserIcon($Page, [double]$X, [double]$Top, [string]$TemplateName = 'actor-head') {
  $actorTemplate = Get-Template $TemplateName
  $scaleX = if ($null -ne $actorTemplate) { Get-TemplateNumber $actorTemplate 'scaleX' 1.0 } else { 1.0 }
  $scaleY = if ($null -ne $actorTemplate) { Get-TemplateNumber $actorTemplate 'scaleY' 1.0 } else { 1.0 }
  if (Add-PrimitiveTemplate $Page $TemplateName $X $Top $scaleX $scaleY) {
    return
  }

  $head = $Page.DrawOval(($X - 0.055), (Convert-Y ($Top + 0.11)), ($X + 0.055), (Convert-Y $Top))
  Set-CellFormula $head 'FillPattern' '0'
  Style-GreenIconLine $head

  $parts = @(
    $Page.DrawLine(($X - 0.08), (Convert-Y ($Top + 0.16)), ($X + 0.08), (Convert-Y ($Top + 0.16))),
    $Page.DrawLine(($X - 0.08), (Convert-Y ($Top + 0.16)), ($X - 0.08), (Convert-Y ($Top + 0.47))),
    $Page.DrawLine(($X + 0.08), (Convert-Y ($Top + 0.16)), ($X + 0.08), (Convert-Y ($Top + 0.47))),
    $Page.DrawLine(($X - 0.08), (Convert-Y ($Top + 0.47)), ($X - 0.035), (Convert-Y ($Top + 0.47))),
    $Page.DrawLine(($X + 0.035), (Convert-Y ($Top + 0.47)), ($X + 0.08), (Convert-Y ($Top + 0.47))),
    $Page.DrawLine(($X - 0.035), (Convert-Y ($Top + 0.47)), ($X - 0.035), (Convert-Y ($Top + 0.62))),
    $Page.DrawLine(($X + 0.035), (Convert-Y ($Top + 0.47)), ($X + 0.035), (Convert-Y ($Top + 0.62))),
    $Page.DrawLine(($X - 0.035), (Convert-Y ($Top + 0.62)), ($X - 0.105), (Convert-Y ($Top + 0.62))),
    $Page.DrawLine(($X + 0.035), (Convert-Y ($Top + 0.62)), ($X + 0.105), (Convert-Y ($Top + 0.62))),
    $Page.DrawLine(($X - 0.14), (Convert-Y ($Top + 0.20)), ($X - 0.14), (Convert-Y ($Top + 0.42))),
    $Page.DrawLine(($X + 0.14), (Convert-Y ($Top + 0.20)), ($X + 0.14), (Convert-Y ($Top + 0.42))),
    $Page.DrawLine(($X - 0.14), (Convert-Y ($Top + 0.20)), ($X - 0.08), (Convert-Y ($Top + 0.20))),
    $Page.DrawLine(($X + 0.08), (Convert-Y ($Top + 0.20)), ($X + 0.14), (Convert-Y ($Top + 0.20)))
  )
  foreach ($part in $parts) {
    Style-GreenIconLine $part
    Bring-ToFront $part
  }
  Bring-ToFront $head
}

function Find-TemplateUserParticipantShape($Page) {
  $userTemplate = Get-Template 'user-participant-head'
  $match = Get-ObjectPropertyValue $userTemplate 'match' $null
  $matchText = Get-TemplateString $match 'text' 'User'
  $masterRegex = Get-TemplateString $match 'masterNameRegex' 'Actor lifeline'
  foreach ($shape in @($Page.Shapes)) {
    $text = ''
    $master = ''
    try { $text = ([string]$shape.Text).Trim() } catch { }
    try { $master = [string]$shape.Master.NameU } catch { }
    if ($text -eq $matchText -and $master -match $masterRegex) {
      return $shape
    }
  }
  return $null
}

function Find-TemplateParticipantShape($Page, $Participant) {
  $label = [string]$Participant.label
  $kind = [string]$Participant.kind
  $template = if ($kind -eq 'actor') { Get-Template 'user-participant-head' } else { Get-Template 'object-participant-lifeline' }
  $stylePolicy = Get-TemplateString $template 'stylePolicy' ''
  $visual = Get-ObjectPropertyValue $template 'visual' $null
  $preferPageShape = $false
  $preferPageShapeValue = Get-ObjectPropertyValue $visual 'preferPageShape' $null
  if ($null -ne $preferPageShapeValue) {
    try { $preferPageShape = [System.Convert]::ToBoolean($preferPageShapeValue) } catch { }
  }
  if ($stylePolicy -eq 'preserve-native' -and -not $preferPageShape) {
    return $null
  }
  $match = Get-ObjectPropertyValue $template 'match' $null
  $matchText = Get-TemplateString $match 'text' $label
  $defaultMasterRegex = if ($kind -eq 'actor') { 'Actor lifeline' } else { 'Object lifeline' }
  $masterRegex = Get-TemplateString $match 'masterNameRegex' $defaultMasterRegex

  foreach ($shape in @($Page.Shapes)) {
    $text = ''
    $master = ''
    try { $text = ([string]$shape.Text).Trim() } catch { }
    try { $master = [string]$shape.Master.NameU } catch { }
    if ($text -eq $matchText -and $master -match $masterRegex) {
      return $shape
    }
  }
  return $null
}

function Find-TemplatePageTitleShape($Page, $PageSpec) {
  $titleSpec = Get-ObjectPropertyValue $PageSpec 'title' $null
  if ($null -eq $titleSpec) { return $null }
  $titleText = if ($titleSpec -is [string]) { [string]$titleSpec } else { [string](Get-ObjectPropertyValue $titleSpec 'text' '') }
  if ([string]::IsNullOrWhiteSpace($titleText)) { return $null }

  foreach ($shape in @($Page.Shapes)) {
    $text = ''
    try { $text = ([string]$shape.Text).Trim() } catch { }
    if ($text -eq $titleText) {
      return $shape
    }
  }
  return $null
}

function Get-TemplateParticipantShape($Participant) {
  $id = [string]$Participant.id
  if ($script:TemplateParticipantShapes.ContainsKey($id)) {
    return $script:TemplateParticipantShapes[$id]
  }
  return $null
}

function Drop-ParticipantLifelineShape($Page, $Doc, $Participant) {
  $kind = [string]$Participant.kind
  $template = if ($kind -eq 'actor') { Get-Template 'user-participant-head' } else { Get-Template 'object-participant-lifeline' }
  $visual = Get-ObjectPropertyValue $template 'visual' $null
  $masterNamesValue = Get-ObjectPropertyValue $visual 'masterNames' $null
  $masterNames = @()
  foreach ($name in @($masterNamesValue)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$name)) { $masterNames += [string]$name }
  }
  if ($masterNames.Count -eq 0) {
    $masterNames = if ($kind -eq 'actor') { @('Actor lifeline') } else { @('Object lifeline', 'Object lifeline.47') }
  }
  $master = Get-Master $Doc $masterNames
  return $Page.Drop($master, 0, 0)
}

function Use-UmlLifelineParticipantShape($Page, $Doc, $Participant, [double]$X, [double]$Top, [double]$Width, [string]$Label, [string]$TextColor, [double]$FontSize, [string]$Font, [bool]$Bold, [double]$ParticipantBottom) {
  $kind = [string]$Participant.kind
  $template = if ($kind -eq 'actor') { Get-Template 'user-participant-head' } else { Get-Template 'object-participant-lifeline' }
  $shape = Get-TemplateParticipantShape $Participant
  if ($null -eq $shape) {
    $shape = Drop-ParticipantLifelineShape $Page $Doc $Participant
  }
  if ($null -eq $shape) {
    return $null
  }

  $visual = Get-ObjectPropertyValue $template 'visual' $null
  $lifelineChild = Get-ObjectPropertyValue $template 'lifelineChild' $null
  $defaultBoxHeight = Get-TemplateNumber $visual 'defaultTemplateBoxHeight' 0.36
  $longLineWidthGreaterThan = Get-TemplateNumber $lifelineChild 'longLineWidthGreaterThan' 2.0
  $hideDetachedChildPinYBelow = Get-TemplateNumber $lifelineChild 'hideDetachedChildPinYBelow' -1.0
  $boxHeight = 0.0
  try { $boxHeight = [double]$shape.CellsU('Height').ResultIU } catch { }
  if ($boxHeight -le 0) { $boxHeight = $defaultBoxHeight }
  $lineTop = $Top + $boxHeight
  $lifelineLength = [Math]::Max(0.1, $ParticipantBottom - $lineTop)

  try { $shape.CellsU('Width').FormulaU = ("{0} in" -f $Width) } catch { }
  try { $shape.CellsU('PinX').FormulaU = ("{0} in" -f $X) } catch { }
  try { $shape.CellsU('PinY').FormulaU = ("{0} in" -f (Convert-Y ($Top + ($boxHeight / 2.0)))) } catch { }
  Set-NativeShapeText $shape $Label

  try {
    foreach ($child in @($shape.Shapes)) {
      $childBeginX = ''
      $childEndY = ''
      try { $childBeginX = [string]$child.CellsU('BeginX').FormulaU } catch { }
      try { $childEndY = [string]$child.CellsU('EndY').FormulaU } catch { }
      if (-not [string]::IsNullOrWhiteSpace($childBeginX) -and -not [string]::IsNullOrWhiteSpace($childEndY)) {
        continue
      }
      $childWidth = 0.0
      $childHeight = 0.0
      $childPinY = 0.0
      try { $childWidth = [Math]::Abs([double]$child.CellsU('Width').ResultIU) } catch { }
      try { $childHeight = [Math]::Abs([double]$child.CellsU('Height').ResultIU) } catch { }
      try { $childPinY = [double]$child.CellsU('PinY').ResultIU } catch { }

      if ($childWidth -gt $longLineWidthGreaterThan -and $childHeight -lt 0.05) {
        Set-CellFormulaForce $child 'LinePattern' '0'
        Set-CellFormulaForce $child 'LineColor' 'RGB(255,255,255)'
        Set-CellFormulaForce $child 'FillPattern' '0'
      }
      elseif ($childPinY -lt $hideDetachedChildPinYBelow) {
        Set-CellFormulaForce $child 'LinePattern' '0'
        Set-CellFormulaForce $child 'LineColor' 'RGB(255,255,255)'
        Set-CellFormulaForce $child 'FillPattern' '0'
      }
    }
  } catch { }

  Bring-ToFront $shape
  return $shape
}

function Add-DashedVerticalLine($Page, [double]$X, [double]$Top, [double]$Bottom) {
  $dash = 0.17
  $gap = 0.12
  $cursor = $Top
  while ($cursor -lt $Bottom) {
    $segmentBottom = [Math]::Min($cursor + $dash, $Bottom)
    $segment = $Page.DrawLine($X, (Convert-Y $cursor), $X, (Convert-Y $segmentBottom))
    Style-GreenLine $segment
    Send-ToBack $segment
    $cursor = $segmentBottom + $gap
  }
}

function Add-LifelineConnectionPointRows($Shape, [double]$Height, [double]$Step = 0.25) {
  if ($Height -le 0) { return }
  $cursor = 0.0
  while ($cursor -le $Height + 0.001) {
    try {
      $row = $Shape.AddRow(7, -2, 153)
      $Shape.CellsSRC(7, $row, 0).FormulaU = 'Width*0.5'
      $Shape.CellsSRC(7, $row, 1).FormulaU = ("Height-{0} in" -f $cursor)
    } catch { }
    $cursor += $Step
  }
}

function Add-UmlLifelineConnectionPointRows($Shape, [double]$Height, [double]$Step = 0.25) {
  if ($Height -le 0) { return }
  $cursor = 0.0
  while ($cursor -le $Height + 0.001) {
    try {
      $row = $Shape.AddRow(7, -2, 153)
      $Shape.CellsSRC(7, $row, 0).FormulaU = 'Width*0.5'
      $Shape.CellsSRC(7, $row, 1).FormulaU = ("-{0} in" -f $cursor)
    } catch { }
    $cursor += $Step
  }
}

function Normalize-UmlLifelineConnectionPointRows($Shape, [double]$Height, [double]$Step) {
  if ($Height -le 0 -or $Step -le 0.03) { return 0 }
  Clear-ConnectionPointRows $Shape
  Add-UmlLifelineConnectionPointRows $Shape $Height $Step
  try { return [int]$Shape.RowCount(7) } catch { return 0 }
}

function Clear-ConnectionPointRows($Shape) {
  try {
    while ($Shape.RowCount(7) -gt 0) {
      try { $Shape.DeleteRow(7, 0) } catch { break }
    }
  } catch { }
}

function Set-UmlLifelineExtent($Shape, [double]$Height) {
  if ($Height -le 0) { return }
  try { $Shape.CellsSRC(9, 0, 1).FormulaU = ("-{0} in" -f $Height) } catch { }
  try {
    foreach ($child in @($Shape.Shapes)) {
      $beginX = ''
      $endY = ''
      try { $beginX = [string]$child.CellsU('BeginX').FormulaU } catch { }
      try { $endY = [string]$child.CellsU('EndY').FormulaU } catch { }
      if (-not [string]::IsNullOrWhiteSpace($beginX) -and -not [string]::IsNullOrWhiteSpace($endY)) {
        Set-CellFormulaForce $child 'LinePattern' '2'
        Set-CellFormulaForce $child 'LineColor' 'RGB(30,80,84)'
        Set-CellFormulaForce $child 'LineWeight' '1 pt'
      }
    }
  } catch { }
}

function Set-AdjustableMessageTextPosition($Shape, [string]$InitialXFormula, [string]$InitialYFormula) {
  $controlName = 'TextPosition'
  $controlX = "Controls.$controlName.X"
  $controlY = "Controls.$controlName.Y"
  try {
    if ($Shape.CellExistsU($controlX, 0) -eq 0 -or $Shape.CellExistsU($controlY, 0) -eq 0) {
      try { $Shape.AddNamedRow(9, $controlName, 0) | Out-Null }
      catch { $Shape.AddRow(9, -2, 0) | Out-Null }
    }
  } catch { }

  try {
    if ($Shape.CellExistsU($controlX, 0) -ne 0 -and $Shape.CellExistsU($controlY, 0) -ne 0) {
      Set-CellFormulaForce $Shape $controlX $InitialXFormula
      Set-CellFormulaForce $Shape $controlY $InitialYFormula
      Set-CellFormulaForce $Shape 'TxtPinX' ("SETATREF({0})" -f $controlX)
      Set-CellFormulaForce $Shape 'TxtPinY' ("SETATREF({0})" -f $controlY)
      return
    }
  } catch { }

  Set-CellFormulaForce $Shape 'TxtPinX' $InitialXFormula
  Set-CellFormulaForce $Shape 'TxtPinY' $InitialYFormula
}

function Add-NativeParticipantLifeline($Page, [double]$X, [double]$Top, [double]$Bottom) {
  $line = $Page.DrawLine($X, (Convert-Y $Top), $X, (Convert-Y $Bottom))
  Set-CellFormula $line 'LineColor' 'RGB(30,80,84)'
  Set-CellFormula $line 'LineWeight' '1 pt'
  Set-CellFormula $line 'LinePattern' '2'
  Set-CellFormula $line 'BeginArrow' '0'
  Set-CellFormula $line 'EndArrow' '0'
  Add-LifelineConnectionPointRows $line ([Math]::Max(0.1, $Bottom - $Top))
  Send-ToBack $line
  return $line
}

function Add-NativeParticipant($Page, $Doc, $Participant) {
  $id = [string]$Participant.id
  $label = [string]$Participant.label
  $kind = [string]$Participant.kind
  $x = [double]$Participant.x
  $top = [double]$Participant.top
  $height = [double]$Participant.height
  $userTemplate = Get-Template 'user-participant-head'
  $userVisual = Get-ObjectPropertyValue $userTemplate 'visual' $null
  $participantGlue = $null
  if ($kind -eq 'actor') {
    $participantGlue = Get-ObjectPropertyValue $userTemplate 'generatedGlue' $null
  }
  else {
    $objectTemplateForGlue = Get-Template 'object-participant-lifeline'
    $participantGlue = Get-ObjectPropertyValue $objectTemplateForGlue 'generatedGlue' $null
  }
  $useGeneratedDashedLifeline = $false
  $useGeneratedDashedLifelineValue = Get-ObjectPropertyValue $participantGlue 'useGeneratedDashedLifeline' $null
  if ($null -ne $useGeneratedDashedLifelineValue) {
    try { $useGeneratedDashedLifeline = [System.Convert]::ToBoolean($useGeneratedDashedLifelineValue) } catch { }
  }
  $labelBoxTemplateName = if ($kind -eq 'actor') { Get-TemplateString $userVisual 'labelBoxTemplate' 'participant-head-box' } else { 'participant-head-box' }
  $participantTemplate = Get-Template $labelBoxTemplateName
  $width = if ($Participant.width) { [double]$Participant.width } else { 0.72 }
  $boxHeight = if ($null -ne $participantTemplate) { Get-TemplateNumber $participantTemplate 'defaultHeight' 0.42 } else { 0.42 }
  $boxTop = $top
  $fillPattern = if ($null -ne $participantTemplate) { [string](Get-TemplateStyleNumber $participantTemplate 'fillPattern' 1) } else { '1' }
  $fillColor = if ($null -ne $participantTemplate) { Get-TemplateStyleString $participantTemplate 'fillColor' 'RGB(255,255,255)' } else { 'RGB(255,255,255)' }
  $lineColor = if ($null -ne $participantTemplate) { Get-TemplateStyleString $participantTemplate 'lineColor' 'RGB(30,80,84)' } else { 'RGB(30,80,84)' }
  $lineWeight = if ($null -ne $participantTemplate) { Get-TemplateStyleString $participantTemplate 'lineWeight' '1.25 pt' } else { '1.25 pt' }
  $linePattern = if ($null -ne $participantTemplate) { [string](Get-TemplateStyleNumber $participantTemplate 'linePattern' 1) } else { '1' }
  $textColor = if ($null -ne $participantTemplate) { Get-TemplateStyleString $participantTemplate 'textColor' 'RGB(0,0,0)' } else { 'RGB(0,0,0)' }
  $font = if ($null -ne $participantTemplate) { Get-TemplateStyleString $participantTemplate 'font' 'Times New Roman' } else { 'Times New Roman' }
  $fontSize = if ($null -ne $participantTemplate) { Get-TemplateStyleNumber $participantTemplate 'fontSize' 9 } else { 9 }
  $fontBold = if ($null -ne $participantTemplate) { Get-TemplateStyleBool $participantTemplate 'fontBold' $false } else { $false }
  $box = Use-UmlLifelineParticipantShape $Page $Doc $Participant $x $boxTop $width $label $textColor $fontSize $font $fontBold ($top + $height)
  $usesUmlLifeline = $false
  if ($null -ne $box) {
    try { $boxHeight = [double]$box.CellsU('Height').ResultIU } catch { }
    try {
      $masterName = [string]$box.Master.NameU
      if ($masterName -match 'lifeline') { $usesUmlLifeline = $true }
    } catch { }
  }

  if ($null -eq $box) {
    $requiredMaster = if ($kind -eq 'actor') { 'Actor lifeline' } else { 'Object lifeline' }
    throw "Unable to create native UML lifeline participant '$label'. Required master/template missing: $requiredMaster"
  }

  if (-not $usesUmlLifeline) {
    $requiredMaster = if ($kind -eq 'actor') { 'Actor lifeline' } else { 'Object lifeline' }
    throw "Native participant '$label' was created without a UML lifeline master. Required formal master/template: $requiredMaster"
  }
  $lineTop = $boxTop + $boxHeight
  $lineBottom = $top + $height
  $lifelineHeight = [Math]::Max(0.1, $lineBottom - $lineTop)
  $lifeline = $box
  if ($useGeneratedDashedLifeline) {
    $lifeline = Add-NativeParticipantLifeline $Page $x $lineTop $lineBottom
  }
  else {
    Set-UmlLifelineExtent $box $lifelineHeight
  }

  return [pscustomobject]@{
    id = $id
    x = $x
    top = $lineTop
    height = ($lineBottom - $lineTop)
    shape = $box
    headShape = $box
    lifelineShape = $lifeline
    connectionMode = if ($usesUmlLifeline) { 'uml-lifeline' } else { 'manual' }
    anchors = @{}
    native = $true
  }
}

function Measure-LabelWidth([string]$Text, [double]$MinWidth, [double]$MaxWidth) {
  $width = 0.22
  foreach ($char in $Text.ToCharArray()) {
    if ([int][char]$char -gt 255) {
      $width += 0.135
    }
    else {
      $width += 0.075
    }
  }
  return [Math]::Min([Math]::Max($MinWidth, $width), $MaxWidth)
}

function Get-TemplateStringArray($Object, [string]$Name, [string[]]$Default) {
  $value = Get-ObjectPropertyValue $Object $Name $null
  $items = @()
  foreach ($item in @($value)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$item)) {
      $items += [string]$item
    }
  }
  if ($items.Count -gt 0) { return $items }
  return $Default
}

function Resize-NativeShapeByTopLeft($Shape, [double]$Left, [double]$Top, [double]$Width, [double]$Height) {
  try { $Shape.CellsU('Width').FormulaU = ("{0} in" -f $Width) } catch { }
  try { $Shape.CellsU('Height').FormulaU = ("{0} in" -f $Height) } catch { }
  try { $Shape.CellsU('PinX').FormulaU = ("{0} in" -f ($Left + ($Width / 2.0))) } catch { }
  try { $Shape.CellsU('PinY').FormulaU = ("{0} in" -f (Convert-Y ($Top + ($Height / 2.0)))) } catch { }
}

function Get-ShapeBounds($Shape) {
  try {
    $pinX = [double]$Shape.CellsU('PinX').ResultIU
    $pinY = [double]$Shape.CellsU('PinY').ResultIU
    $width = [double]$Shape.CellsU('Width').ResultIU
    $height = [double]$Shape.CellsU('Height').ResultIU
    $left = $pinX - ($width / 2.0)
    $right = $pinX + ($width / 2.0)
    $bottom = $pinY - ($height / 2.0)
    $top = $pinY + ($height / 2.0)
    return [pscustomobject]@{
      Left = $left
      Right = $right
      Bottom = $bottom
      Top = $top
      CenterX = $pinX
      CenterY = $pinY
      Area = [Math]::Max(0.0001, $width * $height)
    }
  } catch {
    return $null
  }
}

function Test-PointInsideBounds($Point, $Bounds, [double]$Inset = 0.02) {
  if ($null -eq $Point -or $null -eq $Bounds) { return $false }
  return (
    $Point.CenterX -ge ($Bounds.Left + $Inset) -and
    $Point.CenterX -le ($Bounds.Right - $Inset) -and
    $Point.CenterY -ge ($Bounds.Bottom + $Inset) -and
    $Point.CenterY -le ($Bounds.Top - $Inset)
  )
}

function Test-BoundsInsideBounds($Inner, $Outer, [double]$Inset = 0.02) {
  if ($null -eq $Inner -or $null -eq $Outer) { return $false }
  return (
    $Inner.Left -ge ($Outer.Left + $Inset) -and
    $Inner.Right -le ($Outer.Right - $Inset) -and
    $Inner.Bottom -ge ($Outer.Bottom + $Inset) -and
    $Inner.Top -le ($Outer.Top - $Inset)
  )
}

function Test-NativeOperandInsideFrameLane($OperandBounds, $FrameBounds) {
  if ($null -eq $OperandBounds -or $null -eq $FrameBounds) { return $false }
  $operandWidth = [Math]::Max(0.01, [double]$OperandBounds.Right - [double]$OperandBounds.Left)
  $frameWidth = [Math]::Max(0.01, [double]$FrameBounds.Right - [double]$FrameBounds.Left)
  $horizontalOverlap = [Math]::Min([double]$OperandBounds.Right, [double]$FrameBounds.Right) - [Math]::Max([double]$OperandBounds.Left, [double]$FrameBounds.Left)
  if ($horizontalOverlap -lt ([Math]::Min($operandWidth, $frameWidth) * 0.40)) { return $false }

  # Use the operand's top separator as the ownership anchor. A tall parent operand can
  # visually cross a nested alt frame, but its top separator must stay in the owning alt.
  if ([double]$OperandBounds.Top -gt ([double]$FrameBounds.Top + 0.10)) { return $false }
  if ([double]$OperandBounds.Top -lt ([double]$FrameBounds.Bottom - 0.10)) { return $false }
  return $true
}

$script:NativeConnectionPointUnit = (6.0 / 25.4)

function Get-NativeConnectionPointUnit {
  return [double]$script:NativeConnectionPointUnit
}

function Set-NativeConnectionPointUnit([double]$Unit) {
  if ($Unit -gt 0.03) {
    $script:NativeConnectionPointUnit = [double]$Unit
  }
}

function Get-DominantConnectionGap([double[]]$Gaps) {
  $filtered = @($Gaps | Where-Object { $_ -gt 0.03 -and $_ -lt 1.0 } | ForEach-Object { [Math]::Round([double]$_, 4) })
  if ($filtered.Count -eq 0) { return $null }
  $groups = @($filtered | Group-Object | Sort-Object Count -Descending)
  if ($groups.Count -eq 0) { return $null }
  return [double]$groups[0].Name
}

function Get-PageParticipantConnectionPointUnit($Page) {
  $objectGaps = @()
  $actorGaps = @()
  foreach ($candidate in @($Page.Shapes)) {
    $candidateMaster = Get-ShapeMasterName $candidate
    if ($candidateMaster -notmatch '^(Actor lifeline|Object lifeline)') { continue }
    $ys = @()
    try {
      for ($row = 0; $row -lt [int]$candidate.RowCount(7); $row++) {
        $ys += [double]$candidate.CellsSRC(7, $row, 1).ResultIU
      }
    } catch { }
    $orderedYs = @($ys | Sort-Object -Descending)
    for ($rowIndex = 0; $rowIndex -lt ($orderedYs.Count - 1); $rowIndex++) {
      $gap = [Math]::Abs([double]$orderedYs[$rowIndex] - [double]$orderedYs[$rowIndex + 1])
      if ($candidateMaster -match '^Object lifeline') { $objectGaps += $gap } else { $actorGaps += $gap }
    }
  }
  $objectUnit = Get-DominantConnectionGap ([double[]]$objectGaps)
  if ($null -ne $objectUnit) { return [double]$objectUnit }
  $actorUnit = Get-DominantConnectionGap ([double[]]$actorGaps)
  if ($null -ne $actorUnit) { return [double]$actorUnit }
  return 0.25
}

function Snap-ToNativeConnectionPoint([double]$Value, [string]$Mode = 'nearest') {
  $unit = Get-NativeConnectionPointUnit
  if ($unit -le 0) { return $Value }
  $scaled = $Value / $unit
  switch -Regex ($Mode) {
    'floor' { return [Math]::Floor($scaled) * $unit }
    'ceil' { return [Math]::Ceiling($scaled) * $unit }
    default { return [Math]::Round($scaled, 0, [MidpointRounding]::AwayFromZero) * $unit }
  }
}

function Normalize-PageParticipantConnectionRows($Participants) {
  $unit = Get-NativeConnectionPointUnit
  if ($unit -le 0.03) {
    throw "Native UML lifeline connection-point unit is unavailable; cannot normalize participant connection rows."
  }
  foreach ($participant in @($Participants.Values)) {
    if ($null -eq $participant -or -not $participant.native) { continue }
    if ($participant.connectionMode -ne 'uml-lifeline') {
      throw "Participant '$([string]$participant.id)' is not a native UML lifeline; cannot enforce native connection-point rows."
    }
    $rowCount = Normalize-UmlLifelineConnectionPointRows $participant.shape ([double]$participant.height) $unit
    if ($rowCount -le 0) {
      throw "Participant '$([string]$participant.id)' has no usable UML lifeline connection points after normalization."
    }
  }
}

function Get-PageParticipantCenterXs($Page) {
  $items = @()
  foreach ($shape in @($Page.Shapes)) {
    $masterName = Get-ShapeMasterName $shape
    if ($masterName -notmatch '(?i)^(Actor lifeline|Object lifeline)') { continue }
    try { $items += [double]$shape.CellsU('PinX').ResultIU } catch { }
  }
  return $items
}

function Get-FragmentHorizontalClearance($Page, [double]$Left, [double]$Width, [double]$MinClearance = 0.35) {
  $right = $Left + $Width
  foreach ($x in (Get-PageParticipantCenterXs $Page)) {
    if ($x -lt $Left -or $x -gt $right) { continue }
    if (($x - $Left) -lt $MinClearance) { $Left = $x - $MinClearance }
    if (($right - $x) -lt $MinClearance) { $right = $x + $MinClearance }
  }
  try {
    $pageWidth = [double]$Page.PageSheet.CellsU('PageWidth').ResultIU
    $Left = [Math]::Max(0.25, $Left)
    $right = [Math]::Min($pageWidth - 0.25, $right)
  } catch { }
  return [pscustomobject]@{
    Left = $Left
    Width = [Math]::Max(0.1, $right - $Left)
  }
}

function Snap-NativeFragmentFramesToGrid($Page) {
  $unit = Get-NativeConnectionPointUnit
  foreach ($shape in @($Page.Shapes)) {
    if (-not (Test-NativeFragmentFrameShape $shape)) { continue }
    $bounds = Get-ShapeBounds $shape
    if ($null -eq $bounds) { continue }
    $topDistance = Get-TopDistanceFromY ([double]$bounds.Top)
    $bottomDistance = Get-TopDistanceFromY ([double]$bounds.Bottom)
    $topSnap = Snap-ToNativeConnectionPoint $topDistance 'floor'
    $bottomSnap = Snap-ToNativeConnectionPoint $bottomDistance 'ceil'
    if ((Get-ShapeTextTrimmed $shape) -eq 'ref') {
      $topSnap = Snap-ToNativeConnectionPoint $topDistance
      $bottomSnap = $topSnap + ($unit * 6.0)
    }
    if ($bottomSnap -le ($topSnap + 0.01)) { $bottomSnap = $topSnap + $unit }
    Set-NativeShapeByTopDistances $shape ([double]$bounds.Left) ([double]$bounds.Right) $topSnap $bottomSnap
  }
}

function Test-NativeFragmentFrameShape($Shape) {
  try {
    $masterName = [string]$Shape.Master.NameU
    return ($masterName -match '(?i)(Alternative fragment|Optional fragment|Loop fragment|Other fragment)')
  } catch {
    return $false
  }
}

function Test-ExcludeFromFragmentMembership($Shape) {
  try {
    $masterName = ''
    $text = ''
    try { $masterName = [string]$Shape.Master.NameU } catch { }
    try { $text = ([string]$Shape.Text).Trim() } catch { }
    if ($masterName -match '(?i)lifeline') { return $true }
    if ([string]::IsNullOrWhiteSpace($masterName) -and [string]::IsNullOrWhiteSpace($text)) {
      $width = 0.0
      $height = 0.0
      try { $width = [double]$Shape.CellsU('Width').ResultIU } catch { }
      try { $height = [double]$Shape.CellsU('Height').ResultIU } catch { }
      if ($width -gt 6.0 -and $height -lt 0.08) { return $true }
    }
    if ($text -in @('User', 'APP', 'Enterprise', 'IRIS')) { return $true }
  } catch { }
  return $false
}

function Add-NativeFragmentMember($FrameShape, $MemberShape) {
  foreach ($mode in @(2, 0, 1)) {
    try {
      $FrameShape.ContainerProperties.AddMember($MemberShape, $mode) | Out-Null
      return $true
    } catch { }
  }
  return $false
}

function Test-NativeFragmentListMember($FrameShape, $MemberShape) {
  $memberId = $null
  try { $memberId = [int]$MemberShape.ID } catch { return $false }
  try {
    foreach ($id in @($FrameShape.ContainerProperties.GetListMembers())) {
      try {
        if ([int]$id -eq $memberId) { return $true }
      } catch { }
    }
  } catch { }
  return $false
}

function Insert-NativeFragmentListMember($FrameShape, $MemberShape, [int]$Position) {
  try { $FrameShape.ContainerProperties.LockMembership = $false } catch { }
  try { $FrameShape.ContainerProperties.ResizeAsNeeded = 0 } catch { }
  if (Test-NativeFragmentListMember $FrameShape $MemberShape) {
    try { $FrameShape.ContainerProperties.ReorderListMember($MemberShape, $Position) | Out-Null } catch { }
    return (Test-NativeFragmentListMember $FrameShape $MemberShape)
  }
  try {
    $FrameShape.ContainerProperties.InsertListMember($MemberShape, $Position) | Out-Null
    if (Test-NativeFragmentListMember $FrameShape $MemberShape) { return $true }
  } catch { }
  try {
    $FrameShape.ContainerProperties.ReorderListMember($MemberShape, $Position) | Out-Null
    if (Test-NativeFragmentListMember $FrameShape $MemberShape) { return $true }
  } catch { }
  Add-NativeFragmentMember $FrameShape $MemberShape | Out-Null
  try {
    $FrameShape.ContainerProperties.InsertListMember($MemberShape, $Position) | Out-Null
    if (Test-NativeFragmentListMember $FrameShape $MemberShape) { return $true }
  } catch { }
  try {
    $FrameShape.ContainerProperties.ReorderListMember($MemberShape, $Position) | Out-Null
    if (Test-NativeFragmentListMember $FrameShape $MemberShape) { return $true }
  } catch { }
  return $false
}

function Test-NativeOperandOwnerFrame($Shape) {
  $text = Get-ShapeTextTrimmed $Shape
  $masterName = Get-ShapeMasterName $Shape
  return (
    ($text -eq 'alt' -and $masterName -match '(?i)^Alternative fragment') -or
    ($text -eq 'opt' -and $masterName -match '(?i)^(Alternative fragment|Optional fragment)')
  )
}

function Add-NativeFragmentMemberships($Page) {
  $frames = @()
  foreach ($shape in @($Page.Shapes)) {
    if (Test-NativeFragmentFrameShape $shape) {
      $bounds = Get-ShapeBounds $shape
      if ($null -ne $bounds) {
        $frames += [pscustomobject]@{ Shape = $shape; Bounds = $bounds; Area = $bounds.Area }
      }
    }
  }
  if ($frames.Count -eq 0) { return }

  foreach ($candidate in @($Page.Shapes)) {
    if (Test-ExcludeFromFragmentMembership $candidate) { continue }
    $candidateBounds = Get-ShapeBounds $candidate
    if ($null -eq $candidateBounds) { continue }
    $candidateIsFragment = Test-NativeFragmentFrameShape $candidate
    $candidateIsOperand = (Get-ShapeMasterName $candidate) -match '(?i)^Interaction operand'
    $parent = $null
    foreach ($frame in $frames) {
      try {
        if ([int]$frame.Shape.ID -eq [int]$candidate.ID) { continue }
      } catch { }
      if ($candidateIsOperand -and -not (Test-NativeOperandOwnerFrame $frame.Shape)) { continue }
      $isInsideFrame = if ($candidateIsFragment) {
        Test-BoundsInsideBounds $candidateBounds $frame.Bounds
      }
      elseif ($candidateIsOperand) {
        Test-NativeOperandInsideFrameLane $candidateBounds $frame.Bounds
      }
      else {
        Test-PointInsideBounds $candidateBounds $frame.Bounds
      }
      if ($isInsideFrame) {
        if ($null -eq $parent -or $frame.Area -lt $parent.Area) {
          $parent = $frame
        }
      }
    }
    if ($null -ne $parent) {
      Add-NativeFragmentMember $parent.Shape $candidate | Out-Null
    }
  }
}

function Restore-NativeBusinessGroupFramesFromSpec($FrameRecords) {
  $records = @($FrameRecords)
  if ($records.Count -eq 0) { return }

  $unit = Get-NativeConnectionPointUnit
  $padding = [Math]::Max(0.08, $unit * 0.5)
  foreach ($record in $records) {
    $spec = $record.Spec
    if ([string](Get-ObjectPropertyValue $spec 'kind' '') -ne 'group') { continue }
    $groupShape = $record.Shape
    if ($null -eq $groupShape) { continue }

    $specLeft = [double](Get-ObjectPropertyValue $spec 'left' 0.0)
    $specTop = [double](Get-ObjectPropertyValue $spec 'top' 0.0)
    $specWidth = [double](Get-ObjectPropertyValue $spec 'width' 0.0)
    $specHeight = [double](Get-ObjectPropertyValue $spec 'height' 0.0)
    if ($specWidth -le 0.0 -or $specHeight -le 0.0) { continue }
    $specRight = $specLeft + $specWidth
    $specBottom = $specTop + $specHeight

    $groupBounds = Get-ShapeBounds $groupShape
    $left = if ($null -ne $groupBounds) { [double]$groupBounds.Left } else { $specLeft }
    $right = if ($null -ne $groupBounds) { [double]$groupBounds.Right } else { $specRight }
    $desiredBottom = $specBottom
    $nestedShapes = @()

    foreach ($childRecord in $records) {
      $childShape = $childRecord.Shape
      if ($null -eq $childShape) { continue }
      try {
        if ([int]$childShape.ID -eq [int]$groupShape.ID) { continue }
      } catch { }
      if (-not (Test-NativeFragmentFrameShape $childShape)) { continue }
      $childBounds = Get-ShapeBounds $childShape
      if ($null -eq $childBounds) { continue }

      $childTopDistance = Get-TopDistanceFromY ([double]$childBounds.Top)
      $childBottomDistance = Get-TopDistanceFromY ([double]$childBounds.Bottom)
      $childCenterDistance = ($childTopDistance + $childBottomDistance) / 2.0
      if ($childCenterDistance -lt ($specTop - 0.05) -or $childCenterDistance -gt ($specBottom + 0.05)) { continue }

      $childWidth = [Math]::Max(0.01, [double]$childBounds.Right - [double]$childBounds.Left)
      $overlap = [Math]::Min([double]$childBounds.Right, $specRight) - [Math]::Max([double]$childBounds.Left, $specLeft)
      if ($overlap -lt ([Math]::Min($childWidth, $specWidth) * 0.25)) { continue }

      $left = [Math]::Min($left, [double]$childBounds.Left - $padding)
      $right = [Math]::Max($right, [double]$childBounds.Right + $padding)
      $desiredBottom = [Math]::Max($desiredBottom, $childBottomDistance + $padding)
      $nestedShapes += $childShape
    }

    if ($nestedShapes.Count -eq 0) { continue }
    $desiredTop = Snap-ToNativeConnectionPoint $specTop 'floor'
    $desiredBottom = Snap-ToNativeConnectionPoint $desiredBottom 'ceil'
    if ($desiredBottom -le ($desiredTop + 0.05)) { continue }

    Set-NativeShapeByTopDistances $groupShape $left $right $desiredTop $desiredBottom
    try { $groupShape.ContainerProperties.LockMembership = $false } catch { }
    try { $groupShape.ContainerProperties.ResizeAsNeeded = 0 } catch { }
    foreach ($nestedShape in $nestedShapes) {
      Add-NativeFragmentMember $groupShape $nestedShape | Out-Null
    }
    try { $groupShape.ContainerProperties.LockMembership = $true } catch { }
    try { $groupShape.ContainerProperties.ResizeAsNeeded = 0 } catch { }
  }
}

function Get-ShapeTextTrimmed($Shape) {
  try { return ([string]$Shape.Text).Trim() } catch { return '' }
}

function Get-ShapeMasterName($Shape) {
  try { return [string]$Shape.Master.NameU } catch { return '' }
}

function Get-TopDistanceFromY([double]$Y) {
  return ([double]$script:PageHeight - $Y)
}

function Set-NativeShapeByTopDistances($Shape, [double]$Left, [double]$Right, [double]$TopDistance, [double]$BottomDistance) {
  $width = [Math]::Max(0.1, $Right - $Left)
  $height = [Math]::Max(0.05, $BottomDistance - $TopDistance)
  Resize-NativeShapeByTopLeft $Shape $Left $TopDistance $width $height
}

function Get-ShapeFormulaRef($Shape, [string]$CellName) {
  try {
    $nameId = [string]$Shape.NameID
    if (-not [string]::IsNullOrWhiteSpace($nameId)) { return "$nameId!$CellName" }
  } catch { }
  try { return ("Sheet.{0}!{1}" -f [int]$Shape.ID, $CellName) } catch { return $CellName }
}

function Format-VisioInchFormula([double]$Value) {
  return [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $Value)
}

function Freeze-NativeOperandVerticalGeometry($Shape) {
  try {
    $pinY = [double]$Shape.CellsU('PinY').ResultIU
    $height = [Math]::Abs([double]$Shape.CellsU('Height').ResultIU)
    $locPinY = [double]$Shape.CellsU('LocPinY').ResultIU
    if ($height -lt 0.01) { return }

    Set-CellFormulaForce $Shape 'PinY' (Format-VisioInchFormula $pinY)
    Set-CellFormulaForce $Shape 'Height' (Format-VisioInchFormula $height)
    Set-CellFormulaForce $Shape 'LocPinY' (Format-VisioInchFormula $locPinY)
  } catch { }
}

function Freeze-NativeFrameVerticalGeometry($Shape) {
  try {
    $pinY = [double]$Shape.CellsU('PinY').ResultIU
    $height = [Math]::Abs([double]$Shape.CellsU('Height').ResultIU)
    if ($height -lt 0.05) { return }

    Set-CellFormulaForce $Shape 'PinY' (Format-VisioInchFormula $pinY)
    Set-CellFormulaForce $Shape 'Height' (Format-VisioInchFormula $height)
    Set-CellFormulaForce $Shape 'LocPinY' 'Height*0.5'
  } catch { }
}

function Join-VisioFormulaExtrema([string]$FunctionName, $Expressions) {
  $items = @($Expressions | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
  if ($items.Count -eq 0) { return '' }
  if ($items.Count -eq 1) { return [string]$items[0] }
  return ("{0}({1})" -f $FunctionName, ($items -join ','))
}

function Restore-NativeFragmentHorizontalBinding($FrameShape, [string]$FrameLeftFormula, [string]$FrameWidthFormula, [bool]$HasFrameResizeControl) {
  if (-not $HasFrameResizeControl) { return }
  Set-CellFormula $FrameShape 'Controls.Row_1.X' $FrameWidthFormula
  Set-CellFormula $FrameShape 'Controls.Row_1.Y' 'Height*0.5'
  Set-CellFormula $FrameShape 'LocPinX' 'Width*0.5'
  Set-CellFormula $FrameShape 'LocPinY' 'Height*0.5'
  Set-CellFormula $FrameShape 'Width' 'Controls.Row_1'
  Set-CellFormula $FrameShape 'PinX' ("{0}+(Width*0.5)" -f $FrameLeftFormula)
}

function Set-NativeAltFrameOperandBinding($FrameShape, $Operands, [double]$FirstOperandTopOffset, [double]$FinalBottomDistance, $FinalFormulaBottomEdges) {
  $operandItems = @($Operands)
  if ($operandItems.Count -eq 0) { return }

  $frameBounds = Get-ShapeBounds $FrameShape
  if ($null -eq $frameBounds) { return }
  $frameLeftFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', [double]$frameBounds.Left)
  $frameInitialWidth = [Math]::Max(0.1, [double]$frameBounds.Right - [double]$frameBounds.Left)
  $frameInitialWidthFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $frameInitialWidth)
  $frameTopFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', [double]$frameBounds.Top)
  $firstOperandTopFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', ([double]$frameBounds.Top - $FirstOperandTopOffset))
  $offset = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $FirstOperandTopOffset)
  $hasFrameResizeControl = $false
  try { $hasFrameResizeControl = ($FrameShape.CellExistsU('Controls.Row_1.X', 0) -ne 0 -or $FrameShape.CellExistsU('Controls.Row_1', 0) -ne 0) } catch { }
  # Alternative fragment.52 owns the yellow right-side list-size handle. Keep that handle
  # as the horizontal source of truth so dragging either it or a direct operand width
  # updates the same native control point.
  Restore-NativeFragmentHorizontalBinding $FrameShape $frameLeftFormula $frameInitialWidthFormula $hasFrameResizeControl
  $framePinX = Get-ShapeFormulaRef $FrameShape 'PinX'
  $frameWidth = Get-ShapeFormulaRef $FrameShape 'Width'
  $frameResizeControl = Get-ShapeFormulaRef $FrameShape 'Controls.Row_1'
  $topFormula = $firstOperandTopFormula
  $bottomFormula = ''
  try { $FrameShape.ContainerProperties.LockMembership = $false } catch { }

  for ($i = 0; $i -lt $operandItems.Count; $i++) {
    $operandShape = $operandItems[$i].Shape
    $listPosition = $i + 1
    if (-not (Insert-NativeFragmentListMember $FrameShape $operandShape $listPosition)) {
      throw ("Failed to bind native alt operand as Visio list member: frame={0}, operand={1}" -f [int]$FrameShape.ID, [int]$operandShape.ID)
    }
    Set-CellFormula $operandShape 'PinX' ("IFERROR(LISTSHEETREF()!PinX,{0})" -f $framePinX)
    if ($hasFrameResizeControl) {
      Set-CellFormula $operandShape 'Width' 'IFERROR(LISTSHEETREF()!Controls.ROW_1,User.UserWidth)'
    }
    else {
      Set-CellFormula $operandShape 'Width' $frameWidth
    }

    $heightRef = Get-ShapeFormulaRef $operandShape 'Height'
    $isLast = ($i + 1 -eq $operandItems.Count)
    $baseHeight = 0.05
    $baseHeightFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $baseHeight)
    if ($isLast) {
      $bottomConstantY = [double]$script:PageHeight - $FinalBottomDistance
      $bottomConstantFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $bottomConstantY)
      $bottomFormula = $bottomConstantFormula
      Set-CellFormulaForce $operandShape 'Height' ("MAX({0},({1})-({2}))" -f $baseHeightFormula, $topFormula, $bottomFormula)
      $heightRef = Get-ShapeFormulaRef $operandShape 'Height'
      Set-CellFormulaForce $operandShape 'PinY' ("({0})-(Height*0.5)" -f $topFormula)
      $bottomFormula = ("({0})-({1})" -f $topFormula, $heightRef)
    }
    else {
      if (-not $isLast -and $null -ne $operandItems[$i + 1].PSObject.Properties['TopDistance']) {
        $nextOperandTopY = [double]$script:PageHeight - [double]$operandItems[$i + 1].TopDistance
        $nextOperandTopFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $nextOperandTopY)
        Set-CellFormulaForce $operandShape 'Height' ("MAX({0},({1})-({2}))" -f $baseHeightFormula, $topFormula, $nextOperandTopFormula)
        $heightRef = Get-ShapeFormulaRef $operandShape 'Height'
      }
      Set-CellFormulaForce $operandShape 'PinY' ("({0})-(Height*0.5)" -f $topFormula)
      $bottomFormula = ("({0})-({1})" -f $topFormula, $heightRef)
    }
    $topFormula = $bottomFormula
  }

  # Visio may shrink a list container back to the operand master's default width when
  # InsertListMember materializes the native list relationship. Restore the resolved
  # left edge and width after all operands are list members.
  Restore-NativeFragmentHorizontalBinding $FrameShape $frameLeftFormula $frameInitialWidthFormula $hasFrameResizeControl
  Set-CellFormula $FrameShape 'PinY' ("(({0})+({1}))*0.5" -f $frameTopFormula, $bottomFormula)
  Set-CellFormula $FrameShape 'Height' ("MAX(0.05 in,({0})-({1}))" -f $frameTopFormula, $bottomFormula)
  foreach ($operandItem in $operandItems) {
    Freeze-NativeOperandVerticalGeometry $operandItem.Shape
  }
  Freeze-NativeFrameVerticalGeometry $FrameShape
  try { $FrameShape.ContainerProperties.LockMembership = $true } catch { }
  try { $FrameShape.ContainerProperties.ResizeAsNeeded = 0 } catch { }
}

function Set-NativeFragmentOperandWidthBinding($FrameShape, $OperandShapes) {
  $operandItems = @($OperandShapes)
  if ($operandItems.Count -eq 0) { return }

  $frameBounds = Get-ShapeBounds $FrameShape
  if ($null -eq $frameBounds) { return }
  $frameLeftFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', [double]$frameBounds.Left)
  $frameInitialWidth = [Math]::Max(0.1, [double]$frameBounds.Right - [double]$frameBounds.Left)
  $frameInitialWidthFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $frameInitialWidth)
  $hasFrameResizeControl = $false
  try { $hasFrameResizeControl = ($FrameShape.CellExistsU('Controls.Row_1.X', 0) -ne 0 -or $FrameShape.CellExistsU('Controls.Row_1', 0) -ne 0) } catch { }
  Restore-NativeFragmentHorizontalBinding $FrameShape $frameLeftFormula $frameInitialWidthFormula $hasFrameResizeControl

  $framePinX = Get-ShapeFormulaRef $FrameShape 'PinX'
  $frameWidth = Get-ShapeFormulaRef $FrameShape 'Width'
  $frameResizeControl = Get-ShapeFormulaRef $FrameShape 'Controls.Row_1'
  try { $FrameShape.ContainerProperties.LockMembership = $false } catch { }
  for ($i = 0; $i -lt $operandItems.Count; $i++) {
    $operandShape = $operandItems[$i]
    $listPosition = $i + 1
    if (-not (Insert-NativeFragmentListMember $FrameShape $operandShape $listPosition)) {
      throw ("Failed to bind native fragment operand as Visio list member: frame={0}, operand={1}" -f [int]$FrameShape.ID, [int]$operandShape.ID)
    }
    Set-CellFormula $operandShape 'PinX' ("IFERROR(LISTSHEETREF()!PinX,{0})" -f $framePinX)
    if ($hasFrameResizeControl) {
      Set-CellFormula $operandShape 'Width' 'IFERROR(LISTSHEETREF()!Controls.ROW_1,User.UserWidth)'
    }
    else {
      Set-CellFormula $operandShape 'Width' $frameWidth
    }
    Add-NativeFragmentMember $FrameShape $operandShape | Out-Null
  }
  Restore-NativeFragmentHorizontalBinding $FrameShape $frameLeftFormula $frameInitialWidthFormula $hasFrameResizeControl
  try { $FrameShape.ContainerProperties.LockMembership = $true } catch { }
  try { $FrameShape.ContainerProperties.ResizeAsNeeded = 0 } catch { }
}

function Get-NormalizedShapeBoundsForContainment($Shape) {
  $bounds = Get-ShapeBounds $Shape
  if ($null -eq $bounds) { return $null }

  $left = [Math]::Min([double]$bounds.Left, [double]$bounds.Right)
  $right = [Math]::Max([double]$bounds.Left, [double]$bounds.Right)
  $bottom = [Math]::Min([double]$bounds.Bottom, [double]$bounds.Top)
  $top = [Math]::Max([double]$bounds.Bottom, [double]$bounds.Top)

  try {
    $text = Get-ShapeTextTrimmed $Shape
    if (-not [string]::IsNullOrWhiteSpace($text)) {
      $pinX = [double]$Shape.CellsU('PinX').ResultIU
      $pinY = [double]$Shape.CellsU('PinY').ResultIU
      $locX = [double]$Shape.CellsU('LocPinX').ResultIU
      $locY = [double]$Shape.CellsU('LocPinY').ResultIU
      $txtPinX = [double]$Shape.CellsU('TxtPinX').ResultIU
      $txtPinY = [double]$Shape.CellsU('TxtPinY').ResultIU
      $txtLocX = [double]$Shape.CellsU('TxtLocPinX').ResultIU
      $txtLocY = [double]$Shape.CellsU('TxtLocPinY').ResultIU
      $txtW = [Math]::Abs([double]$Shape.CellsU('TxtWidth').ResultIU)
      $txtH = [Math]::Abs([double]$Shape.CellsU('TxtHeight').ResultIU)
      if ($txtW -gt 0.01 -and $txtH -gt 0.01) {
        $txtCenterX = $pinX - $locX + $txtPinX
        $txtCenterY = $pinY - $locY + $txtPinY
        $textLeft = $txtCenterX - $txtLocX
        $textBottom = $txtCenterY - $txtLocY
        $left = [Math]::Min($left, $textLeft)
        $right = [Math]::Max($right, $textLeft + $txtW)
        $bottom = [Math]::Min($bottom, $textBottom)
        $top = [Math]::Max($top, $textBottom + $txtH)
      }
    }
  } catch { }

  return [pscustomobject]@{
    Left = $left
    Right = $right
    Bottom = $bottom
    Top = $top
    CenterX = ($left + $right) / 2.0
    CenterY = ($bottom + $top) / 2.0
    Area = [Math]::Max(0.0, ($right - $left) * ($top - $bottom))
  }
}

function Get-NativeFinalOperandContentBottomInfo($Page, $FrameShape, $FrameBounds, [double]$OperandTopDistance, [double]$OperandBottomDistance, $ExcludeShapeIds, [double]$Padding) {
  $maxBottomDistance = $OperandBottomDistance
  $formulaBottomEdges = @()
  $continuousGap = [Math]::Max(0.65, (Get-NativeConnectionPointUnit) * 2.5)
  $candidateRows = @()

  foreach ($shape in @($Page.Shapes)) {
    try {
      $shapeId = [int]$shape.ID
      if ($ExcludeShapeIds.ContainsKey($shapeId)) { continue }
    } catch { continue }

    $masterName = Get-ShapeMasterName $shape
    if ($masterName -match '(?i)^(Actor lifeline|Object lifeline|Activation)') { continue }
    $isFragmentFrame = Test-NativeFragmentFrameShape $shape
    if (-not $isFragmentFrame) { continue }

    $bounds = Get-NormalizedShapeBoundsForContainment $shape
    if ($null -eq $bounds) { continue }
    if ($isFragmentFrame -and [double]$bounds.Area -ge ([double]$FrameBounds.Area - 0.01)) { continue }
    if ($bounds.Right -lt ([double]$FrameBounds.Left - 0.10) -or $bounds.Left -gt ([double]$FrameBounds.Right + 0.10)) { continue }

    $shapeTopDistance = Get-TopDistanceFromY ([double]$bounds.Top)
    $shapeBottomDistance = Get-TopDistanceFromY ([double]$bounds.Bottom)
    if ($shapeBottomDistance -lt ($OperandTopDistance - 0.05)) { continue }

    $candidateRows += [pscustomobject]@{
      Shape = $shape
      TopDistance = $shapeTopDistance
      BottomDistance = $shapeBottomDistance
    }
  }

  # Follow a continuous run of nested fragments in the final else/success operand.
  # Visio can shrink the owning alt to the direct operand members unless those
  # child fragments are allowed to extend the final operand bottom first.
  $reachableBottomDistance = $OperandBottomDistance
  foreach ($candidate in @($candidateRows | Sort-Object TopDistance)) {
    if ([double]$candidate.TopDistance -gt ($reachableBottomDistance + $continuousGap)) { continue }
    $reachableBottomDistance = [Math]::Max($reachableBottomDistance, ([double]$candidate.BottomDistance + $Padding))
    $maxBottomDistance = [Math]::Max($maxBottomDistance, ([double]$candidate.BottomDistance + $Padding))

    $shape = $candidate.Shape
    $pinY = Get-ShapeFormulaRef $shape 'PinY'
    $height = Get-ShapeFormulaRef $shape 'Height'
    $paddingFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $Padding)
    $formulaBottomEdges += ("({0}-({1}*0.5)-{2})" -f $pinY, $height, $paddingFormula)
  }

  return [pscustomobject]@{
    BottomDistance = $maxBottomDistance
    FormulaBottomEdges = $formulaBottomEdges
  }
}

function Set-NativeOperandBottomBinding($OperandShape, [double]$TopDistance, [double]$BottomDistance, $FormulaBottomEdges) {
  $formulaEdges = @($FormulaBottomEdges | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) })
  if ($formulaEdges.Count -eq 0) { return }

  $topY = [double]$script:PageHeight - $TopDistance
  $bottomY = [double]$script:PageHeight - $BottomDistance
  $topFormula = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $topY)
  $bottomConstant = [string]::Format([Globalization.CultureInfo]::InvariantCulture, '{0} in', $bottomY)
  $bottomFormula = Join-VisioFormulaExtrema 'MIN' (@($bottomConstant) + $formulaEdges)

  Set-CellFormula $OperandShape 'PinY' ("(({0})+({1}))*0.5" -f $topFormula, $bottomFormula)
  Set-CellFormula $OperandShape 'Height' ("MAX(0.05 in,({0})-({1}))" -f $topFormula, $bottomFormula)
}

function Normalize-NativeAltOperandRegions($Page) {
  $template = Get-Template 'uml-fragment-frame'
  $firstOperandTopOffset = 0.245
  $minOperandWidthRatio = 0.74
  $branchContentBottomPadding = 0.22
  if ($null -ne $template) {
    $firstOperandTopOffset = Get-TemplateNumber $template 'firstOperandTopOffset' $firstOperandTopOffset
    $minOperandWidthRatio = Get-TemplateNumber $template 'operandFullRegionMinWidthRatio' $minOperandWidthRatio
    $branchContentBottomPadding = Get-TemplateNumber $template 'branchContentBottomPadding' $branchContentBottomPadding
  }

  $allShapes = @($Page.Shapes)
  $frames = @()
  foreach ($shape in $allShapes) {
    if ((Get-ShapeTextTrimmed $shape) -ne 'alt') { continue }
    if ((Get-ShapeMasterName $shape) -notmatch '(?i)^Alternative fragment') { continue }
    $bounds = Get-ShapeBounds $shape
    if ($null -eq $bounds) { continue }
    $frames += [pscustomobject]@{
      Shape = $shape
      Bounds = $bounds
      Area = [double]$bounds.Area
      TopDistance = Get-TopDistanceFromY ([double]$bounds.Top)
      BottomDistance = Get-TopDistanceFromY ([double]$bounds.Bottom)
    }
  }
  if ($frames.Count -eq 0) { return }

  $assignments = @{}
  foreach ($frame in $frames) {
    try { $assignments[[int]$frame.Shape.ID] = @() } catch { }
  }

  foreach ($shape in $allShapes) {
    if ((Get-ShapeMasterName $shape) -notmatch '(?i)^Interaction operand') { continue }
    $text = Get-ShapeTextTrimmed $shape
    if ([string]::IsNullOrWhiteSpace($text) -or $text -eq $script:DefaultConditionPlaceholder) { continue }
    $bounds = Get-ShapeBounds $shape
    if ($null -eq $bounds) { continue }
    $operandWidth = [Math]::Max(0.1, [double]$bounds.Right - [double]$bounds.Left)
    $operandHeight = [Math]::Max(0.05, [double]$bounds.Top - [double]$bounds.Bottom)
    $operandTopDistance = Get-TopDistanceFromY ([double]$bounds.Top)
    $operandBottomDistance = Get-TopDistanceFromY ([double]$bounds.Bottom)

    $parent = $null
    foreach ($frame in $frames) {
      $frameBounds = $frame.Bounds
      $frameWidth = [Math]::Max(0.1, [double]$frameBounds.Right - [double]$frameBounds.Left)
      $horizontalOverlap = [Math]::Min([double]$bounds.Right, [double]$frameBounds.Right) - [Math]::Max([double]$bounds.Left, [double]$frameBounds.Left)
      $requiredOverlap = [Math]::Min(0.35, [Math]::Min($operandWidth, $frameWidth) * 0.45)
      if ($horizontalOverlap -lt $requiredOverlap) { continue }

      $topSlack = 0.85
      $bottomSlack = [Math]::Max(0.85, $operandHeight + 0.10)
      if ($operandTopDistance -lt ([double]$frame.TopDistance - $topSlack) -or $operandTopDistance -gt ([double]$frame.BottomDistance + $bottomSlack)) { continue }

      $leftAlignedToFrame = [Math]::Abs(([double]$bounds.Left) - ([double]$frameBounds.Left)) -le 0.75
      $rightAlignedToFrame = [Math]::Abs(([double]$bounds.Right) - ([double]$frameBounds.Right)) -le 0.75
      $spansFrameWidth = $horizontalOverlap -ge ([Math]::Min($operandWidth, $frameWidth) * $minOperandWidthRatio)
      $nearFrameHeader = (
        $operandTopDistance -ge ([double]$frame.TopDistance - 0.05) -and
        $operandTopDistance -le ([double]$frame.TopDistance + 0.85)
      )
      $startsInFrameLane = $operandTopDistance -ge ([double]$frame.TopDistance - 0.10) -and $operandTopDistance -le ([double]$frame.BottomDistance + 0.20)
      $firstConditionOperandForFrame = (
        $nearFrameHeader -and
        $spansFrameWidth -and
        [double]$bounds.Left -ge ([double]$frameBounds.Left - 0.90) -and
        [double]$bounds.Right -le ([double]$frameBounds.Right + 0.90)
      )
      $directElseOperandForFrame = (
        $startsInFrameLane -and
        ($spansFrameWidth -or $leftAlignedToFrame -or $rightAlignedToFrame)
      )
      if (-not ($firstConditionOperandForFrame -or $directElseOperandForFrame)) { continue }

      if ($null -eq $parent -or [double]$frame.Area -lt [double]$parent.Area) {
        $parent = $frame
      }
    }

    if ($null -ne $parent) {
      $parentId = [int]$parent.Shape.ID
      $assignments[$parentId] = @($assignments[$parentId]) + [pscustomobject]@{
        Shape = $shape
        Bounds = $bounds
        TopDistance = $operandTopDistance
        BottomDistance = $operandBottomDistance
      }
    }
  }

  foreach ($frame in @($frames | Sort-Object Area)) {
    $frameId = [int]$frame.Shape.ID
    $operands = @($assignments[$frameId] | Sort-Object TopDistance)
    if ($operands.Count -eq 0) { continue }

    $currentFrameBounds = Get-ShapeBounds $frame.Shape
    if ($null -eq $currentFrameBounds) { continue }
    $operandLeft = [Math]::Min([double]$currentFrameBounds.Left, [double]($operands | ForEach-Object { $_.Bounds.Left } | Measure-Object -Minimum).Minimum)
    $operandRight = [Math]::Max([double]$currentFrameBounds.Right, [double]($operands | ForEach-Object { $_.Bounds.Right } | Measure-Object -Maximum).Maximum)
    $firstTopDistance = [double]$operands[0].TopDistance
    $operandBottomDistance = [double]($operands | ForEach-Object { $_.BottomDistance } | Measure-Object -Maximum).Maximum
    # Keep the native fragment frame as the source of truth. Visio may materialize
    # the first operand at the master's default offset; do not let that operand
    # pull the formal alt frame upward into the preceding message row.
    $desiredTopDistance = [double]$frame.TopDistance
    $desiredBottomDistance = [Math]::Max([double]$frame.BottomDistance, $operandBottomDistance)
    $lastOperandTopDistance = if ($operands.Count -eq 1) { $desiredTopDistance + $firstOperandTopOffset } else { [double]$operands[$operands.Count - 1].TopDistance }
    $excludeShapeIds = @{}
    try { $excludeShapeIds[[int]$frame.Shape.ID] = $true } catch { }
    foreach ($operand in $operands) {
      try { $excludeShapeIds[[int]$operand.Shape.ID] = $true } catch { }
    }
    $contentBottomInfo = Get-NativeFinalOperandContentBottomInfo $Page $frame.Shape $currentFrameBounds $lastOperandTopDistance $desiredBottomDistance $excludeShapeIds $branchContentBottomPadding
    if ($null -ne $contentBottomInfo) {
      $desiredBottomDistance = [Math]::Max($desiredBottomDistance, [double]$contentBottomInfo.BottomDistance)
    }
    $desiredTopDistance = Snap-ToNativeConnectionPoint $desiredTopDistance
    $desiredBottomDistance = Snap-ToNativeConnectionPoint $desiredBottomDistance 'ceil'
    if ($desiredBottomDistance -le ($desiredTopDistance + 0.05)) { continue }

    Set-NativeShapeByTopDistances $frame.Shape $operandLeft $operandRight $desiredTopDistance $desiredBottomDistance
    $frameBounds = Get-ShapeBounds $frame.Shape
    if ($null -eq $frameBounds) { continue }
    $frameTopDistance = Get-TopDistanceFromY ([double]$frameBounds.Top)
    $frameBottomDistance = Get-TopDistanceFromY ([double]$frameBounds.Bottom)

    for ($i = 0; $i -lt $operands.Count; $i++) {
      $operand = $operands[$i]
      $topDistance = if ($i -eq 0) { $frameTopDistance + $firstOperandTopOffset } else { [double]$operand.TopDistance }
      $bottomDistance = if ($i + 1 -lt $operands.Count) { [double]$operands[$i + 1].TopDistance } else { $frameBottomDistance }
      if ($bottomDistance -le $topDistance) { continue }

      Set-NativeShapeByTopDistances $operand.Shape ([double]$frameBounds.Left) ([double]$frameBounds.Right) $topDistance $bottomDistance
      if ($i -eq 0) {
        # The first branch condition should not draw a top separator; only else operands provide visible branch lines.
        Set-CellFormulaForce $operand.Shape 'LinePattern' '0'
      }
      else {
        Set-CellFormulaForce $operand.Shape 'LinePattern' '2'
        Set-CellFormulaForce $operand.Shape 'LineColor' 'RGB(30,80,84)'
      }
      Bring-ToFront $operand.Shape
      Add-NativeFragmentMember $frame.Shape $operand.Shape | Out-Null
    }
    Set-NativeAltFrameOperandBinding $frame.Shape $operands $firstOperandTopOffset $desiredBottomDistance $contentBottomInfo.FormulaBottomEdges
  }
}

function Bind-NativeOptOperandRegions($Page) {
  $allShapes = @($Page.Shapes)
  foreach ($frameShape in $allShapes) {
    if ((Get-ShapeTextTrimmed $frameShape) -ne 'opt') { continue }
    if ((Get-ShapeMasterName $frameShape) -notmatch '(?i)^Alternative fragment') { continue }
    $frameBounds = Get-ShapeBounds $frameShape
    if ($null -eq $frameBounds) { continue }
    $operands = @()
    foreach ($shape in $allShapes) {
      if ((Get-ShapeMasterName $shape) -notmatch '(?i)^Interaction operand') { continue }
      if ((Get-ShapeTextTrimmed $shape) -notmatch '^\[[^\]]+\]') { continue }
      $bounds = Get-ShapeBounds $shape
      if ($null -eq $bounds) { continue }
      if (Test-PointInsideBounds $bounds $frameBounds) {
        $operands += $shape
      }
    }
    if ($operands.Count -eq 0) { continue }
    foreach ($operand in $operands) {
      Set-CellFormulaForce $operand 'LinePattern' '0'
      Bring-ToFront $operand
    }
    Set-NativeFragmentOperandWidthBinding $frameShape $operands
  }
}

function Set-NativeFragmentTexts($Shape, [string]$HeaderText, [string]$ParameterText = '') {
  Clear-ShapeTextRecursive $Shape
  $children = @()
  try {
    foreach ($child in @($Shape.Shapes)) {
      $pinY = 0.0
      try { $pinY = [double]$child.CellsU('PinY').ResultIU } catch { }
      $children += [pscustomobject]@{ Shape = $child; PinY = $pinY }
    }
  } catch { }
  $children = @($children | Sort-Object PinY -Descending)
  if ($children.Count -gt 0) {
    Set-NativeShapeText $children[0].Shape $HeaderText
    Set-NativeShapeTextColor $children[0].Shape 'RGB(30,80,84)'
    Set-CellFormula $children[0].Shape 'Para.HorzAlign' '1'
    Set-CellFormula $children[0].Shape 'VerticalAlign' '1'
    if ($children.Count -gt 1 -and -not [string]::IsNullOrWhiteSpace($ParameterText)) {
      Set-NativeShapeText $children[1].Shape $ParameterText
      Set-NativeShapeTextColor $children[1].Shape 'RGB(30,80,84)'
    }
  }
  else {
    Set-NativeShapeText $Shape $HeaderText
    Set-NativeShapeTextColor $Shape 'RGB(30,80,84)'
    Set-CellFormula $Shape 'Para.HorzAlign' '1'
    Set-CellFormula $Shape 'VerticalAlign' '1'
  }
}

function Format-NativeConditionOperandText([string]$Text) {
  $trimmed = ([string]$Text).Trim()
  if ([string]::IsNullOrWhiteSpace($trimmed)) { return '' }
  if ($trimmed.StartsWith('[') -and $trimmed.EndsWith(']')) { return $trimmed }
  return "[$trimmed]"
}

function Set-NativeInitialConditionOperand($ConditionOperands, $FrameShape, [string]$ConditionText) {
  if ([string]::IsNullOrWhiteSpace($ConditionText)) { return $null }
  if ($null -eq $ConditionOperands -or @($ConditionOperands).Count -eq 0) {
    throw "Native fragment did not expose a [條件] placeholder to replace."
  }

  $shape = @($ConditionOperands | Sort-Object {
    try { -1.0 * [double]$_.CellsU('PinY').ResultIU } catch { 0 }
  })[0]
  Set-NativeShapeText $shape (Format-NativeConditionOperandText $ConditionText)
  Set-NativeShapeTextColor $shape 'RGB(30,80,84)'
  Set-CellFormula $shape 'Para.HorzAlign' '0'
  Set-CellFormula $shape 'VerticalAlign' '1'
  $template = Get-Template 'uml-fragment-frame'
  $offsetX = if ($null -ne $template) { Get-TemplateNumber $template 'initialConditionOffsetX' 0.1 } else { 0.1 }
  $offsetY = if ($null -ne $template) { Get-TemplateNumber $template 'initialConditionOffsetY' 0.32 } else { 0.32 }
  $conditionHeight = if ($null -ne $template) { Get-TemplateNumber $template 'initialConditionHeight' 0.22 } else { 0.22 }
  $frameBounds = Get-ShapeBounds $FrameShape
  if ($null -ne $frameBounds) {
    $frameLeft = [double]$frameBounds.Left
    $frameTop = [double]($script:PageHeight - [double]$frameBounds.Top)
    $frameWidth = [Math]::Max(0.4, [double]$frameBounds.Right - [double]$frameBounds.Left)
    $conditionWidth = [Math]::Max(0.35, $frameWidth - $offsetX - 0.2)
    Resize-NativeShapeByTopLeft $shape ($frameLeft + $offsetX) ($frameTop + $offsetY) $conditionWidth $conditionHeight
  }
  Add-NativeFragmentMember $FrameShape $shape | Out-Null
  Bring-ToFront $shape
  return $shape
}

function Get-NativeFragmentHeaderText([string]$Kind, [string]$Label) {
  switch ($Kind) {
    'alt' { return 'alt' }
    'opt' { return 'opt' }
    'loop' { return 'loop' }
    'ref' { return 'ref' }
    'group' {
      if (-not [string]::IsNullOrWhiteSpace($Label)) { return $Label }
      return 'group'
    }
    default {
      if (-not [string]::IsNullOrWhiteSpace($Label)) { return $Label }
      return $Kind
    }
  }
}

function Get-NativeFragmentParameterText([string]$Kind, [string]$Label) {
  if ($Kind -eq 'loop' -and -not [string]::IsNullOrWhiteSpace($Label) -and $Label -ne $Kind) {
    return $Label
  }
  return ''
}

function Hide-PlaceholderInteractionOperandShape($Shape) {
  try { $Shape.Text = '' } catch { }
  foreach ($cellName in @('LinePattern', 'FillPattern')) {
    try { $Shape.CellsU($cellName).FormulaU = '0' } catch { }
  }
  try { $Shape.CellsU('Width').FormulaU = '0.01 in' } catch { }
  try { $Shape.CellsU('Height').FormulaU = '0.01 in' } catch { }
  try { $Shape.CellsU('PinX').FormulaU = '-100 in' } catch { }
  try { $Shape.CellsU('PinY').FormulaU = '-100 in' } catch { }
}

function Remove-PlaceholderInteractionOperands($Page) {
  foreach ($shape in @($Page.Shapes)) {
    try {
      $masterName = ''
      try { $masterName = [string]$shape.Master.NameU } catch { }
      $text = ''
      try { $text = ([string]$shape.Text).Trim() } catch { }
      if ($masterName -match '(?i)^Interaction operand' -and $text -eq $script:DefaultConditionPlaceholder) {
        Hide-PlaceholderInteractionOperandShape $shape
      }
    } catch { }
  }
}

function Add-NativeFragmentFrame($Page, $Doc, $Frame) {
  $template = Get-Template 'uml-fragment-frame'
  if ($null -eq $template) {
    throw "Native fragment template missing: uml-fragment-frame"
  }

  $kind = [string]$Frame.kind
  $label = [string]$Frame.label
  $left = [double]$Frame.left
  $top = [double]$Frame.top
  $width = [double]$Frame.width
  $height = [double]$Frame.height
  $unit = Get-NativeConnectionPointUnit
  $top = Snap-ToNativeConnectionPoint $top
  if ($kind -eq 'ref') {
    $height = $unit * 6.0
  }
  else {
    $bottom = Snap-ToNativeConnectionPoint ($top + $height)
    if ($bottom -le ($top + 0.01)) { $bottom = $top + $unit }
    $height = $bottom - $top
  }
  $horizontal = Get-FragmentHorizontalClearance $Page $left $width
  $left = [double]$horizontal.Left
  $width = [double]$horizontal.Width

  $masterByKind = Get-ObjectPropertyValue $template 'masterByKind' $null
  $masterNames = Get-TemplateStringArray $masterByKind $kind @()
  if ($masterNames.Count -eq 0 -and ($kind -eq 'ref' -or $kind -eq 'group')) {
    $masterNames = Get-TemplateStringArray $masterByKind 'other' @('Other fragment')
  }
  if ($masterNames.Count -eq 0) {
    throw "No native UML fragment master mapping for frame kind '$kind'"
  }

  $existingShapeIds = @{}
  foreach ($existing in @($Page.Shapes)) {
    try { $existingShapeIds[[int]$existing.ID] = $true } catch { }
  }

  $master = Get-Master $Doc $masterNames
  Write-NativeBuildStage ("fragment-drop-start kind={0}" -f $kind)
  $shape = $Page.Drop($master, ($left + ($width / 2.0)), (Convert-Y ($top + ($height / 2.0))))
  Write-NativeBuildStage ("fragment-drop-done kind={0}" -f $kind)
  $conditionPlaceholders = @()
  Write-NativeBuildStage ("fragment-placeholder-scan-start kind={0}" -f $kind)
  foreach ($newShape in @($Page.Shapes)) {
    try {
      if ($existingShapeIds.ContainsKey([int]$newShape.ID) -or [int]$newShape.ID -eq [int]$shape.ID) { continue }
      $newMaster = ''
      try { $newMaster = [string]$newShape.Master.NameU } catch { }
      $newText = ''
      try { $newText = ([string]$newShape.Text).Trim() } catch { }
      if ($newMaster -match '(?i)Interaction operand' -and $newText -eq $script:DefaultConditionPlaceholder) {
        if ($kind -eq 'alt' -or $kind -eq 'opt') {
          $conditionPlaceholders += $newShape
        }
        else {
          Hide-PlaceholderInteractionOperandShape $newShape
        }
      }
    } catch { }
  }
  Write-NativeBuildStage ("fragment-placeholder-scan-done kind={0} count={1}" -f $kind, @($conditionPlaceholders).Count)
  Write-NativeBuildStage ("fragment-resize-start kind={0}" -f $kind)
  Resize-NativeShapeByTopLeft $shape $left $top $width $height
  Write-NativeBuildStage ("fragment-resize-done kind={0}" -f $kind)
  $conditionText = ''
  if ($kind -eq 'alt' -or $kind -eq 'opt') {
    $conditionText = [string](Get-ObjectPropertyValue $Frame 'condition' '')
    if ($kind -eq 'opt' -and [string]::IsNullOrWhiteSpace($conditionText) -and -not [string]::IsNullOrWhiteSpace($label) -and $label -ne 'opt') {
      $conditionText = if ($label.StartsWith('[') -and $label.EndsWith(']')) { $label } else { "[$label]" }
    }
  }
  $parameterText = Get-NativeFragmentParameterText $kind $label
  if ($kind -eq 'opt' -and -not [string]::IsNullOrWhiteSpace($conditionText) -and @($conditionPlaceholders).Count -eq 0) {
    $parameterText = $conditionText
  }
  Write-NativeBuildStage ("fragment-text-start kind={0}" -f $kind)
  Set-NativeFragmentTexts $shape (Get-NativeFragmentHeaderText $kind $label) $parameterText
  Write-NativeBuildStage ("fragment-text-done kind={0}" -f $kind)
  if ($kind -eq 'alt' -or ($kind -eq 'opt' -and @($conditionPlaceholders).Count -gt 0)) {
    Write-NativeBuildStage ("fragment-condition-start kind={0}" -f $kind)
    Set-NativeInitialConditionOperand $conditionPlaceholders $shape $conditionText | Out-Null
    Write-NativeBuildStage ("fragment-condition-done kind={0}" -f $kind)
  }
  Write-NativeBuildStage ("fragment-send-back-start kind={0}" -f $kind)
  Send-ToBack $shape
  Write-NativeBuildStage ("fragment-send-back-done kind={0}" -f $kind)
  return $shape
}

function Add-Frame($Page, $Doc, $Frame) {
  try {
    return Add-NativeFragmentFrame $Page $Doc $Frame
  }
  catch {
    throw "Unable to create native UML fragment frame '$([string]$Frame.kind)' at top $([string]$Frame.top): $($_.Exception.Message)"
  }

  $left = [double]$Frame.left
  $top = [double]$Frame.top
  $width = [double]$Frame.width
  $height = [double]$Frame.height
  $kind = [string]$Frame.kind
  $label = [string]$Frame.label

  $shape = $Page.DrawRectangle($left, (Convert-Y ($top + $height)), ($left + $width), (Convert-Y $top))
  Set-CellFormula $shape 'FillPattern' '0'
  Style-GreenLine $shape
  Send-ToBack $shape

  if ($label) {
    $maxLabelWidth = [Math]::Max(0.55, $width - 0.18)
    $minLabelWidth = if ($kind -eq 'group' -or $kind -eq 'loop') { 1.05 } else { 0.58 }
    $labelWidth = Measure-LabelWidth $label $minLabelWidth $maxLabelWidth
    $tabTemplate = Get-Template 'clipped-header-tab'
    $tabHeight = if ($null -ne $tabTemplate) { Get-TemplateNumber $tabTemplate 'defaultHeight' 0.28 } else { 0.28 }
    $textInsetX = if ($null -ne $tabTemplate) { Get-TemplateNumber $tabTemplate 'textInsetX' 0.04 } else { 0.04 }
    $textInsetY = if ($null -ne $tabTemplate) { Get-TemplateNumber $tabTemplate 'textInsetY' 0.055 } else { 0.055 }
    $textHeight = if ($null -ne $tabTemplate) { Get-TemplateNumber $tabTemplate 'textHeight' 0.17 } else { 0.17 }
    $labelColor = if ($null -ne $tabTemplate) { Get-TemplateStyleString $tabTemplate 'textColor' 'RGB(30,80,84)' } else { 'RGB(30,80,84)' }
    $labelFont = if ($null -ne $tabTemplate) { Get-TemplateStyleString $tabTemplate 'font' 'Microsoft JhengHei' } else { 'Microsoft JhengHei' }
    $labelFontSize = if ($null -ne $tabTemplate) { Get-TemplateStyleNumber $tabTemplate 'fontSize' 8 } else { 8 }
    Add-ClippedHeaderTab $Page $left $top $labelWidth $tabHeight | Out-Null
    $align = if ($kind -eq 'group' -or $kind -eq 'loop') { 'center' } else { 'left' }
    Add-Text $Page ($left + $textInsetX) ($top + $textInsetY) ([Math]::Max(0.1, $labelWidth - ($textInsetX * 2))) $textHeight $label $labelColor $labelFontSize $align $labelFont | Out-Null
  }
  return $shape
}

function Lock-SectionDividerPart($Shape) {
  foreach ($cellName in @('LockWidth', 'LockHeight', 'LockCalcWH', 'LockAspect', 'LockMoveX')) {
    Set-CellFormula $Shape $cellName '1'
  }
  Set-CellFormula $Shape 'LockMoveY' '0'
}

function Prepare-SectionDividerTitleBox($Shape) {
  foreach ($cellName in @('LockWidth', 'LockHeight', 'LockCalcWH', 'LockAspect', 'LockMoveX', 'LockMoveY')) {
    Set-CellFormula $Shape $cellName '0'
  }
}

function Add-Section($Page, $Section) {
  $left = [double]$Section.left
  $right = [double]$Section.right
  $top = [double]$Section.top
  $label = [string]$Section.label
  $template = Get-Template 'section-divider'
  $lineOffset = if ($null -ne $template) { Get-TemplateNumber $template 'lineOffset' 0.04 } else { 0.04 }
  $lineColor = if ($null -ne $template) { Get-TemplateString $template 'lineColor' 'RGB(30,80,84)' } else { 'RGB(30,80,84)' }
  $lineWeight = if ($null -ne $template) { Get-TemplateString $template 'lineWeight' '1.25 pt' } else { '1.25 pt' }
  $labelBoxHeight = if ($null -ne $template) { Get-TemplateNumber $template 'labelBoxHeight' 0.34 } else { 0.34 }
  $labelBoxMinWidth = if ($null -ne $template) { Get-TemplateNumber $template 'labelBoxMinWidth' 1.0 } else { 1.0 }
  $labelCharWidth = if ($null -ne $template) { Get-TemplateNumber $template 'labelCharWidth' 0.13 } else { 0.13 }
  $labelBoxMaxWidth = if ($null -ne $template) { Get-TemplateNumber $template 'labelBoxMaxWidth' 3.2 } else { 3.2 }
  $labelFillColor = if ($null -ne $template) { Get-TemplateString $template 'labelFillColor' 'RGB(255,255,255)' } else { 'RGB(255,255,255)' }
  $labelTextColor = if ($null -ne $template) { Get-TemplateString $template 'labelTextColor' 'RGB(0,0,0)' } else { 'RGB(0,0,0)' }
  $labelFont = if ($null -ne $template) { Get-TemplateString $template 'labelFont' 'Microsoft JhengHei' } else { 'Microsoft JhengHei' }
  $labelFontSize = if ($null -ne $template) { Get-TemplateNumber $template 'labelFontSize' 9 } else { 9 }
  $labelFontBold = $false
  if ($null -ne $template) {
    try { $labelFontBold = [System.Convert]::ToBoolean((Get-ObjectPropertyValue $template 'labelFontBold' $false)) } catch { $labelFontBold = $false }
  }
  $y = Convert-Y $top
  $line1 = $Page.DrawLine($left, $y + $lineOffset, $right, $y + $lineOffset)
  $line2 = $Page.DrawLine($left, $y - $lineOffset, $right, $y - $lineOffset)
  foreach ($line in @($line1, $line2)) {
    try { $line.NameU = ("section-divider-line-{0}" -f $line.ID) } catch { }
    Set-CellFormula $line 'LineColor' $lineColor
    Set-CellFormula $line 'LineWeight' $lineWeight
    Set-CellFormula $line 'LinePattern' '1'
    Lock-SectionDividerPart $line
  }
  $availableLabelWidth = [Math]::Max($labelBoxMinWidth, ($right - $left) - 0.6)
  $maxLabelWidth = [Math]::Min($labelBoxMaxWidth, $availableLabelWidth)
  $measuredLabelWidth = Measure-LabelWidth $label $labelBoxMinWidth $maxLabelWidth
  $legacyLabelWidth = [Math]::Max($labelBoxMinWidth, 0.24 + ($label.Length * $labelCharWidth))
  $boxWidth = [Math]::Min($maxLabelWidth, [Math]::Max($measuredLabelWidth, $legacyLabelWidth))
  $boxLeft = ($left + $right - $boxWidth) / 2
  $halfHeight = $labelBoxHeight / 2.0
  $box = $Page.DrawRectangle($boxLeft, $y - $halfHeight, ($boxLeft + $boxWidth), $y + $halfHeight)
  try { $box.NameU = ("section-divider-title-{0}" -f $box.ID) } catch { }
  Set-CellFormula $box 'FillPattern' '1'
  Set-CellFormula $box 'FillForegnd' $labelFillColor
  Set-CellFormula $box 'LineColor' $lineColor
  Set-CellFormula $box 'LineWeight' $lineWeight
  Set-CellFormula $box 'LinePattern' '1'
  Prepare-SectionDividerTitleBox $box
  Set-ShapeText $box $label $labelTextColor $labelFontSize $labelFont $labelFontBold
  Bring-ToFront $box
}

function Add-OrangePointer($Page, $Pointer) {
  $left = [double]$Pointer.left
  $top = [double]$Pointer.top
  $width = [double]$Pointer.width
  $height = [double]$Pointer.height
  $text = Format-CommonSvgReferenceText ([string]$Pointer.text)
  if (Test-CommonSvgPointerText $text) {
    $owningRef = $null
    foreach ($shape in @($Page.Shapes)) {
      if ((Get-ShapeTextTrimmed $shape) -ne 'ref') { continue }
      if (-not (Test-NativeFragmentFrameShape $shape)) { continue }
      $bounds = Get-ShapeBounds $shape
      if ($null -eq $bounds) { continue }
      $right = $left + $width
      $horizontalOverlap = [Math]::Min($right, [double]$bounds.Right) - [Math]::Max($left, [double]$bounds.Left)
      if ($horizontalOverlap -lt ([Math]::Min($width, [double]$bounds.Right - [double]$bounds.Left) * 0.40)) { continue }
      $frameTopDistance = Get-TopDistanceFromY ([double]$bounds.Top)
      $frameBottomDistance = Get-TopDistanceFromY ([double]$bounds.Bottom)
      if ($top -lt ($frameTopDistance - 0.25) -or $top -gt ($frameBottomDistance + 0.25)) { continue }
      if ($null -eq $owningRef -or [double]$bounds.Area -lt [double]$owningRef.Bounds.Area) {
        $owningRef = [pscustomobject]@{
          Bounds = $bounds
          TopDistance = $frameTopDistance
          BottomDistance = $frameBottomDistance
        }
      }
    }

    if ($null -ne $owningRef) {
      $sideInset = 0.23
      $bottomInset = 0.08
      $left = [Math]::Max($left, [double]$owningRef.Bounds.Left + $sideInset)
      $maxRight = [double]$owningRef.Bounds.Right - $sideInset
      if (($left + $width) -gt $maxRight) {
        $width = [Math]::Max(0.1, $maxRight - $left)
      }
      $minimumTop = [double]$owningRef.TopDistance + 0.95
      if ($top -lt $minimumTop) { $top = $top + 0.30 }
      $maximumTop = [double]$owningRef.BottomDistance - $height - $bottomInset
      if ($top -gt $maximumTop) { $top = $maximumTop }
    }
  }
  $template = Get-Template 'orange-pointer-strip'
  $fillColor = if ($null -ne $template) { Get-TemplateStyleString $template 'fillColor' 'RGB(244,161,0)' } else { 'RGB(244,161,0)' }
  $linePattern = if ($null -ne $template) { [string](Get-TemplateStyleNumber $template 'linePattern' 0) } else { '0' }
  $textColor = if ($null -ne $template) { Get-TemplateStyleString $template 'textColor' 'RGB(0,0,0)' } else { 'RGB(0,0,0)' }
  $font = if ($null -ne $template) { Get-TemplateStyleString $template 'font' 'Microsoft JhengHei' } else { 'Microsoft JhengHei' }
  $fontSize = if ($null -ne $template) { Get-TemplateStyleNumber $template 'fontSize' 8 } else { 8 }
  $align = if ($null -ne $template) { Get-TemplateStyleString $template 'align' 'center' } else { 'center' }
  $rect = $Page.DrawRectangle($left, (Convert-Y ($top + $height)), ($left + $width), (Convert-Y $top))
  try { $rect.NameU = ("orange-pointer-strip-{0}" -f $rect.ID) } catch { }
  Set-CellFormula $rect 'FillPattern' '1'
  Set-CellFormula $rect 'FillForegnd' $fillColor
  Set-CellFormula $rect 'LinePattern' $linePattern
  Set-ShapeText $rect $text $textColor $fontSize $font
  switch ($align) {
    'left' { Set-CellFormula $rect 'Para.HorzAlign' '0' }
    'right' { Set-CellFormula $rect 'Para.HorzAlign' '2' }
    default { Set-CellFormula $rect 'Para.HorzAlign' '1' }
  }
  Bring-ToFront $rect
  return $rect
}

function Add-TextFromTemplate($Page, $TextSpec) {
  $templateName = [string](Get-ObjectPropertyValue $TextSpec 'template' '')
  $template = Get-Template $templateName
  if ($null -eq $template) { return $null }

  $left = [double]$TextSpec.left
  $top = [double]$TextSpec.top
  $width = [double]$TextSpec.width
  $height = if ($TextSpec.height) { [double]$TextSpec.height } else { Get-TemplateNumber $template 'defaultHeight' 0.22 }
  $text = [string]$TextSpec.text
  $type = [string](Get-ObjectPropertyValue $template 'type' 'text')
  $textColor = Get-TemplateStyleString $template 'textColor' ([string](Get-ObjectPropertyValue $TextSpec 'color' 'RGB(0,0,0)'))
  $font = Get-TemplateStyleString $template 'font' 'Microsoft JhengHei'
  $fontSize = Get-TemplateStyleNumber $template 'fontSize' 8
  if ($TextSpec.size) { $fontSize = [double]$TextSpec.size }
  $align = Get-TemplateStyleString $template 'align' ([string](Get-ObjectPropertyValue $TextSpec 'align' 'center'))

  if ($type -eq 'text-strip' -or $templateName -eq 'orange-pointer-strip') {
    return Add-OrangePointer $Page $TextSpec
  }

  if ($type -eq 'box-text' -or $templateName -eq 'note-card') {
    $fillColor = Get-TemplateStyleString $template 'fillColor' 'RGB(255,242,161)'
    $lineColor = Get-TemplateStyleString $template 'lineColor' 'RGB(176,21,19)'
    $shape = Add-TextWithBox $Page $left $top $width $height $text $textColor $fontSize $align $fillColor $lineColor $font
    Set-CellFormula $shape 'LineWeight' (Get-TemplateStyleString $template 'lineWeight' '1.25 pt')
    return $shape
  }

  return Add-Text $Page $left $top $width $height $text $textColor $fontSize $align $font
}

function Add-RefCommonSvgBlock($Page, $Block) {
  $template = Get-Template 'ref-common-svg-block'
  if ($null -eq $template) { return $false }

  $left = [double]$Block.left
  $top = [double]$Block.top
  $width = [double]$Block.width
  $methodText = [string](Get-ObjectPropertyValue $Block 'methodText' '')
  $pointerText = [string](Get-ObjectPropertyValue $Block 'pointerText' '')

  $method = Get-ObjectPropertyValue $template 'methodText' $null
  if (-not [string]::IsNullOrWhiteSpace($methodText) -and $null -ne $method) {
    $methodTop = $top + (Get-TemplateNumber $method 'topOffset' 0.40)
    $methodHeight = Get-TemplateNumber $method 'height' 0.34
    $sideInset = Get-TemplateNumber $method 'sideInset' 0.18
    $methodStyle = Get-ObjectPropertyValue $method 'style' $null
    $methodColor = Get-TemplateStyleString $method 'textColor' 'RGB(0,0,0)'
    if ($null -ne $methodStyle) { $methodColor = Get-TemplateString $methodStyle 'textColor' $methodColor }
    $methodFont = if ($null -ne $methodStyle) { Get-TemplateString $methodStyle 'font' 'Microsoft JhengHei' } else { 'Microsoft JhengHei' }
    $methodSize = if ($null -ne $methodStyle) { Get-TemplateNumber $methodStyle 'fontSize' 8 } else { 8 }
    $methodAlign = if ($null -ne $methodStyle) { Get-TemplateString $methodStyle 'align' 'center' } else { 'center' }
    Add-Text $Page ($left + $sideInset) $methodTop ([Math]::Max(0.1, $width - ($sideInset * 2))) $methodHeight $methodText $methodColor $methodSize $methodAlign $methodFont | Out-Null
  }

  $pointer = Get-ObjectPropertyValue $template 'pointer' $null
  if (-not [string]::IsNullOrWhiteSpace($pointerText) -and $null -ne $pointer) {
    $pointerTop = $top + (Get-TemplateNumber $pointer 'topOffset' 1.03)
    $pointerHeight = Get-TemplateNumber $pointer 'height' 0.25
    $pointerInset = Get-TemplateNumber $pointer 'sideInset' 0.23
    Add-OrangePointer $Page ([pscustomobject]@{
      left = $left + $pointerInset
      top = $pointerTop
      width = [Math]::Max(0.1, $width - ($pointerInset * 2))
      height = $pointerHeight
      text = $pointerText
    }) | Out-Null
  }

  return $true
}

function Add-NativeInteractionOperand($Page, $Doc, $Sep) {
  $template = Get-Template 'uml-fragment-frame'
  if ($null -eq $template) {
    throw "Native fragment template missing: uml-fragment-frame"
  }

  $operandMasterNames = Get-TemplateStringArray $template 'interactionOperandMasterNames' @('Interaction operand', 'Interaction operand.53')
  $left = [double]$Sep.left
  $right = [double]$Sep.right
  $top = Snap-ToNativeConnectionPoint ([double]$Sep.top)
  $label = Format-NativeConditionOperandText ([string]$Sep.label)
  $height = Get-TemplateNumber $template 'operandHeight' 0.36
  if ($Sep.height) { $height = [double]$Sep.height }

  $master = Get-Master $Doc $operandMasterNames
  $shape = $Page.Drop($master, 0, 0)
  Resize-NativeShapeByTopLeft $shape $left $top ([Math]::Max(0.1, $right - $left)) $height
  if ($label) {
    Set-NativeShapeText $shape $label
    Set-NativeShapeTextColor $shape 'RGB(30,80,84)'
  }
  $isDashed = $true
  try {
    if ($null -ne $Sep.PSObject.Properties['dashed']) {
      $isDashed = [bool]$Sep.dashed
    }
  } catch { }
  $linePattern = if ($isDashed) { '2' } else { '1' }
  Set-CellFormulaForce $shape 'LinePattern' $linePattern
  Set-CellFormulaForce $shape 'LineColor' 'RGB(30,80,84)'
  Bring-ToFront $shape
  return $shape
}

function Add-Separator($Page, $Doc, $Sep) {
  try {
    return Add-NativeInteractionOperand $Page $Doc $Sep
  }
  catch {
    throw "Unable to create native UML interaction operand at top $([string]$Sep.top): $($_.Exception.Message)"
  }
}

function Test-VisualSeparatorShape($Shape) {
  $nameU = ''
  try { $nameU = [string]$Shape.NameU } catch { }
  if ($nameU -match '^section-divider-(line|title)-') { return $true }

  $masterName = Get-ShapeMasterName $Shape
  $text = Get-ShapeTextTrimmed $Shape
  return ($masterName -match '(?i)^Interaction operand' -and -not [string]::IsNullOrWhiteSpace($text))
}

function Bring-VisualSeparatorsToFront($Page) {
  $count = 0
  foreach ($shape in @($Page.Shapes)) {
    if (Test-VisualSeparatorShape $shape) {
      Bring-ToFront $shape
      $count++
    }
  }
  return $count
}

function Set-SelfMessageTextBlock($Shape, $Msg, [double]$FallbackWidth) {
  $text = [string]$Msg.text
  $lineCount = @($text -split "`n").Count
  $labelWidth = if ($Msg.labelWidth) { [double]$Msg.labelWidth } else { Measure-LabelWidth (($text -replace "`n", '')) 1.2 2.5 }
  $labelHeight = [Math]::Max(0.22, $lineCount * 0.18)
  $labelSide = if ($Msg.labelSide) { [string]$Msg.labelSide } else { 'right' }
  $allowCentered = $false
  try { $allowCentered = [System.Convert]::ToBoolean((Get-ObjectPropertyValue $Msg 'allowCenteredLabel' $false)) } catch { }
  if ($labelSide -notin @('right', 'left')) {
    $labelSide = if ($allowCentered) { 'center' } else { 'right' }
  }
  $textPinYFormula = 'Height*0.5'
  $textPinXFormula = 'Width*0.5'

  Set-CellFormulaForce $Shape 'TxtWidth' ("{0} in" -f $labelWidth)
  Set-CellFormulaForce $Shape 'TxtHeight' ("{0} in" -f $labelHeight)
  Set-CellFormulaForce $Shape 'TxtLocPinX' 'TxtWidth*0.5'
  Set-CellFormulaForce $Shape 'TxtLocPinY' 'TxtHeight*0.5'

  if ($labelSide -eq 'right') {
    $offsetX = if ($Msg.labelOffsetX) { [double]$Msg.labelOffsetX } else { 0.12 }
    $textPinXFormula = ("Width+{0} in+{1} in" -f $offsetX, ($labelWidth / 2))
    Set-CellFormula $Shape 'Para.HorzAlign' '0'
  }
  elseif ($labelSide -eq 'left') {
    $textPinXFormula = ("-0.12 in-{0} in" -f ($labelWidth / 2))
    Set-CellFormula $Shape 'Para.HorzAlign' '2'
  }
  else {
    $textPinXFormula = 'Width*0.5'
    Set-CellFormula $Shape 'Para.HorzAlign' '1'
  }

  Set-AdjustableMessageTextPosition $Shape $textPinXFormula $textPinYFormula
}

function Set-ParticipantMessageTextBlock($Shape, $Msg) {
  $text = [string]$Msg.text
  $lineCount = @($text -split "`n").Count
  $labelWidth = if ($Msg.labelWidth) { [double]$Msg.labelWidth } else { Measure-LabelWidth (($text -replace "`n", '')) 1.25 3.10 }
  $labelHeight = [Math]::Max(0.22, $lineCount * 0.18)

  Set-CellFormulaForce $Shape 'TxtWidth' ("{0} in" -f $labelWidth)
  Set-CellFormulaForce $Shape 'TxtHeight' ("{0} in" -f $labelHeight)
  Set-CellFormulaForce $Shape 'TxtLocPinX' 'TxtWidth*0.5'
  Set-CellFormulaForce $Shape 'TxtLocPinY' 'TxtHeight*0.5'
  Set-CellFormula $Shape 'Para.HorzAlign' '1'
  Set-AdjustableMessageTextPosition $Shape 'Width*0.5' 'Height*0.5+TxtHeight*0.5+0.04 in'
}

function Add-Message($Page, $Doc, $Participants, $Msg) {
  $kind = [string]$Msg.kind
  $from = [string]$Msg.from
  $to = [string]$Msg.to
  $top = Snap-ToNativeConnectionPoint ([double]$Msg.top)
  $text = Normalize-CommonMethodNotation ([string]$Msg.text)
  try { $Msg.text = $text } catch { }
  $red = [bool]$Msg.red
  $dashed = [bool]$Msg.dashed
  $messageParts = @()
  Write-NativeBuildStage ("message-start kind={0} from={1} to={2} top={3:N4} text={4}" -f $kind, $from, $to, $top, (($text -replace "`r|`n", ' ') -replace '\s+', ' '))
  $layoutRole = [string](Get-ObjectPropertyValue $Msg 'layoutRole' '')
  if ((Test-CommonMethodMessageText $text) -and $layoutRole -ne 'ref-self') {
    $commonMethodDisplay = (($text -replace "`r|`n", ' ') -replace '\s+', ' ')
    throw "CommonFunc/CommonUtil method '$commonMethodDisplay' must be modeled as a native ref fragment with layoutRole=ref-self, not as a main-flow message/self-call."
  }

  function Get-ConnectionPointOffset($Participant, [int]$Row) {
    $y = 0.0
    $formula = ''
    try { $y = [double]$Participant.shape.CellsSRC(7, $Row, 1).ResultIU } catch { return $null }
    try { $formula = [string]$Participant.shape.CellsSRC(7, $Row, 1).FormulaU } catch { }

    if ($Participant.connectionMode -eq 'lifeline-line' -or $formula -match '(?i)^Height') {
      return [Math]::Max(0.0, ([double]$Participant.height - $y))
    }
    if ($Participant.connectionMode -eq 'uml-lifeline' -or $formula -match '^-') {
      return [Math]::Max(0.0, -1.0 * $y)
    }
    if ($Participant.native) {
      return [Math]::Max(0.0, ([double]$Participant.height - $y))
    }
    return [Math]::Max(0.0, [Math]::Abs($y))
  }

  function Get-ConnectionInfo($Participant, [double]$MessageTop) {
    $key = "{0:N3}" -f $MessageTop
    if (-not $Participant.anchors.ContainsKey($key)) {
      $relativeY = [Math]::Min([Math]::Max(($MessageTop - [double]$Participant.top), 0.0), [double]$Participant.height)
      $bestRow = -1
      $bestOffset = 0.0
      $bestGap = [double]::PositiveInfinity
      $rowCount = 0
      try { $rowCount = [int]$Participant.shape.RowCount(7) } catch { $rowCount = 0 }
      for ($row = 0; $row -lt $rowCount; $row++) {
        $offset = Get-ConnectionPointOffset $Participant $row
        if ($null -eq $offset) { continue }
        $gap = [Math]::Abs([double]$offset - $relativeY)
        if ($gap -lt $bestGap) {
          $bestGap = $gap
          $bestRow = $row
          $bestOffset = [double]$offset
        }
      }
      if ($bestRow -lt 0) {
        throw "No native UML lifeline connection point found for participant '$([string]$Participant.id)' at top $MessageTop. Message endpoints must glue to existing connection points."
      }
      $Participant.anchors[$key] = [pscustomobject]@{
        CellName = ("Connections.X{0}" -f ($bestRow + 1))
        Top = ([double]$Participant.top + $bestOffset)
        Offset = $bestOffset
        Row = ($bestRow + 1)
      }
    }
    return $Participant.anchors[$key]
  }

  function Glue-MessageEndpoint($Shape, [string]$EndpointCell, $Participant, $ConnectionInfo, [string]$EndpointName) {
    if ([string]::IsNullOrWhiteSpace([string]$ConnectionInfo.CellName)) {
      throw "Cannot glue $EndpointName endpoint for participant '$([string]$Participant.id)': missing lifeline connection cell."
    }
    try {
      $Shape.CellsU($EndpointCell).GlueTo($Participant.shape.CellsU([string]$ConnectionInfo.CellName))
    }
    catch {
      throw "Cannot glue $EndpointName endpoint for participant '$([string]$Participant.id)' to $([string]$ConnectionInfo.CellName): $($_.Exception.Message)"
    }
  }

  if ($kind -eq 'self') {
    $x = [double]$Participants[$from].x
    $selfHeight = Get-NativeConnectionPointUnit
    $selfWidth = 0.52
    if ($Msg.width) { $selfWidth = [double]$Msg.width }
    $beginConn = Get-ConnectionInfo $Participants[$from] $top
    $endConn = Get-ConnectionInfo $Participants[$from] ($top + $selfHeight)
    $master = Get-Master $Doc @('Self Message', 'Self Message.48')
    $shape = $Page.Drop($master, 0, 0)
    $shape.CellsU('BeginX').FormulaU = ("{0} in" -f $x)
    $shape.CellsU('BeginY').FormulaU = ("{0} in" -f (Convert-Y ([double]$beginConn.Top)))
    $shape.CellsU('EndX').FormulaU = ("{0} in" -f $x)
    $shape.CellsU('EndY').FormulaU = ("{0} in" -f (Convert-Y ([double]$endConn.Top)))
    Set-CellFormulaForce $shape 'Width' ("{0} in" -f $selfWidth)
    Glue-MessageEndpoint $shape 'BeginX' $Participants[$from] $beginConn 'self-begin'
    Glue-MessageEndpoint $shape 'EndX' $Participants[$from] $endConn 'self-end'
  }
  elseif ($kind -eq 'return') {
    $master = if ($dashed) { Get-Master $Doc @('Return Message', 'Return Message.44') } else { Get-Master $Doc @('Message', 'Message.41') }
    $x1 = [double]$Participants[$from].x
    $x2 = [double]$Participants[$to].x
    $beginConn = Get-ConnectionInfo $Participants[$from] $top
    $endConn = Get-ConnectionInfo $Participants[$to] $top
    $shape = $Page.Drop($master, 0, 0)
    $shape.CellsU('BeginX').FormulaU = ("{0} in" -f $x1)
    $shape.CellsU('BeginY').FormulaU = ("{0} in" -f (Convert-Y ([double]$beginConn.Top)))
    $shape.CellsU('EndX').FormulaU = ("{0} in" -f $x2)
    $shape.CellsU('EndY').FormulaU = ("{0} in" -f (Convert-Y ([double]$endConn.Top)))
    Glue-MessageEndpoint $shape 'BeginX' $Participants[$from] $beginConn 'return-begin'
    Glue-MessageEndpoint $shape 'EndX' $Participants[$to] $endConn 'return-end'
  }
  else {
    $master = Get-Master $Doc @('Message', 'Message.41')
    $x1 = [double]$Participants[$from].x
    $x2 = [double]$Participants[$to].x
    $beginConn = Get-ConnectionInfo $Participants[$from] $top
    $endConn = Get-ConnectionInfo $Participants[$to] $top
    $shape = $Page.Drop($master, 0, 0)
    $shape.CellsU('BeginX').FormulaU = ("{0} in" -f $x1)
    $shape.CellsU('BeginY').FormulaU = ("{0} in" -f (Convert-Y ([double]$beginConn.Top)))
    $shape.CellsU('EndX').FormulaU = ("{0} in" -f $x2)
    $shape.CellsU('EndY').FormulaU = ("{0} in" -f (Convert-Y ([double]$endConn.Top)))
    Glue-MessageEndpoint $shape 'BeginX' $Participants[$from] $beginConn 'message-begin'
    Glue-MessageEndpoint $shape 'EndX' $Participants[$to] $endConn 'message-end'
  }

  if ($kind -eq 'self') {
    Set-NativeShapeText $shape $text
    Set-SelfMessageTextBlock $shape $Msg $selfWidth
  }
  else {
    Set-NativeShapeText $shape $text
    Set-ParticipantMessageTextBlock $shape $Msg
  }

  $lineColor = Get-MessageStyleValue $Msg 'lineColor' ''
  $textColor = Get-MessageStyleValue $Msg 'textColor' ''
  $messagePolicyForTheme = Get-MessageStyleValue $Msg 'policy' ''
  $useThemeMessageStyle = ($messagePolicyForTheme -match '(?i)^e001-reference$')
  if (($red -or (Test-ProjectRedMessagePolicy $Msg)) -and -not $useThemeMessageStyle) {
    if ([string]::IsNullOrWhiteSpace($lineColor)) { $lineColor = 'RGB(176,21,19)' }
    if ([string]::IsNullOrWhiteSpace($textColor)) { $textColor = 'RGB(176,21,19)' }
  }
  if ([string]::IsNullOrWhiteSpace($textColor)) {
    $textColor = 'RGB(0,0,0)'
  }

  $dashOverride = $null
  $hasDashProperty = $false
  try { $hasDashProperty = ($null -ne $Msg.PSObject.Properties['dashed']) } catch { }
  if ($hasDashProperty -and (-not [string]::IsNullOrWhiteSpace($lineColor))) {
    $dashOverride = [bool]$dashed
  }
  if (-not [string]::IsNullOrWhiteSpace($lineColor)) {
    Set-MessageLineColorRecursive $shape $lineColor $dashOverride
  }
  if (-not [string]::IsNullOrWhiteSpace($textColor)) {
    Set-NativeShapeTextColor $shape $textColor
  }

  Bring-ToFront $shape
  return $shape
}

$specFull = Resolve-FullPath $SpecPath
$templateFull = Resolve-FullPath $TemplateVsdx
$outputFull = Resolve-FullPath $OutputVsdx
$previewFull = $null
if (-not [string]::IsNullOrWhiteSpace($PreviewPng)) {
  $previewFull = Resolve-FullPath $PreviewPng
}
if ([string]::IsNullOrWhiteSpace($ShapeLibraryDir)) {
  $projectShapeLibrary = Resolve-ProjectRulesAsset 'nativeShapeLibrary' $RulesRoot
  if (-not [string]::IsNullOrWhiteSpace($projectShapeLibrary)) {
    $shapeLibraryFull = $projectShapeLibrary
  }
  else {
    $shapeLibraryFull = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\references\native-shape-library'))
  }
}
elseif (Test-Path -LiteralPath $ShapeLibraryDir) {
  $shapeLibraryFull = Resolve-FullPath $ShapeLibraryDir
}
else {
  $shapeLibraryFull = $ShapeLibraryDir
}

$projectThemeTemplate = Resolve-ProjectRulesAsset 'nativeVsdxTemplate' $RulesRoot
if (-not (Test-VsdxHasProjectTheme $templateFull)) {
  if (-not [string]::IsNullOrWhiteSpace($projectThemeTemplate) -and (Test-VsdxHasProjectTheme $projectThemeTemplate)) {
    Write-Output "template VSDX is missing project theme; using project-rules native VSDX template: $projectThemeTemplate"
    $templateFull = $projectThemeTemplate
  }
  else {
    throw "Template VSDX is missing project theme and project-rules native VSDX template is unavailable or invalid: $templateFull"
  }
}

Load-NativeShapeTemplates $shapeLibraryFull

$effectiveSpecFull = $specFull
$layoutPlannerTempFull = $null
$layoutPlanner = Join-Path $PSScriptRoot 'normalize_native_visio_spec_layout.js'
if (Test-Path -LiteralPath $layoutPlanner) {
  $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
  if ($null -eq $nodeCommand) {
    throw "Native VSDX layout planner requires node.exe, but it was not found in PATH. Planner: $layoutPlanner"
  }
  $layoutPlannerTempFull = [System.IO.Path]::ChangeExtension([System.IO.Path]::GetTempFileName(), '.json')
  Write-NativeBuildStage 'layout-planner-start'
  & $nodeCommand.Source $layoutPlanner --input $specFull --output $layoutPlannerTempFull
  Write-NativeBuildStage 'layout-planner-done'
  if ($LASTEXITCODE -ne 0) {
    throw "Native VSDX layout planner failed with exit code $LASTEXITCODE"
  }
  $effectiveSpecFull = $layoutPlannerTempFull
}

$spec = Get-Content -Raw -Encoding UTF8 -LiteralPath $effectiveSpecFull | ConvertFrom-Json
$script:MessageStyleSpec = Get-ObjectPropertyValue $spec 'messageStyle' $null
$messagePolicy = Get-ObjectPropertyValue $script:MessageStyleSpec 'policy' ''
if ([string]::IsNullOrWhiteSpace([string]$messagePolicy)) {
  throw 'Native spec must declare messageStyle.policy. Use e001-reference, project-red, or preserve-native.'
}
$allowedMessagePolicies = @('e001-reference', 'project-red', 'preserve-native')
if ($allowedMessagePolicies -notcontains ([string]$messagePolicy)) {
  throw "Unsupported messageStyle.policy '$messagePolicy'. Allowed values: $($allowedMessagePolicies -join ', ')"
}
function New-LegacyNativeSpecPageBundle($Spec) {
  return [pscustomobject]@{
    page = $Spec.page
    participants = $Spec.participants
    sections = $Spec.sections
    frames = $Spec.frames
    separators = $Spec.separators
    messages = $Spec.messages
    texts = $Spec.texts
    orangePointers = $Spec.orangePointers
    refCommonSvgBlocks = $Spec.refCommonSvgBlocks
  }
}

function Get-NativeSpecPageBundles($Spec) {
  $pagesValue = Get-ObjectPropertyValue $Spec 'pages' $null
  $pages = @()
  foreach ($pageValue in @($pagesValue)) {
    if ($null -ne $pageValue) { $pages += $pageValue }
  }
  if ($pages.Count -gt 0) { return $pages }
  return @(New-LegacyNativeSpecPageBundle $Spec)
}

$pageBundles = @(Get-NativeSpecPageBundles $spec)
if ($pageBundles.Count -le 0) {
  throw 'Native spec must contain either a legacy page or pages[].'
}
$firstPageSpec = Get-ObjectPropertyValue $pageBundles[0] 'page' $null
if ($null -eq $firstPageSpec) {
  throw 'Native spec page bundle is missing page metadata.'
}
$script:PageHeight = [double]$firstPageSpec.height
function Convert-Y([double]$Top) { $script:PageHeight - $Top }

function Get-NativeSpecArray($Object, [string]$Name) {
  $value = Get-ObjectPropertyValue $Object $Name @()
  if ($null -eq $value) { return @() }
  return @($value)
}

function Assert-NoUserTargetMessages($PageBundles) {
  foreach ($pageBundle in @($PageBundles)) {
    $pageSpec = Get-ObjectPropertyValue $pageBundle 'page' $null
    $pageName = if ($null -ne $pageSpec) { [string]$pageSpec.name } else { '<unknown>' }
    foreach ($msg in (Get-NativeSpecArray $pageBundle 'messages')) {
      $target = [string](Get-ObjectPropertyValue $msg 'to' '')
      if ([string]::IsNullOrWhiteSpace($target)) {
        $target = [string](Get-ObjectPropertyValue $msg 'target' '')
      }
      if ($target -eq 'User') {
        $text = [string](Get-ObjectPropertyValue $msg 'text' '')
        throw "Native spec page '$pageName' contains a message targeting User: '$text'. User may only trigger APP actions; represent UI response as an APP self message."
      }
    }
  }
}

Assert-NoUserTargetMessages $pageBundles

function Render-NativeSpecPage($Page, $Doc, $PageBundle) {
  $pageSpec = Get-ObjectPropertyValue $PageBundle 'page' $null
  if ($null -eq $pageSpec) {
    throw 'Native spec page bundle is missing page metadata.'
  }
  $participantsSpec = @(Get-NativeSpecArray $PageBundle 'participants')
  if ($participantsSpec.Count -le 0) {
    throw "Native spec page '$([string]$pageSpec.name)' has no participants."
  }

  $script:PageHeight = [double]$pageSpec.height
  try { $Page.Name = [string]$pageSpec.name } catch { }
  $Page.PageSheet.CellsU('PageWidth').FormulaU = ("{0} in" -f ([double]$pageSpec.width))
  $Page.PageSheet.CellsU('PageHeight').FormulaU = ("{0} in" -f ([double]$pageSpec.height))
  Disable-PageAutoResize $Page

  $script:TemplateParticipantShapes = @{}
  $templateParticipantShapeIds = @{}
  $templatePageTitleShape = Find-TemplatePageTitleShape $Page $pageSpec
  if ($null -ne $templatePageTitleShape) {
    try { $templateParticipantShapeIds[[int]$templatePageTitleShape.ID] = $true } catch { }
  }
  foreach ($p in $participantsSpec) {
    $templateShape = Find-TemplateParticipantShape $Page $p
    if ($null -ne $templateShape) {
      $script:TemplateParticipantShapes[[string]$p.id] = $templateShape
      try { $templateParticipantShapeIds[[int]$templateShape.ID] = $true } catch { }
    }
  }

  foreach ($shape in @($Page.Shapes)) {
    try {
      if ($templateParticipantShapeIds.ContainsKey([int]$shape.ID)) { continue }
    } catch { }
    $shape.Delete() | Out-Null
  }

  $participants = @{}
  foreach ($p in $participantsSpec) {
    $participants[[string]$p.id] = Add-NativeParticipant $Page $Doc $p
  }
  Write-NativeBuildStage ("participants-added page={0}" -f ([string]$pageSpec.name))
  # Visio UML lifeline masters use 6 mm native connection-point intervals. Keep
  # the page on that measured native unit instead of visual-only or ad hoc rows.
  Set-NativeConnectionPointUnit (6.0 / 25.4)
  Normalize-PageParticipantConnectionRows $participants
  Set-NativeConnectionPointUnit (6.0 / 25.4)
  Write-NativeBuildStage ("connection-unit page={0} unit={1:N4}" -f ([string]$pageSpec.name), (Get-NativeConnectionPointUnit))

  Add-PageTitle $Page $pageSpec $templatePageTitleShape | Out-Null
  foreach ($section in (Get-NativeSpecArray $PageBundle 'sections')) { Add-Section $Page $section }
  $frameShapeRecords = @()
  foreach ($frame in (Get-NativeSpecArray $PageBundle 'frames')) {
    Write-NativeBuildStage ("frame-start page={0} kind={1} top={2}" -f ([string]$pageSpec.name), ([string]$frame.kind), ([string]$frame.top))
    $frameShape = Add-Frame $Page $Doc $frame
    if ($null -ne $frameShape) {
      $frameShapeRecords += [pscustomobject]@{
        Shape = $frameShape
        Spec = $frame
      }
    }
    Write-NativeBuildStage ("frame-done page={0} kind={1} top={2}" -f ([string]$pageSpec.name), ([string]$frame.kind), ([string]$frame.top))
  }
  Write-NativeBuildStage ("frames-added page={0}" -f ([string]$pageSpec.name))
  Write-NativeBuildStage ("separators-start page={0}" -f ([string]$pageSpec.name))
  foreach ($sep in (Get-NativeSpecArray $PageBundle 'separators')) { Add-Separator $Page $Doc $sep | Out-Null }
  Write-NativeBuildStage ("separators-done page={0}" -f ([string]$pageSpec.name))
  foreach ($text in (Get-NativeSpecArray $PageBundle 'texts')) {
    if ($text.template) {
      Add-TextFromTemplate $Page $text | Out-Null
    }
    elseif ($text.fill -or $text.border) {
      $fill = if ($text.fill) { [string]$text.fill } else { 'RGB(255,255,255)' }
      $border = if ($text.border) { [string]$text.border } else { 'RGB(30,80,84)' }
      Add-TextWithBox $Page ([double]$text.left) ([double]$text.top) ([double]$text.width) ([double]$text.height) ([string]$text.text) ([string]$text.color) ([double]$text.size) ([string]$text.align) $fill $border | Out-Null
    }
    else {
      Add-Text $Page ([double]$text.left) ([double]$text.top) ([double]$text.width) ([double]$text.height) ([string]$text.text) ([string]$text.color) ([double]$text.size) ([string]$text.align) | Out-Null
    }
  }
  foreach ($pointer in (Get-NativeSpecArray $PageBundle 'orangePointers')) { Add-OrangePointer $Page $pointer | Out-Null }
  foreach ($block in (Get-NativeSpecArray $PageBundle 'refCommonSvgBlocks')) {
    if ($null -ne $block) { Add-RefCommonSvgBlock $Page $block | Out-Null }
  }
  $messageShapes = @()
  $allMessages = @(Get-NativeSpecArray $PageBundle 'messages')
  $refMessages = @($allMessages | Where-Object { ([string](Get-ObjectPropertyValue $_ 'layoutRole' '')) -eq 'ref-self' })
  $regularMessages = @($allMessages | Where-Object { ([string](Get-ObjectPropertyValue $_ 'layoutRole' '')) -ne 'ref-self' })
  foreach ($msg in $refMessages) {
    $messageShape = Add-Message $Page $Doc $participants $msg
    if ($null -ne $messageShape) { $messageShapes += $messageShape }
  }
  Write-NativeBuildStage ("ref-messages-added page={0}" -f ([string]$pageSpec.name))
  foreach ($msg in $regularMessages) {
    $messageShape = Add-Message $Page $Doc $participants $msg
    if ($null -ne $messageShape) { $messageShapes += $messageShape }
  }
  Write-NativeBuildStage ("messages-added page={0}" -f ([string]$pageSpec.name))
  Remove-PlaceholderInteractionOperands $Page
  foreach ($shape in @($Page.Shapes)) {
    Clear-PlaceholderTextRecursive $shape
    Hide-DashedHorizontalLinesRecursive $shape
  }

  Write-NativeBuildStage ("normalize-alt-operands-start page={0}" -f ([string]$pageSpec.name))
  Normalize-NativeAltOperandRegions $Page
  Write-NativeBuildStage ("normalize-alt-operands-done page={0}" -f ([string]$pageSpec.name))
  Write-NativeBuildStage ("bind-opt-operands-start page={0}" -f ([string]$pageSpec.name))
  Bind-NativeOptOperandRegions $Page
  Write-NativeBuildStage ("bind-opt-operands-done page={0}" -f ([string]$pageSpec.name))
  Write-NativeBuildStage ("normalize-alt-operands-after-opt-start page={0}" -f ([string]$pageSpec.name))
  Normalize-NativeAltOperandRegions $Page
  Write-NativeBuildStage ("normalize-alt-operands-after-opt-done page={0}" -f ([string]$pageSpec.name))
  Write-NativeBuildStage ("restore-group-frames-start page={0}" -f ([string]$pageSpec.name))
  Restore-NativeBusinessGroupFramesFromSpec $frameShapeRecords
  Write-NativeBuildStage ("restore-group-frames-done page={0}" -f ([string]$pageSpec.name))
  Write-NativeBuildStage ("fragment-membership-start page={0}" -f ([string]$pageSpec.name))
  Add-NativeFragmentMemberships $Page
  Write-NativeBuildStage ("fragment-membership-done page={0}" -f ([string]$pageSpec.name))
  Write-NativeBuildStage ("normalize-alt-operands-after-membership-start page={0}" -f ([string]$pageSpec.name))
  Normalize-NativeAltOperandRegions $Page
  Write-NativeBuildStage ("normalize-alt-operands-after-membership-done page={0}" -f ([string]$pageSpec.name))
  Write-NativeBuildStage ("restore-group-frames-after-membership-start page={0}" -f ([string]$pageSpec.name))
  Restore-NativeBusinessGroupFramesFromSpec $frameShapeRecords
  Write-NativeBuildStage ("restore-group-frames-after-membership-done page={0}" -f ([string]$pageSpec.name))
  Remove-PlaceholderInteractionOperands $Page
  Write-NativeBuildStage ("visual-separators-front-start page={0}" -f ([string]$pageSpec.name))
  $visualSeparatorsRaised = Bring-VisualSeparatorsToFront $Page
  Write-NativeBuildStage ("visual-separators-front-done page={0} count={1}" -f ([string]$pageSpec.name), $visualSeparatorsRaised)

  return [pscustomobject]@{
    Name = [string]$pageSpec.name
    Shapes = $Page.Shapes.Count
    Connects = $Page.Connects.Count
  }
}

$outDir = Split-Path -Parent $outputFull
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
if ($previewFull -ne $null) {
  $previewDir = Split-Path -Parent $previewFull
  New-Item -ItemType Directory -Force -Path $previewDir | Out-Null
}

if ((Test-Path -LiteralPath $outputFull) -and -not $NoBackup) {
  $backup = $outputFull + '.bak'
  Remove-Item -LiteralPath $backup -Force -ErrorAction SilentlyContinue
  Copy-Item -LiteralPath $outputFull -Destination $backup -Force
}

try {
  Copy-Item -LiteralPath $templateFull -Destination $outputFull -Force
  Set-ItemProperty -LiteralPath $outputFull -Name IsReadOnly -Value $false -ErrorAction SilentlyContinue
}
catch {
  if (-not (Test-Path -LiteralPath $outputFull)) {
    throw
  }
  Write-Output "template is locked; reusing existing output VSDX as native master source: $outputFull"
}

$visio = $null
$doc = $null
try {
  Write-NativeBuildStage 'create-visio-application'
  $visio = New-Object -ComObject Visio.Application
  $visio.Visible = $false
  $visio.AlertResponse = 7
  Write-NativeBuildStage 'open-output-template'
  $doc = $visio.Documents.Open($outputFull)
  while ($doc.Pages.Count -gt $pageBundles.Count) {
    $doc.Pages.Item($doc.Pages.Count).Delete() | Out-Null
  }

  $pageRenderReports = @()
  for ($pageIndex = 0; $pageIndex -lt $pageBundles.Count; $pageIndex++) {
    if ($pageIndex -eq 0) {
      $page = $doc.Pages.Item(1)
    }
    else {
      $page = $doc.Pages.Add()
    }
    Write-NativeBuildStage ("render-page-start index={0}" -f ($pageIndex + 1))
    $pageRenderReports += Render-NativeSpecPage $page $doc $pageBundles[$pageIndex]
    Write-NativeBuildStage ("render-page-done index={0}" -f ($pageIndex + 1))
  }
  Write-NativeBuildStage 'save-start'
  $doc.SaveAs($outputFull) | Out-Null
  Write-NativeBuildStage 'save-done'
  # Native Alternative fragment masters materialize default operand placeholders after the document is persisted.
  # Finalize in a fresh PowerShell/Visio process, then hide those filler operands from the clean file.
  $shapeCountOut = 0
  $connectCountOut = 0
  foreach ($report in $pageRenderReports) {
    $shapeCountOut += [int]$report.Shapes
    $connectCountOut += [int]$report.Connects
  }
  $masterCountOut = $doc.Masters.Count
  $doc.Close()
  $doc = $null
  $visio.Quit()
  $visio = $null

  $finalizer = Join-Path $PSScriptRoot 'finalize_native_visio_fragments.ps1'
  $powershellExe = Join-Path $PSHOME 'powershell.exe'
  if (-not (Test-Path $powershellExe)) { $powershellExe = 'powershell' }
  Write-NativeBuildStage 'finalizer-start'
  if ($previewFull -ne $null) {
    & $powershellExe -NoProfile -ExecutionPolicy Bypass -File $finalizer -VsdxPath $outputFull -PreviewPng $previewFull -SpecPath $effectiveSpecFull
  }
  else {
    & $powershellExe -NoProfile -ExecutionPolicy Bypass -File $finalizer -VsdxPath $outputFull -SpecPath $effectiveSpecFull
  }
  Write-NativeBuildStage 'finalizer-done'
  if ($LASTEXITCODE -ne 0) {
    throw "Native fragment finalizer failed with exit code $LASTEXITCODE"
  }

  $validator = Join-Path $PSScriptRoot 'validate_native_visio_output.ps1'
  if (-not (Test-Path -LiteralPath $validator)) {
    throw "Native VSDX validator is missing: $validator"
  }
  Write-NativeBuildStage 'validator-start'
  & $powershellExe -NoProfile -ExecutionPolicy Bypass -File $validator -VsdxPath $outputFull
  Write-NativeBuildStage 'validator-done'
  if ($LASTEXITCODE -ne 0) {
    throw "Native VSDX validation failed with exit code $LASTEXITCODE"
  }

  Write-Output "native-shape-library: $script:NativeShapeTemplateStatus"
  Write-Output "native-visio VSDX saved: $outputFull"
  if ($previewFull -ne $null) {
    Write-Output "preview PNG saved: $previewFull"
  }
  else {
    Write-Output "preview PNG skipped"
  }
  Write-Output "shapes=$shapeCountOut connects=$connectCountOut masters=$masterCountOut"
}
finally {
  if ($doc -ne $null) { $doc.Close() }
  if ($visio -ne $null) { $visio.Quit() }
  if (-not [string]::IsNullOrWhiteSpace($layoutPlannerTempFull)) {
    Remove-Item -LiteralPath $layoutPlannerTempFull -Force -ErrorAction SilentlyContinue
  }
}
