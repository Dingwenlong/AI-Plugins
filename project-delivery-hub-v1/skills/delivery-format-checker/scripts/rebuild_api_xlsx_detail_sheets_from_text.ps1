param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string[]]$Sheets,

  [string]$ConfigPath,

  [string]$RulesRoot,

  [switch]$Visible,

  [switch]$CreateBackup,

  [switch]$ForceRebuild
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectExcelConfigPath {
  param([string]$ExplicitRulesRoot)
  $root = $ExplicitRulesRoot
  if ([string]::IsNullOrWhiteSpace($root)) { $root = $env:PROJECT_RULES_ROOT }
  if ([string]::IsNullOrWhiteSpace($root)) {
    $pluginRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
    $configPath = Join-Path $pluginRoot 'references\local-workspaces.json'
    if (Test-Path -LiteralPath $configPath) {
      $config = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
      $workspaceKey = if ($env:PROJECT_WORKSPACE_KEY) { $env:PROJECT_WORKSPACE_KEY } else { $config.defaultWorkspace }
      if ($workspaceKey -and $config.workspaces.$workspaceKey) {
        $root = $config.workspaces.$workspaceKey.rulesRoot
      }
    }
  }
  if ([string]::IsNullOrWhiteSpace($root)) { return '' }
  $catalogPath = Join-Path $root 'catalog.json'
  if (-not (Test-Path -LiteralPath $catalogPath)) { return '' }
  $catalog = Get-Content -LiteralPath $catalogPath -Raw -Encoding UTF8 | ConvertFrom-Json
  $relative = $catalog.assets.apiDetailExcelStyle
  if ([string]::IsNullOrWhiteSpace($relative)) { return '' }
  $candidate = [System.IO.Path]::GetFullPath((Join-Path $root $relative))
  if (Test-Path -LiteralPath $candidate) { return $candidate }
  return ''
}

if (-not $ConfigPath) {
  $ConfigPath = Resolve-ProjectExcelConfigPath $RulesRoot
  if (-not $ConfigPath) {
    throw "Project API Detail Excel style config not found. Provide -RulesRoot with catalog asset apiDetailExcelStyle or pass -ConfigPath explicitly."
  }
}

$xlEdgeLeft = 7
$xlEdgeTop = 8
$xlEdgeBottom = 9
$xlEdgeRight = 10
$xlInsideVertical = 11
$xlInsideHorizontal = 12
$xlContinuous = 1
$xlThin = 2
$xlLineStyleNone = -4142
$xlPatternNone = -4142
$xlSolid = 1
$xlLeft = -4131
$xlCenter = -4108
$xlTop = -4160
$xlUnderlineStyleSingle = 2

$VisibleColumnLimit = 7
$OutsideColumnEnd = 52

$ExampleSectionLabel = [string]::Concat([char]0x7BC4, [char]0x4F8B)
$MiddleOfficeSectionLabel = "For" + [string]::Concat([char]0x4E2D, [char]0x53F0, [char]0x958B, [char]0x767C, [char]0x4EBA, [char]0x54E1)
$InternalLogicSectionLabel = "API " + [string]::Concat([char]0x5167, [char]0x90E8, [char]0x696D, [char]0x52D9, [char]0x908F, [char]0x8F2F)
$ReturnLinkText = [string]::Concat([char]0x8FD4, [char]0x56DE) + "API_List"

function Convert-RgbToComColor {
  param([Parameter(Mandatory = $true)][string]$Rgb)

  $value = $Rgb
  if ($value.Length -eq 8) {
    $value = $value.Substring(2)
  }
  if ($value.Length -ne 6) {
    throw "Invalid RGB value: $Rgb"
  }

  $r = [Convert]::ToInt32($value.Substring(0, 2), 16)
  $g = [Convert]::ToInt32($value.Substring(2, 2), 16)
  $b = [Convert]::ToInt32($value.Substring(4, 2), 16)
  return ($r -bor ($g -shl 8) -bor ($b -shl 16))
}

function Normalize-Text {
  param([object]$Value)
  if ($null -eq $Value) {
    return ""
  }
  return ([string]$Value).Trim() -replace "\s+", ""
}

function Get-CellString {
  param([Parameter(Mandatory = $true)]$Cell)

  $value = $Cell.Value2
  if ($null -ne $value) {
    $valueText = [string]$value
    if ($valueText.Length -gt 0) {
      return $valueText
    }
  }

  try {
    $displayText = [string]$Cell.Text
    if ($displayText.Trim().Length -gt 0) {
      return $displayText
    }
  } catch {
  }

  return ""
}

function Test-RowHasText {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [int]$MaxColumn = 7
  )

  for ($col = 1; $col -le $MaxColumn; $col++) {
    if ((Get-CellString $Worksheet.Cells.Item($Row, $col)).Trim().Length -gt 0) {
      return $true
    }
  }
  return $false
}

function Get-RowValues {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  $values = @()
  for ($col = 1; $col -le $MaxColumn; $col++) {
    $values += (Get-CellString $Worksheet.Cells.Item($Row, $col))
  }
  return $values
}

function Join-Cells {
  param(
    [Parameter(Mandatory = $true)][object[]]$Values,
    [Parameter(Mandatory = $true)][int]$StartIndex,
    [Parameter(Mandatory = $true)][int]$EndIndex
  )

  $parts = @()
  for ($i = $StartIndex; $i -le $EndIndex; $i++) {
    $text = [string]$Values[$i]
    if ($text.Trim().Length -gt 0) {
      $parts += $text.Trim()
    }
  }
  return ($parts -join "`r`n")
}

