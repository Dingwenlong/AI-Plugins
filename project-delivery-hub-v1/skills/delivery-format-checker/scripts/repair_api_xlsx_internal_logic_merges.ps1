param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string[]]$Sheets,

  [switch]$Visible
)

$ErrorActionPreference = "Stop"
$VisibleColumnLimit = 7
$ExampleSectionLabel = [string]::Concat([char]0x7BC4, [char]0x4F8B)
$InternalLogicSectionLabel = "API" + [string]::Concat([char]0x5167, [char]0x90E8, [char]0x696D, [char]0x52D9, [char]0x908F, [char]0x8F2F)

$xlEdgeLeft = 7
$xlEdgeTop = 8
$xlEdgeBottom = 9
$xlEdgeRight = 10
$xlInsideVertical = 11
$xlContinuous = 1
$xlThin = 2
$xlLineStyleNone = -4142
$xlAutomatic = -4105
$xlLeft = -4131
$xlCenter = -4108
$xlPatternSolid = 1

function Normalize-Text {
  param([object]$Value)
  if ($null -eq $Value) {
    return ""
  }
  return ([string]$Value).Trim() -replace "\s+", ""
}

function Test-ApiListSheet {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $name = [string]$Worksheet.Name
  if ($name -match '^(Api_List|API_List)$') {
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

  $a1 = Normalize-Text $Worksheet.Range("A1").Text
  if ($a1 -match "^APIName$") {
    return $true
  }

  $labels = @("Request", "Response", $ExampleSectionLabel, $InternalLogicSectionLabel)
  $found = 0
  $maxRows = [Math]::Min(120, [Math]::Max(1, $Worksheet.UsedRange.Rows.Count + $Worksheet.UsedRange.Row - 1))
  for ($row = 1; $row -le $maxRows; $row++) {
    for ($col = 1; $col -le $VisibleColumnLimit; $col++) {
      $text = Normalize-Text $Worksheet.Cells.Item($row, $col).Text
      if ($labels -contains $text) {
        $found++
      }
    }
  }

  return ($found -ge 2)
}

function Get-LastContentRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  $used = $Worksheet.UsedRange
  if ($null -eq $used) {
    return 0
  }

  $lastUsedRow = $used.Row + $used.Rows.Count - 1
  for ($row = $lastUsedRow; $row -ge 1; $row--) {
    for ($col = 1; $col -le $MaxColumn; $col++) {
      $value = $Worksheet.Cells.Item($row, $col).Value2
      if ($null -ne $value -and ([string]$value).Trim().Length -gt 0) {
        return $row
      }
    }
  }

  return 0
}

function Find-InternalLogicRow {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $lastRow = Get-LastContentRow -Worksheet $Worksheet -MaxColumn $VisibleColumnLimit
  for ($row = 1; $row -le $lastRow; $row++) {
    $text = Normalize-Text $Worksheet.Cells.Item($row, 1).Text
    if ($text -eq (Normalize-Text $InternalLogicSectionLabel)) {
      return $row
    }
  }

  return 0
}

function Test-RowHasContent {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row
  )

  for ($col = 1; $col -le 6; $col++) {
    $value = $Worksheet.Cells.Item($Row, $col).Value2
    if ($null -ne $value -and ([string]$value).Trim().Length -gt 0) {
      return $true
    }
  }
  return $false
}

function Test-HighRiskMergeRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row
  )

  for ($col = 2; $col -le 6; $col++) {
    $cell = $Worksheet.Cells.Item($Row, $col)
    if ($cell.HasFormula) {
      return "formula at $($cell.Address($false, $false))"
    }
    if ($cell.Hyperlinks.Count -gt 0) {
      return "hyperlink at $($cell.Address($false, $false))"
    }
  }

  return ""
}

function Test-ExactBfMerge {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row
  )

  $cell = $Worksheet.Cells.Item($Row, 2)
  if (-not $cell.MergeCells) {
    return $false
  }

  $address = [string]$cell.MergeArea.Address($false, $false)
  return ($address -eq "B${Row}:F${Row}")
}

function Set-ThinBorder {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)][int]$BorderIndex
  )

  $border = $Range.Borders.Item($BorderIndex)
  $border.LineStyle = $xlContinuous
  $border.Weight = $xlThin
  $border.ColorIndex = $xlAutomatic
}

function Set-TableHeaderLightFill {
  param([Parameter(Mandatory = $true)]$Range)

  $Range.Interior.Pattern = $xlPatternSolid
  $Range.Interior.ThemeColor = 10
  $Range.Interior.TintAndShade = 0.5999938962981048
}

function Set-InternalLogicLabelStyle {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)][bool]$IsHeader
  )

  $Range.WrapText = $true
  $Range.HorizontalAlignment = if ($IsHeader) { $xlCenter } else { $xlLeft }
  $Range.VerticalAlignment = $xlCenter
  Set-TableHeaderLightFill -Range $Range
  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight)) {
    Set-ThinBorder -Range $Range -BorderIndex $borderIndex
  }
}

function Set-InternalLogicDescriptionStyle {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)][bool]$IsHeader
  )

  $Range.HorizontalAlignment = if ($IsHeader) { $xlCenter } else { $xlLeft }
  $Range.VerticalAlignment = $xlCenter
  $Range.WrapText = $true
  if ($IsHeader) {
    Set-TableHeaderLightFill -Range $Range
  }
  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight)) {
    Set-ThinBorder -Range $Range -BorderIndex $borderIndex
  }
  $Range.Borders.Item($xlInsideVertical).LineStyle = $xlLineStyleNone
}

