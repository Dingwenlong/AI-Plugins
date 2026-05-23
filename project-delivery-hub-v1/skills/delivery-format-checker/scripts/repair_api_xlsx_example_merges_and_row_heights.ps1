param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string[]]$Sheets,

  [switch]$Visible
)

$ErrorActionPreference = "Stop"
$VisibleColumnLimit = 7
$ExampleSectionLabel = [string]::Concat([char]0x7BC4, [char]0x4F8B)
$MiddleOfficeSectionLabel = "For" + [string]::Concat([char]0x4E2D, [char]0x53F0, [char]0x958B, [char]0x767C, [char]0x4EBA, [char]0x54E1)
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
$xlTop = -4160

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
    [int]$MaxColumn = 6
  )

  for ($col = $MinColumn; $col -le $MaxColumn; $col++) {
    $value = $Worksheet.Cells.Item($Row, $col).Value2
    if ($null -ne $value -and ([string]$value).Trim().Length -gt 0) {
      return $true
    }
  }
  return $false
}

function Test-HighRiskMergeRange {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$StartColumn,
    [Parameter(Mandatory = $true)][int]$EndColumn
  )

  for ($col = $StartColumn; $col -le $EndColumn; $col++) {
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

function Get-ColumnLetter {
  param([Parameter(Mandatory = $true)][int]$Column)

  $name = ""
  while ($Column -gt 0) {
    $mod = ($Column - 1) % 26
    $name = [string][char](65 + $mod) + $name
    $Column = [Math]::Floor(($Column - $mod) / 26)
  }
  return $name
}

function Get-RangeAddress {
  param(
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$StartColumn,
    [Parameter(Mandatory = $true)][int]$EndColumn
  )

  $start = Get-ColumnLetter -Column $StartColumn
  $end = Get-ColumnLetter -Column $EndColumn
  return "${start}${Row}:${end}${Row}"
}

function Test-ExactSingleRowMerge {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$StartColumn,
    [Parameter(Mandatory = $true)][int]$EndColumn
  )

  $cell = $Worksheet.Cells.Item($Row, $StartColumn)
  if (-not $cell.MergeCells) {
    return $false
  }

  $expected = Get-RangeAddress -Row $Row -StartColumn $StartColumn -EndColumn $EndColumn
  $address = [string]$cell.MergeArea.Address($false, $false)
  return ($address -eq $expected)
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

function Repair-MergedRange {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$StartColumn,
    [Parameter(Mandatory = $true)][int]$EndColumn,
    [Parameter(Mandatory = $true)][bool]$IsHeader
  )

  $rangeAddress = Get-RangeAddress -Row $Row -StartColumn $StartColumn -EndColumn $EndColumn
  if (Test-ExactSingleRowMerge -Worksheet $Worksheet -Row $Row -StartColumn $StartColumn -EndColumn $EndColumn) {
    $target = $Worksheet.Range($Worksheet.Cells.Item($Row, $StartColumn), $Worksheet.Cells.Item($Row, $EndColumn))
    $target.WrapText = $true
    return [PSCustomObject]@{
      Row = $Row
      Range = $rangeAddress
      Status = "UNCHANGED"
      Detail = "already merged"
    }
  }

  $risk = Test-HighRiskMergeRange -Worksheet $Worksheet -Row $Row -StartColumn $StartColumn -EndColumn $EndColumn
  if ($risk) {
    return [PSCustomObject]@{
      Row = $Row
      Range = $rangeAddress
      Status = "SKIPPED_RISK"
      Detail = $risk
    }
  }

  $texts = @()
  for ($col = $StartColumn; $col -le $EndColumn; $col++) {
    $value = $Worksheet.Cells.Item($Row, $col).Value2
    if ($null -ne $value -and ([string]$value).Trim().Length -gt 0) {
      $texts += ([string]$value).Trim()
    }
  }

  $target = $Worksheet.Range($Worksheet.Cells.Item($Row, $StartColumn), $Worksheet.Cells.Item($Row, $EndColumn))
  try {
    if ($target.MergeCells) {
      $target.UnMerge()
    }
  } catch {
    # Excel can report a mixed merge state when only part of a row slice is selected.
  }

  $Worksheet.Cells.Item($Row, $StartColumn).Value2 = ($texts -join "`r`n")
  if ($EndColumn -gt $StartColumn) {
    $Worksheet.Range($Worksheet.Cells.Item($Row, $StartColumn + 1), $Worksheet.Cells.Item($Row, $EndColumn)).ClearContents() | Out-Null
  }

  $target.Merge() | Out-Null
  $target.WrapText = $true
  $target.HorizontalAlignment = if ($IsHeader) { $xlCenter } else { $xlLeft }
  $target.VerticalAlignment = if ($IsHeader) { $xlCenter } else { $xlTop }

  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight)) {
    Set-ThinBorder -Range $target -BorderIndex $borderIndex
  }
  $target.Borders.Item($xlInsideVertical).LineStyle = $xlLineStyleNone

  return [PSCustomObject]@{
    Row = $Row
    Range = $rangeAddress
    Status = "REPAIRED"
    Detail = if ($texts.Count -gt 1) { "consolidated $($texts.Count) cells" } else { "merged" }
  }
}