function Test-ApiListSheet {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $name = [string]$Worksheet.Name
  if ($name -match '^(Api_List|API_List|API List)$') {
    return $true
  }

  $a1 = Normalize-Text $Worksheet.Range("A1").Text
  $e1 = Normalize-Text $Worksheet.Range("E1").Text
  return ($a1 -match "PRD" -and $e1 -match "API")
}

function Test-ApiDetailSheet {
  param([Parameter(Mandatory = $true)]$Worksheet)

  if (Test-ApiListSheet -Worksheet $Worksheet) {
    return $false
  }

  if ((Normalize-Text $Worksheet.Range("A1").Text) -match "^APIName$") {
    return $true
  }

  $labels = @("Request", "Response", $ExampleSectionLabel, $InternalLogicSectionLabel)
  $found = 0
  $maxRows = [Math]::Min(140, [Math]::Max(1, $Worksheet.UsedRange.Rows.Count + $Worksheet.UsedRange.Row - 1))
  for ($row = 1; $row -le $maxRows; $row++) {
    for ($col = 1; $col -le $VisibleColumnLimit; $col++) {
      if ($labels -contains (Normalize-Text $Worksheet.Cells.Item($row, $col).Text)) {
        $found++
      }
    }
  }
  return ($found -ge 2)
}

function Get-LastTextRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  $used = $Worksheet.UsedRange
  $lastUsedRow = $used.Row + $used.Rows.Count - 1
  for ($row = $lastUsedRow; $row -ge 1; $row--) {
    if (Test-RowHasText -Worksheet $Worksheet -Row $row -MaxColumn $MaxColumn) {
      return $row
    }
  }
  return 0
}

function Find-SectionRows {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $sectionRows = @{}
  $labels = @("Header", "Request", "Response", $ExampleSectionLabel, $MiddleOfficeSectionLabel, $InternalLogicSectionLabel)
  $lastRow = Get-LastTextRow -Worksheet $Worksheet -MaxColumn $VisibleColumnLimit
  for ($row = 1; $row -le $lastRow; $row++) {
    $text = Normalize-Text $Worksheet.Cells.Item($row, 1).Text
    foreach ($label in $labels) {
      if ($text -eq (Normalize-Text $label) -and -not $sectionRows.ContainsKey($label)) {
        $sectionRows[$label] = $row
      }
    }
  }
  return $sectionRows
}

function Get-NextSectionRow {
  param(
    [Parameter(Mandatory = $true)][hashtable]$SectionRows,
    [Parameter(Mandatory = $true)][int]$CurrentRow,
    [Parameter(Mandatory = $true)][int]$LastRow
  )

  $next = $LastRow + 1
  foreach ($row in $SectionRows.Values) {
    $value = [int]$row
    if ($value -gt $CurrentRow -and $value -lt $next) {
      $next = $value
    }
  }
  return $next
}

function Test-UnsafeSheetContent {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$LastRow,
    [Parameter(Mandatory = $true)][int]$LastColumn
  )

  $issues = New-Object System.Collections.Generic.List[string]

  if ($Worksheet.Shapes.Count -gt 0) {
    $issues.Add(("Shapes or embedded objects on sheet: {0}" -f $Worksheet.Shapes.Count))
  }

  for ($row = 1; $row -le $LastRow; $row++) {
    for ($col = 1; $col -le $LastColumn; $col++) {
      $cell = $Worksheet.Cells.Item($row, $col)
      if ([bool]$cell.HasFormula) {
        $issues.Add(("Formula at {0}" -f $cell.Address($false, $false)))
      }
      if ($cell.Hyperlinks.Count -gt 0) {
        $link = $cell.Hyperlinks.Item(1)
        if (([string]$link.Address).Length -gt 0) {
          $issues.Add(("External hyperlink at {0}" -f $cell.Address($false, $false)))
        }
      }
      try {
        if ($null -ne $cell.Comment) {
          $issues.Add(("Comment at {0}" -f $cell.Address($false, $false)))
        }
      } catch {
      }
    }
  }

  return $issues
}

function New-RowObject {
  param([object[]]$Values)
  return [PSCustomObject]@{ Values = @($Values) }
}

function Extract-StandardRows {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$StartRow,
    [Parameter(Mandatory = $true)][int]$EndRow,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  $rows = New-Object System.Collections.Generic.List[object]
  for ($row = $StartRow; $row -le $EndRow; $row++) {
    if (Test-RowHasText -Worksheet $Worksheet -Row $row -MaxColumn $MaxColumn) {
      $rows.Add((New-RowObject -Values (Get-RowValues -Worksheet $Worksheet -Row $row -MaxColumn $MaxColumn)))
    }
  }
  return $rows
}

function Extract-ExampleRows {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$StartRow,
    [Parameter(Mandatory = $true)][int]$EndRow
  )

  $rows = New-Object System.Collections.Generic.List[object]
  for ($row = $StartRow; $row -le $EndRow; $row++) {
    if (-not (Test-RowHasText -Worksheet $Worksheet -Row $row -MaxColumn 6)) {
      continue
    }
    $values = Get-RowValues -Worksheet $Worksheet -Row $row -MaxColumn 6
    $normalized = @($values[0], (Join-Cells -Values $values -StartIndex 1 -EndIndex 2), "", (Join-Cells -Values $values -StartIndex 3 -EndIndex 5), "", "")
    $rows.Add((New-RowObject -Values $normalized))
  }
  return $rows
}

