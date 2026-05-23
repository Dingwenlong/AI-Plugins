param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string[]]$Sheets,

  [string[]]$FunctionCodes,

  [switch]$Visible
)

$ErrorActionPreference = "Stop"

$VisibleColumnLimit = 7
$ApiListStyleColumnLimit = 10
$ContentMinHeight = 20.1

$ExampleSectionLabel = [string]::Concat([char]0x7BC4, [char]0x4F8B)
$MiddleOfficeSectionLabel = "For" + [string]::Concat([char]0x4E2D, [char]0x53F0, [char]0x958B, [char]0x767C, [char]0x4EBA, [char]0x54E1)
$InternalLogicSectionLabel = "API" + [string]::Concat([char]0x5167, [char]0x90E8, [char]0x696D, [char]0x52D9, [char]0x908F, [char]0x8F2F)

$xlEdgeTop = 8
$xlEdgeBottom = 9
$xlEdgeRight = 10
$xlContinuous = 1
$xlThin = 2
$xlLineStyleNone = -4142
$xlLeft = -4131
$xlCenter = -4108
$xlUnderlineStyleSingle = 2
$hyperlinkBlue = 0xC16305
$black = 0

function Normalize-Text {
  param([object]$Value)
  if ($null -eq $Value) {
    return ""
  }
  return ([string]$Value).Trim() -replace "\s+", ""
}