function Repair-ExampleRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][bool]$IsHeader
  )

  $aCell = $Worksheet.Cells.Item($Row, 1)
  $aCell.WrapText = $true
  $aCell.HorizontalAlignment = if ($IsHeader) { $xlCenter } else { $xlLeft }
  $aCell.VerticalAlignment = $xlCenter
  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight)) {
    Set-ThinBorder -Range $aCell -BorderIndex $borderIndex
  }

  $results = @()
  $results += Repair-MergedRange -Worksheet $Worksheet -Row $Row -StartColumn 2 -EndColumn 3 -IsHeader $IsHeader
  $results += Repair-MergedRange -Worksheet $Worksheet -Row $Row -StartColumn 4 -EndColumn 6 -IsHeader $IsHeader
  return $results
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
  return [Math]::Min([Math]::Max([double]$MeasureSheet.Rows.Item(1).RowHeight, 15.0), 409.5)
}

function Set-AutoFitVisibleRows {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$MeasureSheet,
    [Parameter(Mandatory = $true)][int]$LastRow,
    [hashtable]$FixedRows = @{}
  )

  $changedRows = 0
  for ($row = 1; $row -le $LastRow; $row++) {
    if ($FixedRows.ContainsKey($row)) {
      continue
    }
    if (-not (Test-RowHasContent -Worksheet $Worksheet -Row $row -MinColumn 1 -MaxColumn $VisibleColumnLimit)) {
      continue
    }

    $desiredHeight = 15.0
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

    $desiredHeight = [Math]::Min([Math]::Max([Math]::Ceiling($desiredHeight), 15.0), 409.5)
    if ([Math]::Abs([double]$Worksheet.Rows.Item($row).RowHeight - $desiredHeight) -gt 0.25) {
      $Worksheet.Rows.Item($row).RowHeight = $desiredHeight
      $changedRows++
    }
  }

  return $changedRows
}

function Get-FixedTemplateRows {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $fixedRows = @{}
  $fixedRows[1] = $true
  $fixedRows[2] = $true

  foreach ($label in @("Request", "Response", $ExampleSectionLabel, $MiddleOfficeSectionLabel, $InternalLogicSectionLabel)) {
    $sectionRow = Find-SectionRow -Worksheet $Worksheet -Label $label
    if ($sectionRow -gt 0) {
      $fixedRows[$sectionRow] = $true
      if ($label -ne $MiddleOfficeSectionLabel) {
        $fixedRows[$sectionRow + 1] = $true
      }
    }
  }

  return $fixedRows
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

  $changed = $false
  $results = @()
  $autoFitRowsChanged = 0

  foreach ($worksheet in $targetSheets) {
    $exampleRow = Find-SectionRow -Worksheet $worksheet -Label $ExampleSectionLabel
    $middleOfficeRow = Find-SectionRow -Worksheet $worksheet -Label $MiddleOfficeSectionLabel
    $lastRow = Get-LastContentRow -Worksheet $worksheet -MaxColumn $VisibleColumnLimit

    if ($exampleRow -gt 0 -and $lastRow -gt $exampleRow) {
      $startRow = $exampleRow + 1
      $endRow = if ($middleOfficeRow -gt $startRow) { $middleOfficeRow - 1 } else { $lastRow }
      $seenScenarioContent = $false

      for ($row = $startRow; $row -le $endRow; $row++) {
        $isHeader = ($row -eq $startRow)
        if (-not (Test-RowHasContent -Worksheet $worksheet -Row $row -MinColumn 1 -MaxColumn 6)) {
          if ($seenScenarioContent) {
            break
          }
          continue
        }
        if (-not $isHeader) {
          $seenScenarioContent = $true
        }

        foreach ($result in (Repair-ExampleRow -Worksheet $worksheet -Row $row -IsHeader $isHeader)) {
          $result | Add-Member -NotePropertyName Sheet -NotePropertyValue ([string]$worksheet.Name)
          $result | Add-Member -NotePropertyName Rule -NotePropertyValue "example_merge"
          $results += $result
          if ($result.Status -eq "REPAIRED") {
            $changed = $true
          }
        }
      }
    } else {
      $results += [PSCustomObject]@{
        Sheet = [string]$worksheet.Name
        Rule = "example_merge"
        Row = 0
        Range = ""
        Status = "SKIPPED_NO_EXAMPLE"
        Detail = ""
      }
    }

    $fixedRows = Get-FixedTemplateRows -Worksheet $worksheet
    $changedRows = Set-AutoFitVisibleRows -Worksheet $worksheet -MeasureSheet $measureSheet -LastRow $lastRow -FixedRows $fixedRows
    if ($changedRows -gt 0) {
      $changed = $true
      $autoFitRowsChanged += $changedRows
    }
  }

  if ($changed) {
    $workbook.Save()
  }

  $summary = [PSCustomObject]@{
    Path = $resolved.Path
    TargetSheets = $targetSheets.Count
    RepairedRanges = @($results | Where-Object { $_.Status -eq "REPAIRED" }).Count
    SkippedRiskRanges = @($results | Where-Object { $_.Status -eq "SKIPPED_RISK" }).Count
    AutoFitRowsChanged = $autoFitRowsChanged
    Results = $results
  }
  $summary | ConvertTo-Json -Depth 5
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