function Extract-InternalLogicRows {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$StartRow,
    [Parameter(Mandatory = $true)][int]$EndRow
  )

  $logicRows = New-Object System.Collections.Generic.List[object]
  $tailRows = New-Object System.Collections.Generic.List[object]
  $inTail = $false

  for ($row = $StartRow; $row -le $EndRow; $row++) {
    $hasLogicText = Test-RowHasText -Worksheet $Worksheet -Row $row -MaxColumn 6
    if (-not $hasLogicText) {
      if ($logicRows.Count -gt 0) {
        $inTail = $true
      }
      continue
    }

    if ($inTail) {
      $tailRows.Add((New-RowObject -Values (Get-RowValues -Worksheet $Worksheet -Row $row -MaxColumn 7)))
      continue
    }

    $values = Get-RowValues -Worksheet $Worksheet -Row $row -MaxColumn 6
    $normalized = @($values[0], (Join-Cells -Values $values -StartIndex 1 -EndIndex 5), "", "", "", "")
    $logicRows.Add((New-RowObject -Values $normalized))
  }

  return [PSCustomObject]@{
    LogicRows = $logicRows
    TailRows = $tailRows
  }
}

function Extract-ApiDetailSheet {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $lastRow = Get-LastTextRow -Worksheet $Worksheet -MaxColumn $VisibleColumnLimit
  $sectionRows = Find-SectionRows -Worksheet $Worksheet

  if (-not $sectionRows.ContainsKey("Request") -or -not $sectionRows.ContainsKey("Response")) {
    throw ("Cannot safely identify Request/Response sections on sheet {0}." -f $Worksheet.Name)
  }

  $result = [PSCustomObject]@{
    Name = [string]$Worksheet.Name
    Index = [int]$Worksheet.Index
    ApiName = Get-CellString $Worksheet.Range("A2")
    ApiDescription = Get-CellString $Worksheet.Range("B2")
    LastRow = $lastRow
    Sections = @{}
    TailRows = (New-Object System.Collections.Generic.List[object])
  }

  foreach ($label in @("Header", "Request", "Response")) {
    if (-not $sectionRows.ContainsKey($label)) {
      continue
    }
    $titleRow = [int]$sectionRows[$label]
    $nextRow = Get-NextSectionRow -SectionRows $sectionRows -CurrentRow $titleRow -LastRow $lastRow
    $headerValues = Get-RowValues -Worksheet $Worksheet -Row ($titleRow + 1) -MaxColumn 7
    $dataRows = Extract-StandardRows -Worksheet $Worksheet -StartRow ($titleRow + 2) -EndRow ($nextRow - 1) -MaxColumn 7
    $result.Sections[$label] = [PSCustomObject]@{
      HeaderValues = $headerValues
      Rows = $dataRows
    }
  }

  if ($sectionRows.ContainsKey($ExampleSectionLabel)) {
    $titleRow = [int]$sectionRows[$ExampleSectionLabel]
    $nextRow = Get-NextSectionRow -SectionRows $sectionRows -CurrentRow $titleRow -LastRow $lastRow
    $headerValues = Get-RowValues -Worksheet $Worksheet -Row ($titleRow + 1) -MaxColumn 6
    $rows = Extract-ExampleRows -Worksheet $Worksheet -StartRow ($titleRow + 2) -EndRow ($nextRow - 1)
    $result.Sections[$ExampleSectionLabel] = [PSCustomObject]@{
      HeaderValues = $headerValues
      Rows = $rows
    }
  }

  if ($sectionRows.ContainsKey($MiddleOfficeSectionLabel)) {
    $result.Sections[$MiddleOfficeSectionLabel] = [PSCustomObject]@{
      HeaderValues = @()
      Rows = (New-Object System.Collections.Generic.List[object])
    }
  }

  if ($sectionRows.ContainsKey($InternalLogicSectionLabel)) {
    $titleRow = [int]$sectionRows[$InternalLogicSectionLabel]
    $nextRow = Get-NextSectionRow -SectionRows $sectionRows -CurrentRow $titleRow -LastRow $lastRow
    $headerValues = Get-RowValues -Worksheet $Worksheet -Row ($titleRow + 1) -MaxColumn 6
    $logic = Extract-InternalLogicRows -Worksheet $Worksheet -StartRow ($titleRow + 2) -EndRow ($nextRow - 1)
    $result.Sections[$InternalLogicSectionLabel] = [PSCustomObject]@{
      HeaderValues = $headerValues
      Rows = $logic.LogicRows
    }
    $result.TailRows = $logic.TailRows
  }

  return $result
}

function Set-FontProperty {
  param(
    [Parameter(Mandatory = $true)]$Font,
    [Parameter(Mandatory = $true)][string]$Property,
    [Parameter(Mandatory = $true)][string]$Value
  )

  try {
    $Font.$Property = $Value
  } catch {
  }
}

function Set-FontSlots {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)]$Config,
    [bool]$Bold = $false
  )

  $Range.Font.Name = [string]$Config.global.fontSlots.latin
  Set-FontProperty -Font $Range.Font -Property "NameAscii" -Value ([string]$Config.global.fontSlots.latin)
  Set-FontProperty -Font $Range.Font -Property "NameOther" -Value ([string]$Config.global.fontSlots.latin)
  Set-FontProperty -Font $Range.Font -Property "NameFarEast" -Value ([string]$Config.global.fontSlots.cjk)
  $Range.Font.Size = [double]$Config.global.fontSlots.latinSize
  $Range.Font.Bold = $Bold
}

