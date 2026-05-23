param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string[]]$Sheets,

  [switch]$Visible
)

$ErrorActionPreference = "Stop"
$VisibleColumnLimit = 7
$OutsideColumnStart = 8
$OutsideColumnEnd = 52
$ApiHeaderHeight = 15.95
$ApiContentHeight = 20.1
$SectionTitleHeight = 15.95
$TableHeaderHeight = 15
$MiddleOfficeTitleHeight = 17.1
$ContentMinHeight = 20.1

$ExampleSectionLabel = [string]::Concat([char]0x7BC4, [char]0x4F8B)
$MiddleOfficeSectionLabel = "For" + [string]::Concat([char]0x4E2D, [char]0x53F0, [char]0x958B, [char]0x767C, [char]0x4EBA, [char]0x54E1)
$InternalLogicSectionLabel = "API" + [string]::Concat([char]0x5167, [char]0x90E8, [char]0x696D, [char]0x52D9, [char]0x908F, [char]0x8F2F)

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
$xlAutomatic = -4105
$xlLeft = -4131
$xlCenter = -4108

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

function Find-SectionRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][string]$Label
  )

  $lastRow = Get-LastContentRow -Worksheet $Worksheet -MaxColumn $VisibleColumnLimit
  for ($row = 1; $row -le $lastRow; $row++) {
    $text = Normalize-Text $Worksheet.Cells.Item($row, 1).Text
    if ($text -eq (Normalize-Text $Label)) {
      return $row
    }
  }

  return 0
}

function Test-RowHasContent {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [int]$MinColumn = 1,
    [int]$MaxColumn = 7
  )

  for ($col = $MinColumn; $col -le $MaxColumn; $col++) {
    $value = $Worksheet.Cells.Item($Row, $col).Value2
    if ($null -ne $value -and ([string]$value).Trim().Length -gt 0) {
      return $true
    }
  }
  return $false
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

function Clear-RangeVisuals {
  param([Parameter(Mandatory = $true)]$Range)

  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight, $xlInsideVertical, $xlInsideHorizontal)) {
    $Range.Borders.Item($borderIndex).LineStyle = $xlLineStyleNone
  }
  $Range.Interior.Pattern = $xlPatternNone
}

function Clear-RangeContentAndLinks {
  param([Parameter(Mandatory = $true)]$Range)

  try {
    $Range.UnMerge() | Out-Null
  } catch {
  }

  foreach ($cell in $Range.Cells) {
    while ($cell.Hyperlinks.Count -gt 0) {
      $cell.Hyperlinks.Item(1).Delete()
    }
    $cell.ClearContents() | Out-Null
  }
}

function Repair-ApiNameDescriptionTop {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $Worksheet.Rows.Item(1).RowHeight = $ApiHeaderHeight
  $Worksheet.Rows.Item(2).RowHeight = $ApiContentHeight

  $headerRange = $Worksheet.Range("A1:B1")
  $headerRange.WrapText = $true
  $headerRange.HorizontalAlignment = $xlCenter
  $headerRange.VerticalAlignment = $xlCenter
  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight)) {
    Set-ThinBorder -Range $headerRange -BorderIndex $borderIndex
  }

  $contentRange = $Worksheet.Range("A2:B2")
  $contentRange.WrapText = $true
  $contentRange.HorizontalAlignment = $xlLeft
  $contentRange.VerticalAlignment = $xlCenter
  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight)) {
    Set-ThinBorder -Range $contentRange -BorderIndex $borderIndex
  }

  $returnArea = $Worksheet.Range("C1:G2")
  Clear-RangeVisuals -Range $returnArea
  Clear-RangeContentAndLinks -Range $returnArea
  Set-ThinBorder -Range $Worksheet.Range("B1") -BorderIndex $xlEdgeRight
  Set-ThinBorder -Range $Worksheet.Range("B2") -BorderIndex $xlEdgeRight
  $returnLink = $Worksheet.Range("C1")
  $returnLink.Value2 = "返回API_List"
  $Worksheet.Hyperlinks.Add($returnLink, "", "#'Api_List'!A1") | Out-Null
  $returnLink.Font.Underline = $true
  $returnLink.Font.Color = 0xC16305
  $returnLink.HorizontalAlignment = $xlLeft
  $returnLink.VerticalAlignment = $xlCenter
}

function Get-FixedTemplateRows {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $fixedRows = @{}
  $fixedRows[1] = $ApiHeaderHeight
  $fixedRows[2] = $ApiContentHeight

  $sectionHeights = @{
    "Request" = $SectionTitleHeight
    "Response" = $SectionTitleHeight
    $ExampleSectionLabel = $SectionTitleHeight
    $MiddleOfficeSectionLabel = $MiddleOfficeTitleHeight
    $InternalLogicSectionLabel = $SectionTitleHeight
  }

  foreach ($label in $sectionHeights.Keys) {
    $sectionRow = Find-SectionRow -Worksheet $Worksheet -Label $label
    if ($sectionRow -gt 0) {
      $fixedRows[$sectionRow] = $sectionHeights[$label]
      if ($label -ne $MiddleOfficeSectionLabel) {
        $fixedRows[$sectionRow + 1] = $TableHeaderHeight
      }
    }
  }

  return $fixedRows
}