function Get-CellText {
  param([Parameter(Mandatory = $true)]$Cell)
  if ($null -eq $Cell.Value2) {
    return ""
  }
  return ([string]$Cell.Value2).Trim()
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

  if ((Normalize-Text $Worksheet.Range("A1").Text) -match "^APIName$") {
    return $true
  }

  $labels = @("Request", "Response", $ExampleSectionLabel, $InternalLogicSectionLabel)
  $found = 0
  $maxRows = [Math]::Min(120, [Math]::Max(1, $Worksheet.UsedRange.Rows.Count + $Worksheet.UsedRange.Row - 1))
  for ($row = 1; $row -le $maxRows; $row++) {
    for ($col = 1; $col -le $VisibleColumnLimit; $col++) {
      if ($labels -contains (Normalize-Text $Worksheet.Cells.Item($row, $col).Text)) {
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
  $lastUsedRow = $used.Row + $used.Rows.Count - 1
  for ($row = $lastUsedRow; $row -ge 1; $row--) {
    for ($col = 1; $col -le $MaxColumn; $col++) {
      if ((Get-CellText $Worksheet.Cells.Item($row, $col)).Length -gt 0) {
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
    if ((Normalize-Text $Worksheet.Cells.Item($row, 1).Text) -eq (Normalize-Text $Label)) {
      return $row
    }
  }
  return 0
}

function Test-RowHasContent {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  for ($col = 1; $col -le $MaxColumn; $col++) {
    if ((Get-CellText $Worksheet.Cells.Item($Row, $col)).Length -gt 0) {
      return $true
    }
  }
  return $false
}

function Set-ThinBlackBorder {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)][int]$BorderIndex
  )

  $border = $Range.Borders.Item($BorderIndex)
  $border.LineStyle = $xlContinuous
  $border.Weight = $xlThin
  $border.Color = $black
}

function Reset-MergedRangeBottomBorder {
  param([Parameter(Mandatory = $true)]$Range)

  $firstCell = $Range.Cells.Item(1, 1)
  $value = $firstCell.Value2
  $horizontal = $firstCell.HorizontalAlignment
  $vertical = $firstCell.VerticalAlignment
  $wrap = $firstCell.WrapText
  try {
    if ($Range.MergeCells) {
      $Range.UnMerge() | Out-Null
    }
  } catch {
  }

  $firstCell = $Range.Cells.Item(1, 1)
  $firstCell.Value2 = $value
  if ($Range.Columns.Count -gt 1) {
    $Range.Offset(0, 1).Resize(1, $Range.Columns.Count - 1).ClearContents() | Out-Null
  }
  $Range.Merge() | Out-Null
  $Range.HorizontalAlignment = $horizontal
  $Range.VerticalAlignment = $vertical
  $Range.WrapText = $wrap
  foreach ($borderIndex in @($xlEdgeTop, $xlEdgeBottom, $xlEdgeRight)) {
    Set-ThinBlackBorder -Range $Range -BorderIndex $borderIndex
  }
}

function Get-EstimatedWrappedRowHeight {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$Row,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  $maxLines = 1
  for ($col = 1; $col -le $MaxColumn; $col++) {
    $text = Get-CellText $Worksheet.Cells.Item($Row, $col)
    if ($text.Length -eq 0) {
      continue
    }

    $width = [Math]::Max([double]$Worksheet.Columns.Item($col).ColumnWidth, 1.0)
    $lineWidth = [Math]::Max($width * 1.15, 1.0)
    $cellLines = 0
    $lines = $text -split "`r?`n"
    if ($lines.Count -eq 0) {
      $lines = @($text)
    }

    foreach ($line in $lines) {
      $cellLines += [Math]::Max(1, [int][Math]::Ceiling(([double]$line.Length) / $lineWidth))
    }
    $maxLines = [Math]::Max($maxLines, $cellLines)
  }

  return [Math]::Min([Math]::Max($ContentMinHeight, $maxLines * 15.0), 409.5)
}

function Find-ApiListSheet {
  param([Parameter(Mandatory = $true)]$Workbook)

  foreach ($worksheet in $Workbook.Worksheets) {
    if (Test-ApiListSheet -Worksheet $worksheet) {
      return $worksheet
    }
  }
  return $null
}

function Find-ApiNameColumn {
  param([Parameter(Mandatory = $true)]$ApiList)

  $maxCol = [Math]::Min(30, $ApiList.UsedRange.Columns.Count + $ApiList.UsedRange.Column - 1)
  for ($row = 1; $row -le [Math]::Min(5, $ApiList.UsedRange.Rows.Count); $row++) {
    for ($col = 1; $col -le $maxCol; $col++) {
      $text = Normalize-Text $ApiList.Cells.Item($row, $col).Text
      if ($text -eq "API名稱" -or $text -eq "APIName") {
        return $col
      }
    }
  }
  return 5
}

function Get-TargetSheets {
  param([Parameter(Mandatory = $true)]$Workbook)

  $targets = New-Object System.Collections.Generic.List[object]
  if ($Sheets -and $Sheets.Count -gt 0) {
    foreach ($sheetName in $Sheets) {
      [void]$targets.Add($Workbook.Worksheets.Item($sheetName))
    }
  } else {
    foreach ($worksheet in $Workbook.Worksheets) {
      if (Test-ApiDetailSheet -Worksheet $worksheet) {
        [void]$targets.Add($worksheet)
      }
    }
  }
  return @($targets.ToArray())
}

function Repair-ApiListRows {
  param(
    [Parameter(Mandatory = $true)]$Workbook,
    [Parameter(Mandatory = $true)][object[]]$TargetSheets
  )

  $apiList = Find-ApiListSheet -Workbook $Workbook
  if ($null -eq $apiList) {
    throw "Api_List worksheet was not found."
  }

  $apiNameColumn = Find-ApiNameColumn -ApiList $apiList
  $methodToSheet = @{}
  foreach ($worksheet in $TargetSheets) {
    $method = Get-CellText $worksheet.Range("A2")
    if ($method.Length -gt 0 -and -not $methodToSheet.ContainsKey($method)) {
      $methodToSheet[$method] = [string]$worksheet.Name
    }
  }

  $lastRow = Get-LastContentRow -Worksheet $apiList -MaxColumn $ApiListStyleColumnLimit
  $changedRows = 0
  for ($row = 2; $row -le $lastRow; $row++) {
    $methodCell = $apiList.Cells.Item($row, $apiNameColumn)
    $method = Get-CellText $methodCell
    if (-not $methodToSheet.ContainsKey($method)) {
      continue
    }

    $sheetName = $methodToSheet[$method]
    $rowRange = $apiList.Range($apiList.Cells.Item($row, 1), $apiList.Cells.Item($row, $ApiListStyleColumnLimit))
    $rowRange.WrapText = $true
    $rowRange.VerticalAlignment = $xlCenter
    while ($methodCell.Hyperlinks.Count -gt 0) {
      $methodCell.Hyperlinks.Item(1).Delete()
    }
    $apiList.Hyperlinks.Add($methodCell, "", ("#'{0}'!A1" -f $sheetName)) | Out-Null
    $methodCell.Font.Name = "Times New Roman"
    $methodCell.Font.Size = 10
    $methodCell.Font.Underline = $xlUnderlineStyleSingle
    $methodCell.Font.Color = $hyperlinkBlue
    $methodCell.HorizontalAlignment = $xlLeft
    $methodCell.VerticalAlignment = $xlCenter
    $methodCell.WrapText = $true
    Set-ThinBlackBorder -Range $rowRange -BorderIndex $xlEdgeBottom
    Set-ThinBlackBorder -Range $methodCell -BorderIndex $xlEdgeBottom

    $apiList.Rows.Item($row).AutoFit() | Out-Null
    if ([double]$apiList.Rows.Item($row).RowHeight -lt $ContentMinHeight) {
      $apiList.Rows.Item($row).RowHeight = $ContentMinHeight
    }
    $estimatedHeight = Get-EstimatedWrappedRowHeight -Worksheet $apiList -Row $row -MaxColumn $ApiListStyleColumnLimit
    if ([double]$apiList.Rows.Item($row).RowHeight -lt $estimatedHeight) {
      $apiList.Rows.Item($row).RowHeight = $estimatedHeight
    }
    $changedRows++
  }

  return $changedRows
}

function Get-SectionRows {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $rows = @{}
  foreach ($label in @("Request", "Response", $ExampleSectionLabel, $MiddleOfficeSectionLabel, $InternalLogicSectionLabel)) {
    $row = Find-SectionRow -Worksheet $Worksheet -Label $label
    if ($row -gt 0) {
      $rows[$label] = $row
    }
  }
  return $rows
}

function Get-NextSectionRow {
  param(
    [Parameter(Mandatory = $true)][hashtable]$SectionRows,
    [Parameter(Mandatory = $true)][int]$CurrentRow
  )

  $next = 0
  foreach ($row in $SectionRows.Values) {
    if ([int]$row -gt $CurrentRow -and ($next -eq 0 -or [int]$row -lt $next)) {
      $next = [int]$row
    }
  }
  return $next
}

function Get-LastSectionContentRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][hashtable]$SectionRows,
    [Parameter(Mandatory = $true)][string]$Label,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  if (-not $SectionRows.ContainsKey($Label)) {
    return 0
  }
  $titleRow = [int]$SectionRows[$Label]
  $nextRow = Get-NextSectionRow -SectionRows $SectionRows -CurrentRow $titleRow
  $lastSemantic = Get-LastContentRow -Worksheet $Worksheet -MaxColumn $MaxColumn
  $endRow = if ($nextRow -gt 0) { $nextRow - 1 } else { $lastSemantic }
  for ($row = $endRow; $row -ge ($titleRow + 2); $row--) {
    if (Test-RowHasContent -Worksheet $Worksheet -Row $row -MaxColumn $MaxColumn) {
      return $row
    }
  }
  return 0
}