function Set-ThinBlackBorders {
  param([Parameter(Mandatory = $true)]$Range)

  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight, $xlInsideVertical, $xlInsideHorizontal)) {
    $border = $Range.Borders.Item($borderIndex)
    $border.LineStyle = $xlContinuous
    $border.Weight = $xlThin
    $border.Color = 0
  }
}

function Set-ThinBlackBorder {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)][int]$BorderIndex
  )

  $border = $Range.Borders.Item($BorderIndex)
  $border.LineStyle = $xlContinuous
  $border.Weight = $xlThin
  $border.Color = 0
}

function Set-RowBottomBorder {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  if ($Row -lt 1) {
    return
  }

  $range = $Worksheet.Range($Worksheet.Cells.Item($Row, 1), $Worksheet.Cells.Item($Row, $MaxColumn))
  Set-ThinBlackBorder -Range $range -BorderIndex $xlEdgeBottom
}

function Clear-RangeVisuals {
  param([Parameter(Mandatory = $true)]$Range)

  try {
    $Range.UnMerge() | Out-Null
  } catch {
  }
  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight, $xlInsideVertical, $xlInsideHorizontal)) {
    $Range.Borders.Item($borderIndex).LineStyle = $xlLineStyleNone
  }
  $Range.Interior.Pattern = $xlPatternNone
}

function Set-FillRgb {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)][string]$Rgb
  )

  $Range.Interior.Pattern = $xlSolid
  $Range.Interior.Color = Convert-RgbToComColor -Rgb $Rgb
}

function Set-FillTableHeaderLight {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)]$Config
  )

  $Range.Interior.Pattern = $xlSolid
  $Range.Interior.ThemeColor = [int]$Config.fills.tableHeaderLight.excelCom.themeColor
  $Range.Interior.TintAndShade = [double]$Config.fills.tableHeaderLight.excelCom.tintAndShade
}

function Merge-Range {
  param([Parameter(Mandatory = $true)]$Range)
  try {
    if ($Range.MergeCells) {
      $Range.UnMerge() | Out-Null
    }
  } catch {
  }
  $Range.Merge() | Out-Null
}

function Get-SafeSheetSubAddress {
  param([string]$SheetName)
  $escaped = $SheetName.Replace("'", "''")
  return "#'$escaped'!A1"
}

function Set-TopArea {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$Data,
    [Parameter(Mandatory = $true)]$Config
  )

  $Worksheet.Range("A1").Value2 = [string]$Config.regions.apiNameDescription.headerRow.labels[0]
  $Worksheet.Range("B1").Value2 = [string]$Config.regions.apiNameDescription.headerRow.labels[1]
  $Worksheet.Range("A2").Value2 = [string]$Data.ApiName
  $Worksheet.Range("B2").Value2 = [string]$Data.ApiDescription

  $Worksheet.Rows.Item(1).RowHeight = [double]$Config.regions.apiNameDescription.headerRow.rowHeight
  $Worksheet.Rows.Item(2).RowHeight = [double]$Config.regions.apiNameDescription.contentRow.rowHeight

  $header = $Worksheet.Range("A1:B1")
  Set-FontSlots -Range $header -Config $Config -Bold $true
  Set-FillRgb -Range $header -Rgb ([string]$Config.fills.blueSection.fgColor.rgb)
  $header.HorizontalAlignment = $xlCenter
  $header.VerticalAlignment = $xlCenter
  $header.WrapText = $true
  Set-ThinBlackBorders -Range $header

  $content = $Worksheet.Range("A2:B2")
  Set-FontSlots -Range $content -Config $Config -Bold $false
  $content.HorizontalAlignment = $xlLeft
  $content.VerticalAlignment = $xlCenter
  $content.WrapText = $true
  Set-ThinBlackBorders -Range $content
  Set-FillRgb -Range $Worksheet.Range("B2") -Rgb ([string]$Config.fills.apiDescriptionGray.fgColor.rgb)

  $returnArea = $Worksheet.Range("C1:G2")
  $returnArea.Clear() | Out-Null
  Clear-RangeVisuals -Range $returnArea
  Set-ThinBlackBorders -Range $Worksheet.Range("B1:B2")

  $returnCell = $Worksheet.Range("C1")
  $returnCell.Value2 = $ReturnLinkText
  $Worksheet.Hyperlinks.Add($returnCell, "", "#'Api_List'!A1") | Out-Null
  $returnCell.Font.Name = "Times New Roman"
  $returnCell.Font.Size = 10
  $returnCell.Font.Underline = $xlUnderlineStyleSingle
  $returnCell.Font.Color = Convert-RgbToComColor -Rgb ([string]$Config.fonts.hyperlink.color.rgb)
  $returnCell.HorizontalAlignment = $xlLeft
  $returnCell.VerticalAlignment = $xlCenter
  Clear-RangeVisuals -Range $returnCell
  Set-ThinBlackBorder -Range $Worksheet.Range("B1:B2") -BorderIndex $xlEdgeRight
}

function Set-ColumnWidths {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$Config
  )

  foreach ($property in $Config.global.columnWidths.PSObject.Properties) {
    $Worksheet.Columns.Item($property.Name).ColumnWidth = [double]$property.Value
  }
}

function Get-CombinedColumnWidth {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$StartColumn,
    [Parameter(Mandatory = $true)][int]$EndColumn
  )

  $width = 0.0
  for ($col = $StartColumn; $col -le $EndColumn; $col++) {
    $width += [double]$Worksheet.Columns.Item($col).ColumnWidth
  }
  return [Math]::Min([Math]::Max($width, 1.0), 255.0)
}