function Set-FixedTemplateRows {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][hashtable]$FixedRows
  )

  $changed = 0
  foreach ($row in $FixedRows.Keys) {
    $target = [double]$FixedRows[$row]
    if ([Math]::Abs([double]$Worksheet.Rows.Item([int]$row).RowHeight - $target) -gt 0.25) {
      $Worksheet.Rows.Item([int]$row).RowHeight = $target
      $changed++
    }
  }

  return $changed
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
    [bool]$Bold
  )

  if ($Text.Trim().Length -eq 0) {
    return 0.0
  }

  $cell = $MeasureSheet.Range("A1")
  $MeasureSheet.Cells.Clear() | Out-Null
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
  return [Math]::Min([Math]::Max([double]$MeasureSheet.Rows.Item(1).RowHeight, $ContentMinHeight), 409.5)
}

function Set-AutoFitVisibleContentRows {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [Parameter(Mandatory = $true)][int]$LastRow,
    [Parameter(Mandatory = $true)][hashtable]$FixedRows
  )

  $changedRows = 0
  for ($row = 1; $row -le $LastRow; $row++) {
    if ($FixedRows.ContainsKey($row)) {
      continue
    }
    if (-not (Test-RowHasContent -Worksheet $Worksheet -Row $row -MinColumn 1 -MaxColumn $VisibleColumnLimit)) {
      continue
    }

    $desiredHeight = $ContentMinHeight
    $seenMergeAreas = @{}
    for ($col = 1; $col -le $VisibleColumnLimit; $col++) {
      $cell = $Worksheet.Cells.Item($row, $col)
      if ($cell.MergeCells) {
        $area = $cell.MergeArea
        $address = [string]$area.Address($false, $false)
        if ($seenMergeAreas.ContainsKey($address)) {
          continue
        }
        $seenMergeAreas[$address] = $true
        if ($area.Row -ne $row -or $area.Rows.Count -ne 1) {
          continue
        }
        $text = [string]$area.Cells.Item(1, 1).Text
        $width = Get-CombinedColumnWidth -Worksheet $Worksheet -StartColumn $area.Column -EndColumn ($area.Column + $area.Columns.Count - 1)
        $font = $area.Cells.Item(1, 1).Font
        $desiredHeight = [Math]::Max($desiredHeight, (Measure-TextHeight -MeasureSheet $MeasureSheet -Text $text -ColumnWidth $width -FontName ([string]$font.Name) -FontSize ([double]$font.Size) -Bold ([bool]$font.Bold)))
      } else {
        $text = [string]$cell.Text
        if ($text.Trim().Length -eq 0) {
          continue
        }
        $width = Get-CombinedColumnWidth -Worksheet $Worksheet -StartColumn $col -EndColumn $col
        $desiredHeight = [Math]::Max($desiredHeight, (Measure-TextHeight -MeasureSheet $MeasureSheet -Text $text -ColumnWidth $width -FontName ([string]$cell.Font.Name) -FontSize ([double]$cell.Font.Size) -Bold ([bool]$cell.Font.Bold)))
      }
    }

    $desiredHeight = [Math]::Min([Math]::Max([Math]::Ceiling($desiredHeight), $ContentMinHeight), 409.5)
    if ([Math]::Abs([double]$Worksheet.Rows.Item($row).RowHeight - $desiredHeight) -gt 0.25) {
      $Worksheet.Rows.Item($row).RowHeight = $desiredHeight
      $changedRows++
    }
  }

  return $changedRows
}

function Clear-OutsideScope {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$LastRow
  )

  $Worksheet.Range("H:AZ").Clear() | Out-Null

  $used = $Worksheet.UsedRange
  $usedLastRow = $used.Row + $used.Rows.Count - 1
  if ($LastRow -gt 0 -and $usedLastRow -gt $LastRow) {
    $Worksheet.Range($Worksheet.Cells.Item($LastRow + 1, 1), $Worksheet.Cells.Item($usedLastRow, $OutsideColumnEnd)).Clear() | Out-Null
  }
}

$resolved = Resolve-Path -LiteralPath $Path
$excel = New-Object -ComObject Excel.Application
$excel.Visible = [bool]$Visible
$excel.DisplayAlerts = $false
$workbook = $null
$measureWorkbook = $null

try {
  $workbook = $excel.Workbooks.Open($resolved.Path)
  $measureWorkbook = $excel.Workbooks.Add()
  $measureSheet = $measureWorkbook.Worksheets.Item(1)

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

  $fixedRowsChanged = 0
  $autoFitRowsChanged = 0
  foreach ($worksheet in $targetSheets) {
    $worksheet.Activate() | Out-Null
    if ($null -ne $excel.ActiveWindow) {
      $excel.ActiveWindow.DisplayGridlines = $false
    }

    $lastRow = Get-LastContentRow -Worksheet $worksheet -MaxColumn $VisibleColumnLimit
    Repair-ApiNameDescriptionTop -Worksheet $worksheet
    $fixedRows = Get-FixedTemplateRows -Worksheet $worksheet
    $fixedRowsChanged += Set-FixedTemplateRows -Worksheet $worksheet -FixedRows $fixedRows
    $autoFitRowsChanged += Set-AutoFitVisibleContentRows -Worksheet $worksheet -MeasureSheet $measureSheet -LastRow $lastRow -FixedRows $fixedRows
    Clear-OutsideScope -Worksheet $worksheet -LastRow $lastRow
  }

  $workbook.Save()

  [PSCustomObject]@{
    Path = $resolved.Path
    TargetSheets = $targetSheets.Count
    FixedRowsChanged = $fixedRowsChanged
    AutoFitRowsChanged = $autoFitRowsChanged
    OutsideScopeCleared = "H:AZ columns and bottom blank rows inside existing UsedRange"
  } | ConvertTo-Json -Depth 4
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