function Repair-InternalLogicRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][bool]$IsHeader
  )

  $aCell = $Worksheet.Cells.Item($Row, 1)
  Set-InternalLogicLabelStyle -Range $aCell -IsHeader $IsHeader

  if (Test-ExactBfMerge -Worksheet $Worksheet -Row $Row) {
    $target = $Worksheet.Range($Worksheet.Cells.Item($Row, 2), $Worksheet.Cells.Item($Row, 6))
    Set-InternalLogicDescriptionStyle -Range $target -IsHeader $IsHeader
    return [PSCustomObject]@{
      Row = $Row
      Range = "B${Row}:F${Row}"
      Status = "STYLED"
      Detail = "already merged; style refreshed"
    }
  }

  $risk = Test-HighRiskMergeRow -Worksheet $Worksheet -Row $Row
  if ($risk) {
    return [PSCustomObject]@{
      Row = $Row
      Range = "B${Row}:F${Row}"
      Status = "SKIPPED_RISK"
      Detail = $risk
    }
  }

  $texts = @()
  for ($col = 2; $col -le 6; $col++) {
    $value = $Worksheet.Cells.Item($Row, $col).Value2
    if ($null -ne $value -and ([string]$value).Trim().Length -gt 0) {
      $texts += ([string]$value).Trim()
    }
  }

  $target = $Worksheet.Range($Worksheet.Cells.Item($Row, 2), $Worksheet.Cells.Item($Row, 6))
  try {
    if ($target.MergeCells) {
      $target.UnMerge()
    }
  } catch {
    # Keep going; Excel may report mixed merge state for row slices.
  }

  $Worksheet.Cells.Item($Row, 2).Value2 = ($texts -join "`r`n")
  if ($texts.Count -gt 1) {
    $Worksheet.Cells.Item($Row, 2).WrapText = $true
  }
  $Worksheet.Range($Worksheet.Cells.Item($Row, 3), $Worksheet.Cells.Item($Row, 6)).ClearContents() | Out-Null

  $target.Merge() | Out-Null
  Set-InternalLogicDescriptionStyle -Range $target -IsHeader $IsHeader

  $Worksheet.Rows.Item($Row).AutoFit() | Out-Null
  if ($Worksheet.Rows.Item($Row).RowHeight -lt 20.1) {
    $Worksheet.Rows.Item($Row).RowHeight = 20.1
  }

  return [PSCustomObject]@{
    Row = $Row
    Range = "B${Row}:F${Row}"
    Status = "REPAIRED"
    Detail = if ($texts.Count -gt 1) { "consolidated $($texts.Count) cells" } else { "merged" }
  }
}

$resolved = Resolve-Path -LiteralPath $Path
$excel = New-Object -ComObject Excel.Application
$excel.Visible = [bool]$Visible
$excel.DisplayAlerts = $false
$workbook = $null

try {
  $workbook = $excel.Workbooks.Open($resolved.Path)

  $targetSheets = @()
  if ($Sheets -and $Sheets.Count -gt 0) {
    foreach ($sheetName in $Sheets) {
      $targetSheets += $workbook.Worksheets.Item($sheetName)
    }
  } else {
    foreach ($worksheet in $workbook.Worksheets) {
      if (Test-ApiDetailSheet -Worksheet $worksheet) {
        $targetSheets += $worksheet
      }
    }
  }

  if ($targetSheets.Count -eq 0) {
    throw "No target API Detail worksheets found."
  }

  $changed = $false
  $results = @()
  foreach ($worksheet in $targetSheets) {
    $logicRow = Find-InternalLogicRow -Worksheet $worksheet
    $lastRow = Get-LastContentRow -Worksheet $worksheet -MaxColumn $VisibleColumnLimit
    if ($logicRow -le 0 -or $lastRow -le $logicRow) {
      $results += [PSCustomObject]@{
        Sheet = [string]$worksheet.Name
        Row = 0
        Range = ""
        Status = "SKIPPED_NO_INTERNAL_LOGIC"
        Detail = ""
      }
      continue
    }

    $seenLogicContent = $false
    for ($row = $logicRow + 1; $row -le $lastRow; $row++) {
      if (-not (Test-RowHasContent -Worksheet $worksheet -Row $row)) {
        if ($seenLogicContent) {
          break
        }
        continue
      }
      $seenLogicContent = $true

      $result = Repair-InternalLogicRow -Worksheet $worksheet -Row $row -IsHeader ($row -eq ($logicRow + 1))
      $result | Add-Member -NotePropertyName Sheet -NotePropertyValue ([string]$worksheet.Name)
      $results += $result
      if ($result.Status -in @("REPAIRED", "STYLED")) {
        $changed = $true
      }
    }
  }

  if ($changed) {
    $workbook.Save()
  }

  $summary = [PSCustomObject]@{
    Path = $resolved.Path
    TargetSheets = $targetSheets.Count
    RepairedRows = @($results | Where-Object { $_.Status -eq "REPAIRED" }).Count
    StyledRows = @($results | Where-Object { $_.Status -eq "STYLED" }).Count
    SkippedRiskRows = @($results | Where-Object { $_.Status -eq "SKIPPED_RISK" }).Count
    Results = $results
  }
  $summary | ConvertTo-Json -Depth 5
} finally {
  if ($null -ne $workbook) {
    $workbook.Close($false) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook) | Out-Null
  }
  $excel.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
  [System.GC]::Collect()
  [System.GC]::WaitForPendingFinalizers()
}