function Measure-TextHeight {
  param(
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [AllowEmptyString()][string]$Text,
    [Parameter(Mandatory = $true)][double]$ColumnWidth,
    [string]$FontName,
    [double]$FontSize,
    [bool]$Bold,
    [double]$MinHeight
  )

  if ($Text.Trim().Length -eq 0) {
    return $MinHeight
  }

  $MeasureSheet.Cells.Clear() | Out-Null
  $cell = $MeasureSheet.Range("A1")
  $MeasureSheet.Columns.Item(1).ColumnWidth = [Math]::Min([Math]::Max($ColumnWidth, 1.0), 255.0)
  $cell.Value2 = $Text
  $cell.WrapText = $true
  if ($FontName) {
    $cell.Font.Name = $FontName
  }
  if ($FontSize -gt 0) {
    $cell.Font.Size = $FontSize
  }
  $cell.Font.Bold = $Bold
  $MeasureSheet.Rows.Item(1).AutoFit() | Out-Null
  return [Math]::Min([Math]::Max([double]$MeasureSheet.Rows.Item(1).RowHeight, $MinHeight), 409.5)
}

function Set-ContentRowHeight {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$MaxColumn,
    [Parameter(Mandatory = $true)][double]$MinHeight
  )

  $desired = $MinHeight
  $seen = @{}
  for ($col = 1; $col -le $MaxColumn; $col++) {
    $cell = $Worksheet.Cells.Item($Row, $col)
    if ($cell.MergeCells) {
      $area = $cell.MergeArea
      $address = [string]$area.Address($false, $false)
      if ($seen.ContainsKey($address)) {
        continue
      }
      $seen[$address] = $true
      if ($area.Row -ne $Row -or $area.Rows.Count -ne 1) {
        continue
      }
      $text = [string]$area.Cells.Item(1, 1).Text
      $width = Get-CombinedColumnWidth -Worksheet $Worksheet -StartColumn $area.Column -EndColumn ($area.Column + $area.Columns.Count - 1)
      $font = $area.Cells.Item(1, 1).Font
      $desired = [Math]::Max($desired, (Measure-TextHeight -MeasureSheet $MeasureSheet -Text $text -ColumnWidth $width -FontName ([string]$font.Name) -FontSize ([double]$font.Size) -Bold ([bool]$font.Bold) -MinHeight $MinHeight))
    } else {
      $text = [string]$cell.Text
      if ($text.Trim().Length -eq 0) {
        continue
      }
      $width = Get-CombinedColumnWidth -Worksheet $Worksheet -StartColumn $col -EndColumn $col
      $desired = [Math]::Max($desired, (Measure-TextHeight -MeasureSheet $MeasureSheet -Text $text -ColumnWidth $width -FontName ([string]$cell.Font.Name) -FontSize ([double]$cell.Font.Size) -Bold ([bool]$cell.Font.Bold) -MinHeight $MinHeight))
    }
  }
  $Worksheet.Rows.Item($Row).RowHeight = [Math]::Min([Math]::Max([Math]::Ceiling($desired), $MinHeight), 409.5)
}

function Write-BlankRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row
  )

  $range = $Worksheet.Range($Worksheet.Cells.Item($Row, 1), $Worksheet.Cells.Item($Row, $VisibleColumnLimit))
  $range.Clear() | Out-Null
  Clear-RangeVisuals -Range $range
}

function Write-MergedTitle {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$Config,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][int]$EndColumn,
    [double]$Height,
    [string]$FillKind = "blue"
  )

  $range = $Worksheet.Range($Worksheet.Cells.Item($Row, 1), $Worksheet.Cells.Item($Row, $EndColumn))
  $range.Clear() | Out-Null
  Merge-Range -Range $range
  $range.Cells.Item(1, 1).Value2 = $Label
  Set-FontSlots -Range $range -Config $Config -Bold $true
  if ($FillKind -eq "yellow") {
    Set-FillRgb -Range $range -Rgb ([string]$Config.fills.middleOfficeYellow.fgColor.rgb)
  } else {
    Set-FillRgb -Range $range -Rgb ([string]$Config.fills.blueSection.fgColor.rgb)
  }
  $range.HorizontalAlignment = $xlLeft
  $range.VerticalAlignment = $xlCenter
  $range.WrapText = $true
  Set-ThinBlackBorders -Range $range
  $Worksheet.Rows.Item($Row).RowHeight = $Height
}