function Repair-SectionBottomBorders {
  param([Parameter(Mandatory = $true)]$Worksheet)

  $sectionRows = Get-SectionRows -Worksheet $Worksheet
  $changed = 0
  foreach ($item in @(
    @{ Label = "Request"; MaxColumn = 7 },
    @{ Label = "Response"; MaxColumn = 7 },
    @{ Label = $ExampleSectionLabel; MaxColumn = 6 },
    @{ Label = $InternalLogicSectionLabel; MaxColumn = 6 }
  )) {
    $lastRow = Get-LastSectionContentRow -Worksheet $Worksheet -SectionRows $sectionRows -Label $item.Label -MaxColumn $item.MaxColumn
    if ($lastRow -le 0) {
      continue
    }
    $range = $Worksheet.Range($Worksheet.Cells.Item($lastRow, 1), $Worksheet.Cells.Item($lastRow, [int]$item.MaxColumn))
    Set-ThinBlackBorder -Range $range -BorderIndex $xlEdgeBottom
    if ($item.Label -eq $ExampleSectionLabel) {
      Reset-MergedRangeBottomBorder -Range $Worksheet.Range(("B{0}:C{0}" -f $lastRow))
      Reset-MergedRangeBottomBorder -Range $Worksheet.Range(("D{0}:F{0}" -f $lastRow))
    } elseif ($item.Label -eq $InternalLogicSectionLabel) {
      Reset-MergedRangeBottomBorder -Range $Worksheet.Range(("B{0}:F{0}" -f $lastRow))
    }
    $changed++
  }
  return $changed
}

$resolved = Resolve-Path -LiteralPath $Path
$excel = New-Object -ComObject Excel.Application
$excel.Visible = [bool]$Visible
$excel.DisplayAlerts = $false
$workbook = $null

try {
  $workbook = $excel.Workbooks.Open($resolved.Path)
  $targetSheets = Get-TargetSheets -Workbook $workbook
  if ($targetSheets.Count -eq 0) {
    throw "No target API Detail worksheets found."
  }

  $apiListRowsChanged = Repair-ApiListRows -Workbook $workbook -TargetSheets $targetSheets
  $sectionBordersChanged = 0
  foreach ($worksheet in $targetSheets) {
    $sectionBordersChanged += Repair-SectionBottomBorders -Worksheet $worksheet
  }

  $workbook.Save()

  [PSCustomObject]@{
    Path = $resolved.Path
    TargetSheets = $targetSheets.Count
    ApiListRowsChanged = $apiListRowsChanged
    SectionBottomBordersChanged = $sectionBordersChanged
  } | ConvertTo-Json -Depth 4
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