function Write-RequestResponseSection {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [Parameter(Mandatory = $true)]$Config,
    [Parameter(Mandatory = $true)][int]$StartRow,
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)]$SectionData
  )

  Write-MergedTitle -Worksheet $Worksheet -Config $Config -Row $StartRow -Label $Label -EndColumn 7 -Height ([double]$Config.global.rowHeights.sectionTitle)
  $headerRow = $StartRow + 1
  for ($col = 1; $col -le 7; $col++) {
    $Worksheet.Cells.Item($headerRow, $col).Value2 = [string]$SectionData.HeaderValues[$col - 1]
  }
  $headerRange = $Worksheet.Range($Worksheet.Cells.Item($headerRow, 1), $Worksheet.Cells.Item($headerRow, 7))
  Set-FontSlots -Range $headerRange -Config $Config -Bold $true
  Set-FillTableHeaderLight -Range $headerRange -Config $Config
  $headerRange.HorizontalAlignment = $xlCenter
  $headerRange.VerticalAlignment = $xlCenter
  $headerRange.WrapText = $true
  Set-ThinBlackBorders -Range $headerRange
  $Worksheet.Rows.Item($headerRow).RowHeight = [double]$Config.global.rowHeights.tableHeader

  $row = $StartRow + 2
  foreach ($item in $SectionData.Rows) {
    for ($col = 1; $col -le 7; $col++) {
      $Worksheet.Cells.Item($row, $col).Value2 = [string]$item.Values[$col - 1]
    }
    $range = $Worksheet.Range($Worksheet.Cells.Item($row, 1), $Worksheet.Cells.Item($row, 7))
    Set-FontSlots -Range $range -Config $Config -Bold $false
    $range.Interior.Pattern = $xlPatternNone
    $range.VerticalAlignment = $xlCenter
    $range.WrapText = $true
    $range.HorizontalAlignment = $xlLeft
    $Worksheet.Cells.Item($row, 1).HorizontalAlignment = $xlCenter
    Set-ThinBlackBorders -Range $range
    Set-ContentRowHeight -Worksheet $Worksheet -MeasureSheet $MeasureSheet -Row $row -MaxColumn 7 -MinHeight ([double]$Config.global.rowHeights.content)
    $row++
  }

  $lastVisibleRow = if ($row -gt ($StartRow + 2)) { $row - 1 } else { $headerRow }
  Set-RowBottomBorder -Worksheet $Worksheet -Row $lastVisibleRow -MaxColumn 7
  return $row
}

function Write-ExampleSection {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [Parameter(Mandatory = $true)]$Config,
    [Parameter(Mandatory = $true)][int]$StartRow,
    [Parameter(Mandatory = $true)]$SectionData
  )

  Write-MergedTitle -Worksheet $Worksheet -Config $Config -Row $StartRow -Label $ExampleSectionLabel -EndColumn 6 -Height ([double]$Config.global.rowHeights.sectionTitle)
  $headerRow = $StartRow + 1
  $Worksheet.Cells.Item($headerRow, 1).Value2 = [string]$SectionData.HeaderValues[0]
  $Worksheet.Cells.Item($headerRow, 2).Value2 = [string]$SectionData.HeaderValues[1]
  $Worksheet.Cells.Item($headerRow, 4).Value2 = [string]$SectionData.HeaderValues[3]
  Merge-Range -Range $Worksheet.Range(("B{0}:C{0}" -f $headerRow))
  Merge-Range -Range $Worksheet.Range(("D{0}:F{0}" -f $headerRow))
  $headerRange = $Worksheet.Range($Worksheet.Cells.Item($headerRow, 1), $Worksheet.Cells.Item($headerRow, 6))
  Set-FontSlots -Range $headerRange -Config $Config -Bold $false
  Set-FillTableHeaderLight -Range $headerRange -Config $Config
  $headerRange.HorizontalAlignment = $xlCenter
  $headerRange.VerticalAlignment = $xlCenter
  $headerRange.WrapText = $true
  Set-ThinBlackBorders -Range $headerRange
  $Worksheet.Rows.Item($headerRow).RowHeight = [double]$Config.global.rowHeights.tableHeader

  $row = $StartRow + 2
  foreach ($item in $SectionData.Rows) {
    $Worksheet.Cells.Item($row, 1).Value2 = [string]$item.Values[0]
    $Worksheet.Cells.Item($row, 2).Value2 = [string]$item.Values[1]
    $Worksheet.Cells.Item($row, 4).Value2 = [string]$item.Values[3]
    Merge-Range -Range $Worksheet.Range(("B{0}:C{0}" -f $row))
    Merge-Range -Range $Worksheet.Range(("D{0}:F{0}" -f $row))
    $range = $Worksheet.Range($Worksheet.Cells.Item($row, 1), $Worksheet.Cells.Item($row, 6))
    Set-FontSlots -Range $range -Config $Config -Bold $false
    Set-FillRgb -Range $range -Rgb ([string]$Config.fills.scenarioContentWhite.fgColor.rgb)
    $range.HorizontalAlignment = $xlLeft
    $range.VerticalAlignment = $xlCenter
    $range.WrapText = $true
    Set-ThinBlackBorders -Range $range
    Set-ContentRowHeight -Worksheet $Worksheet -MeasureSheet $MeasureSheet -Row $row -MaxColumn 6 -MinHeight ([double]$Config.global.rowHeights.content)
    $row++
  }

  $lastVisibleRow = if ($row -gt ($StartRow + 2)) { $row - 1 } else { $headerRow }
  Set-RowBottomBorder -Worksheet $Worksheet -Row $lastVisibleRow -MaxColumn 6
  return $row
}

function Write-InternalLogicSection {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [Parameter(Mandatory = $true)]$Config,
    [Parameter(Mandatory = $true)][int]$StartRow,
    [Parameter(Mandatory = $true)]$SectionData
  )

  Write-MergedTitle -Worksheet $Worksheet -Config $Config -Row $StartRow -Label $InternalLogicSectionLabel -EndColumn 6 -Height ([double]$Config.global.rowHeights.sectionTitle)
  $headerRow = $StartRow + 1
  $Worksheet.Cells.Item($headerRow, 1).Value2 = [string]$SectionData.HeaderValues[0]
  $Worksheet.Cells.Item($headerRow, 2).Value2 = [string]$SectionData.HeaderValues[1]
  Merge-Range -Range $Worksheet.Range(("B{0}:F{0}" -f $headerRow))
  $headerRange = $Worksheet.Range($Worksheet.Cells.Item($headerRow, 1), $Worksheet.Cells.Item($headerRow, 6))
  Set-FontSlots -Range $headerRange -Config $Config -Bold $true
  Set-FillTableHeaderLight -Range $headerRange -Config $Config
  $headerRange.HorizontalAlignment = $xlCenter
  $headerRange.VerticalAlignment = $xlCenter
  $headerRange.WrapText = $true
  Set-ThinBlackBorders -Range $headerRange
  $Worksheet.Rows.Item($headerRow).RowHeight = [double]$Config.global.rowHeights.tableHeader

  $row = $StartRow + 2
  foreach ($item in $SectionData.Rows) {
    $Worksheet.Cells.Item($row, 1).Value2 = [string]$item.Values[0]
    $Worksheet.Cells.Item($row, 2).Value2 = [string]$item.Values[1]
    Merge-Range -Range $Worksheet.Range(("B{0}:F{0}" -f $row))
    $range = $Worksheet.Range($Worksheet.Cells.Item($row, 1), $Worksheet.Cells.Item($row, 6))
    Set-FontSlots -Range $range -Config $Config -Bold $false
    $range.VerticalAlignment = $xlCenter
    $range.WrapText = $true
    $range.HorizontalAlignment = $xlLeft
    Set-FillTableHeaderLight -Range $Worksheet.Cells.Item($row, 1) -Config $Config
    $Worksheet.Range($Worksheet.Cells.Item($row, 2), $Worksheet.Cells.Item($row, 6)).Interior.Pattern = $xlPatternNone
    Set-ThinBlackBorders -Range $range
    Set-ContentRowHeight -Worksheet $Worksheet -MeasureSheet $MeasureSheet -Row $row -MaxColumn 6 -MinHeight ([double]$Config.global.rowHeights.content)
    $row++
  }

  $lastVisibleRow = if ($row -gt ($StartRow + 2)) { $row - 1 } else { $headerRow }
  Set-RowBottomBorder -Worksheet $Worksheet -Row $lastVisibleRow -MaxColumn 6
  return $row
}

function Write-TailRows {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [Parameter(Mandatory = $true)]$Config,
    [Parameter(Mandatory = $true)][int]$StartRow,
    [Parameter(Mandatory = $true)]$Rows
  )

  $row = $StartRow
  foreach ($item in $Rows) {
    for ($col = 1; $col -le 7; $col++) {
      $Worksheet.Cells.Item($row, $col).Value2 = [string]$item.Values[$col - 1]
    }
    $range = $Worksheet.Range($Worksheet.Cells.Item($row, 1), $Worksheet.Cells.Item($row, 7))
    Set-FontSlots -Range $range -Config $Config -Bold $false
    $range.Interior.Pattern = $xlPatternNone
    $range.VerticalAlignment = $xlCenter
    $range.HorizontalAlignment = $xlLeft
    $range.WrapText = $true
    Set-ThinBlackBorders -Range $range
    Set-ContentRowHeight -Worksheet $Worksheet -MeasureSheet $MeasureSheet -Row $row -MaxColumn 7 -MinHeight ([double]$Config.global.rowHeights.content)
    $row++
  }
  return $row
}

function Clear-OutsideScope {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$LastRow
  )

  # The worksheet has just been recreated. Do not clear or delete H:AZ / bottom
  # rows here; broad operations create blank XML cell records and stale UsedRange.
  [void]$Worksheet
  [void]$LastRow
}

function Rebuild-Sheet {
  param(
    [Parameter(Mandatory = $true)]$Workbook,
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [Parameter(Mandatory = $true)]$Config,
    [Parameter(Mandatory = $true)]$Data
  )

  $originalIndex = [int]$Data.Index
  $sheetName = [string]$Data.Name
  $previousSheetName = ""
  if ($originalIndex -gt 1) {
    $previousSheetName = [string]$Workbook.Worksheets.Item($originalIndex - 1).Name
  }
  $oldSheet = $Workbook.Worksheets.Item($sheetName)
  $oldTempName = ("__old_{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 12)))
  $newTempName = ("__api_rebuild_{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 12)))
  $oldSheet.Name = $oldTempName
  $newSheet = $Workbook.Worksheets.Add()
  $newSheet.Name = $newTempName

  Set-ColumnWidths -Worksheet $newSheet -Config $Config
  Set-TopArea -Worksheet $newSheet -Data $Data -Config $Config
  Write-BlankRow -Worksheet $newSheet -Row 3

  $row = 4
  foreach ($label in @("Header", "Request", "Response")) {
    if ($Data.Sections.ContainsKey($label)) {
      $row = Write-RequestResponseSection -Worksheet $newSheet -MeasureSheet $MeasureSheet -Config $Config -StartRow $row -Label $label -SectionData $Data.Sections[$label]
      Write-BlankRow -Worksheet $newSheet -Row $row
      $row++
    }
  }

  if ($Data.Sections.ContainsKey($ExampleSectionLabel)) {
    $row = Write-ExampleSection -Worksheet $newSheet -MeasureSheet $MeasureSheet -Config $Config -StartRow $row -SectionData $Data.Sections[$ExampleSectionLabel]
    Write-BlankRow -Worksheet $newSheet -Row $row
    $row++
  }

  if ($Data.Sections.ContainsKey($MiddleOfficeSectionLabel)) {
    Write-MergedTitle -Worksheet $newSheet -Config $Config -Row $row -Label $MiddleOfficeSectionLabel -EndColumn 6 -Height ([double]$Config.global.rowHeights.middleOfficeTitle) -FillKind "yellow"
    $row++
    Write-BlankRow -Worksheet $newSheet -Row $row
    $row++
  }

  if ($Data.Sections.ContainsKey($InternalLogicSectionLabel)) {
    $row = Write-InternalLogicSection -Worksheet $newSheet -MeasureSheet $MeasureSheet -Config $Config -StartRow $row -SectionData $Data.Sections[$InternalLogicSectionLabel]
  }

  if ($Data.TailRows.Count -gt 0) {
    Write-BlankRow -Worksheet $newSheet -Row $row
    $row++
    $row = Write-TailRows -Worksheet $newSheet -MeasureSheet $MeasureSheet -Config $Config -StartRow $row -Rows $Data.TailRows
  }

  $lastRow = [Math]::Max(1, $row - 1)
  Clear-OutsideScope -Worksheet $newSheet -LastRow $lastRow
  $oldSheet.Delete() | Out-Null
  $newSheet.Name = $sheetName
  $missing = [System.Type]::Missing
  if ($previousSheetName.Length -eq 0) {
    if ($newSheet.Index -ne 1) {
      $newSheet.Move($Workbook.Worksheets.Item(1)) | Out-Null
    }
  } else {
    $previousSheet = $Workbook.Worksheets.Item($previousSheetName)
    if ($newSheet.Index -ne ($previousSheet.Index + 1)) {
      $newSheet.Move($missing, $previousSheet) | Out-Null
    }
  }
  $newSheet.Activate() | Out-Null
  try {
    if ($null -ne $Workbook.Application.ActiveWindow) {
      $Workbook.Application.ActiveWindow.DisplayGridlines = $false
    }
  } catch {
  }

  return $lastRow
}

$resolvedPath = Resolve-Path -LiteralPath $Path
$resolvedConfig = Resolve-Path -LiteralPath $ConfigPath
$config = Get-Content -LiteralPath $resolvedConfig.Path -Encoding UTF8 -Raw | ConvertFrom-Json

# -CreateBackup is retained for backward-compatible invocations; same-directory
# .bak output is intentionally disabled by the Office deliverable edit contract.

$excel = New-Object -ComObject Excel.Application
$excel.Visible = [bool]$Visible
$excel.DisplayAlerts = $false
$workbook = $null
$measureWorkbook = $null

try {
  $workbook = $excel.Workbooks.Open($resolvedPath.Path)
  $measureWorkbook = $excel.Workbooks.Add()
  $measureSheet = $measureWorkbook.Worksheets.Item(1)

  $targets = New-Object System.Collections.Generic.List[object]
  if ($Sheets -and $Sheets.Count -gt 0) {
    foreach ($sheetName in $Sheets) {
      [void]$targets.Add($workbook.Worksheets.Item($sheetName))
    }
  } else {
    foreach ($worksheet in $workbook.Worksheets) {
      if (Test-ApiDetailSheet -Worksheet $worksheet) {
        [void]$targets.Add($worksheet)
      }
    }
  }

  if ($targets.Count -eq 0) {
    throw "No target API Detail worksheets found."
  }

  $extracted = New-Object System.Collections.Generic.List[object]
  $unsafe = New-Object System.Collections.Generic.List[object]
  foreach ($worksheet in $targets) {
    $lastRow = Get-LastTextRow -Worksheet $worksheet -MaxColumn $VisibleColumnLimit
    $issues = Test-UnsafeSheetContent -Worksheet $worksheet -LastRow $lastRow -LastColumn $VisibleColumnLimit
    if ($issues.Count -gt 0 -and -not $ForceRebuild) {
      [void]$unsafe.Add([PSCustomObject]@{
        Sheet = [string]$worksheet.Name
        Issues = @($issues)
      })
      continue
    }
    [void]$extracted.Add((Extract-ApiDetailSheet -Worksheet $worksheet))
  }

  if ($unsafe.Count -gt 0) {
    throw ("Some sheets are unsafe to rebuild automatically: {0}" -f (($unsafe | ConvertTo-Json -Depth 5 -Compress)))
  }

  $results = New-Object System.Collections.Generic.List[object]
  foreach ($data in $extracted) {
    $lastRow = Rebuild-Sheet -Workbook $workbook -MeasureSheet $measureSheet -Config $config -Data $data
    [void]$results.Add([PSCustomObject]@{
      Sheet = [string]$data.Name
      RowsRebuilt = $lastRow
      RequestRows = if ($data.Sections.ContainsKey("Request")) { $data.Sections["Request"].Rows.Count } else { 0 }
      ResponseRows = if ($data.Sections.ContainsKey("Response")) { $data.Sections["Response"].Rows.Count } else { 0 }
      ExampleRows = if ($data.Sections.ContainsKey($ExampleSectionLabel)) { $data.Sections[$ExampleSectionLabel].Rows.Count } else { 0 }
      InternalLogicRows = if ($data.Sections.ContainsKey($InternalLogicSectionLabel)) { $data.Sections[$InternalLogicSectionLabel].Rows.Count } else { 0 }
      TailRows = $data.TailRows.Count
    })
  }

  $workbook.Save()

  [PSCustomObject]@{
    Path = $resolvedPath.Path
    ConfigPath = $resolvedConfig.Path
    RebuiltSheets = $results.Count
    Sheets = $results
  } | ConvertTo-Json -Depth 6
} finally {
  if ($null -ne $measureWorkbook) {
    $measureWorkbook.Close($false) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($measureWorkbook) | Out-Null
  }
  if ($null -ne $workbook) {
    $workbook.Close($false) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) | Out-Null
  }
  $excel.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
  [System.GC]::Collect()
  [System.GC]::WaitForPendingFinalizers()
}
