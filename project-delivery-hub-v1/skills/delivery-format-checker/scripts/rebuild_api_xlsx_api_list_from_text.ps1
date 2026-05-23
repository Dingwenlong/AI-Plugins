param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string]$ConfigPath,

  [string]$RulesRoot,

  [switch]$Visible,

  [switch]$CreateBackup,

  [switch]$ForceRebuild,

  [switch]$NoBackendSourceSync
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
$xlSolid = 1
$xlLeft = -4131
$xlCenter = -4108
$xlGeneral = 1
$xlUnderlineStyleSingle = 2
$xlYes = 1
$xlAscending = 1
$xlSortNormal = 0
$xlSortRows = 2
$xlPinYin = 1

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

function Get-CellString {
  param([Parameter(Mandatory = $true)]$Cell)

  if ($null -eq $Cell.Value2) {
    return ""
  }
  return [string]$Cell.Value2
}

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
  if ($name -match '^(Api_List|API_List|API List)$') {
    return $true
  }

  $a1 = Normalize-Text $Worksheet.Range("A1").Text
  $e1 = Normalize-Text $Worksheet.Range("E1").Text
  return ($a1 -match "PRD" -and $e1 -match "API")
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

function Get-LastTextRow {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$MaxColumn
  )

  $used = $Worksheet.UsedRange
  $lastUsedRow = $used.Row + $used.Rows.Count - 1
  for ($row = $lastUsedRow; $row -ge 1; $row--) {
    for ($col = 1; $col -le $MaxColumn; $col++) {
      if ((Get-CellString $Worksheet.Cells.Item($row, $col)).Trim().Length -gt 0) {
        return $row
      }
    }
  }
  return 0
}

function Test-UnsafeSheetContent {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$LastRow,
    [Parameter(Mandatory = $true)][int]$LastColumn
  )

  $issues = New-Object System.Collections.Generic.List[string]

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

  if ($Worksheet.Shapes.Count -gt 0) {
    $issues.Add(("Shapes on Api_List: {0}" -f $Worksheet.Shapes.Count))
  }

  return $issues
}

function Get-SubAddress {
  param([Parameter(Mandatory = $true)]$Cell)

  if ($Cell.Hyperlinks.Count -le 0) {
    return ""
  }
  return [string]$Cell.Hyperlinks.Item(1).SubAddress
}

function Get-SheetNameFromSubAddress {
  param([AllowEmptyString()][string]$SubAddress)

  if (-not $SubAddress) {
    return ""
  }

  $value = $SubAddress
  if ($value.StartsWith("#")) {
    $value = $value.Substring(1)
  }

  if ($value -match "^'([^']+)'!") {
    return $Matches[1]
  }
  if ($value -match "^([^!]+)!") {
    return $Matches[1]
  }
  return ""
}

function Get-SafeSheetSubAddress {
  param([Parameter(Mandatory = $true)][string]$SheetName)

  $escaped = $SheetName.Replace("'", "''")
  return "#'$escaped'!A1"
}

function Find-MatchingApiSheet {
  param(
    [Parameter(Mandatory = $true)]$Workbook,
    [Parameter(Mandatory = $true)][string]$Method,
    [AllowEmptyString()][string]$CurrentTargetSheet
  )

  if ($CurrentTargetSheet) {
    try {
      $candidate = $Workbook.Worksheets.Item($CurrentTargetSheet)
      if ($null -ne $candidate) {
        return [string]$candidate.Name
      }
    } catch {
    }
  }

  foreach ($worksheet in $Workbook.Worksheets) {
    if (Test-ApiListSheet -Worksheet $worksheet) {
      continue
    }
    $apiName = (Get-CellString $worksheet.Range("A2")).Trim()
    if ($apiName -eq $Method) {
      return [string]$worksheet.Name
    }
  }

  foreach ($worksheet in $Workbook.Worksheets) {
    if (Test-ApiListSheet -Worksheet $worksheet) {
      continue
    }
    $name = [string]$worksheet.Name
    if ($Method.Length -gt 0 -and ($name.StartsWith($Method) -or $Method.StartsWith($name))) {
      return $name
    }
  }

  return ""
}

function Get-BackendSourceFromApiSheet {
  param(
    [Parameter(Mandatory = $true)]$Workbook,
    [Parameter(Mandatory = $true)][string]$SheetName
  )

  if (-not $SheetName) {
    return ""
  }

  try {
    $worksheet = $Workbook.Worksheets.Item($SheetName)
  } catch {
    return ""
  }

  $targetLabel = [string]::Concat(
    [char]0x6D89,
    [char]0x53CA,
    "BackendAPI"
  )
  $lastRow = Get-LastTextRow -Worksheet $worksheet -MaxColumn 7
  for ($row = 1; $row -le $lastRow; $row++) {
    if ((Normalize-Text $worksheet.Cells.Item($row, 1).Text) -eq (Normalize-Text $targetLabel)) {
      return Get-CellString $worksheet.Cells.Item($row, 2)
    }
  }
  return ""
}

function Get-PrdSortKey {
  param([AllowEmptyString()][string]$Value)

  $text = $Value.Trim()
  if (-not $text) {
    return "ZZZ"
  }
  $prefix = ""
  $numbers = @()
  foreach ($part in ($text -split "\.")) {
    if ($part -match "^([A-Za-z]+)(\d+)$") {
      $prefix = $Matches[1].ToUpperInvariant()
      $numbers += [int]$Matches[2]
    } elseif ($part -match "^\d+$") {
      $numbers += [int]$part
    } else {
      $prefix += $part.ToUpperInvariant()
    }
  }

  $segments = @($prefix)
  foreach ($number in $numbers) {
    $segments += ("{0:D6}" -f $number)
  }
  return ($segments -join ".")
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

function Clear-Borders {
  param([Parameter(Mandatory = $true)]$Range)

  foreach ($borderIndex in @($xlEdgeLeft, $xlEdgeTop, $xlEdgeBottom, $xlEdgeRight, $xlInsideVertical, $xlInsideHorizontal)) {
    $Range.Borders.Item($borderIndex).LineStyle = $xlLineStyleNone
  }
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

function Set-CellFontSlots {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)][string]$LatinFont,
    [Parameter(Mandatory = $true)][string]$CjkFont,
    [Parameter(Mandatory = $true)][double]$Size,
    [bool]$Bold = $false
  )

  $Range.Font.Name = $LatinFont
  Set-FontProperty -Font $Range.Font -Property "NameAscii" -Value $LatinFont
  Set-FontProperty -Font $Range.Font -Property "NameOther" -Value $LatinFont
  Set-FontProperty -Font $Range.Font -Property "NameFarEast" -Value $CjkFont
  $Range.Font.Size = $Size
  $Range.Font.Bold = $Bold
}

function Set-ApiListStyles {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)]$Config,
    [Parameter(Mandatory = $true)][int]$LastRow
  )

  $apiList = $Config.apiList
  $fonts = $Config.global.fontSlots
  $columns = @("A","B","C","D","E","F","G","H","I","J")

  foreach ($letter in $columns) {
    $columnConfig = $apiList.columns.$letter
    if ($null -ne $columnConfig.excelComWidth) {
      $Worksheet.Columns.Item($letter).ColumnWidth = [double]$columnConfig.excelComWidth
    }
  }

  $headerRange = $Worksheet.Range("A1:J1")
  $headerRange.RowHeight = [double]$apiList.rowHeights.headerRow
  $headerRange.WrapText = $true
  $headerRange.HorizontalAlignment = $xlCenter
  $headerRange.VerticalAlignment = $xlCenter
  Set-CellFontSlots -Range $headerRange -LatinFont $fonts.latin -CjkFont $fonts.cjk -Size ([double]$apiList.styles.header.font.size) -Bold $true
  $headerRange.Interior.Pattern = $xlSolid
  $headerRange.Interior.Color = Convert-RgbToComColor -Rgb ([string]$apiList.styles.header.fill.rgb)
  Set-ThinBlackBorders -Range $headerRange

  if ($LastRow -ge 2) {
    $dataRange = $Worksheet.Range(("A2:J{0}" -f $LastRow))
    $dataRange.WrapText = $true
    $dataRange.VerticalAlignment = $xlCenter
    $dataRange.Interior.Pattern = -4142
    Set-CellFontSlots -Range $dataRange -LatinFont $fonts.latin -CjkFont $fonts.cjk -Size ([double]$apiList.styles.generalData.font.size) -Bold $false
    Set-ThinBlackBorders -Range $dataRange

    $Worksheet.Range(("A2:A{0}" -f $LastRow)).HorizontalAlignment = $xlCenter
    $Worksheet.Range(("B2:D{0}" -f $LastRow)).HorizontalAlignment = $xlGeneral
    $Worksheet.Range(("F2:J{0}" -f $LastRow)).HorizontalAlignment = $xlGeneral

    $apiNameRange = $Worksheet.Range(("E2:E{0}" -f $LastRow))
    $apiNameRange.HorizontalAlignment = $xlLeft
    $apiNameRange.VerticalAlignment = $xlCenter
    $apiNameRange.WrapText = $true
    $apiNameRange.Font.Name = "Times New Roman"
    Set-FontProperty -Font $apiNameRange.Font -Property "NameAscii" -Value "Times New Roman"
    Set-FontProperty -Font $apiNameRange.Font -Property "NameOther" -Value "Times New Roman"
    $apiNameRange.Font.Size = [double]$apiList.styles.apiNameHyperlink.font.size
    $apiNameRange.Font.Bold = $false
    $apiNameRange.Font.Underline = $xlUnderlineStyleSingle
    $apiNameRange.Font.Color = Convert-RgbToComColor -Rgb ([string]$apiList.styles.apiNameHyperlink.font.colorRgb)
    Set-ThinBlackBorders -Range $apiNameRange

    $backendRange = $Worksheet.Range(("I2:I{0}" -f $LastRow))
    $backendRange.HorizontalAlignment = $xlLeft
    $backendRange.VerticalAlignment = $xlCenter
    $backendRange.WrapText = $true
    Set-ThinBlackBorders -Range $backendRange

    for ($row = 2; $row -le $LastRow; $row++) {
      $Worksheet.Rows.Item($row).AutoFit() | Out-Null
      $minHeight = [double]$apiList.rowHeights.dataRows.minHeight
      if ([double]$Worksheet.Rows.Item($row).RowHeight -lt $minHeight) {
        $Worksheet.Rows.Item($row).RowHeight = $minHeight
      }
    }
  }

  $Worksheet.Rows.Item(1).RowHeight = [double]$apiList.rowHeights.headerRow
  if ($LastRow -ge 1) {
    $autoFilterRange = $Worksheet.Range(("A1:J{0}" -f $LastRow))
    try {
      if ($Worksheet.AutoFilterMode) {
        $Worksheet.AutoFilterMode = $false
      }
    } catch {
    }
    $autoFilterRange.AutoFilter() | Out-Null
  }

  if ($LastRow -lt 1048576) {
    $clearStart = $LastRow + 1
    $Worksheet.Range(("A{0}:J1048576" -f $clearStart)).Clear() | Out-Null
  }
  $Worksheet.Range("K:XFD").Clear() | Out-Null
}

function Get-ApiListRows {
  param(
    [Parameter(Mandatory = $true)]$Worksheet,
    [Parameter(Mandatory = $true)][int]$LastRow,
    [Parameter(Mandatory = $true)][int]$LastColumn
  )

  $rows = New-Object System.Collections.Generic.List[object]

  for ($row = 2; $row -le $LastRow; $row++) {
    $values = @()
    $hasText = $false
    for ($col = 1; $col -le $LastColumn; $col++) {
      $value = Get-CellString $Worksheet.Cells.Item($row, $col)
      if ($value.Trim().Length -gt 0) {
        $hasText = $true
      }
      $values += $value
    }
    if (-not $hasText) {
      continue
    }

    $methodCell = $Worksheet.Cells.Item($row, 5)
    $subAddress = Get-SubAddress -Cell $methodCell
    $rows.Add([PSCustomObject]@{
      OriginalRow = $row
      Values = $values
      Method = $values[4]
      HyperlinkSubAddress = $subAddress
      TargetSheet = Get-SheetNameFromSubAddress -SubAddress $subAddress
      SortKey = Get-PrdSortKey -Value $values[0]
    })
  }

  return $rows
}

$resolvedPath = Resolve-Path -LiteralPath $Path
$resolvedConfig = Resolve-Path -LiteralPath $ConfigPath
$config = Get-Content -LiteralPath $resolvedConfig.Path -Encoding UTF8 -Raw | ConvertFrom-Json
$apiListConfig = $config.apiList
$lastColumn = 10

if ($CreateBackup) {
  Copy-Item -LiteralPath $resolvedPath.Path -Destination ($resolvedPath.Path + ".bak") -Force
}

$excel = New-Object -ComObject Excel.Application
$excel.Visible = [bool]$Visible
$excel.DisplayAlerts = $false
$workbook = $null

try {
  $workbook = $excel.Workbooks.Open($resolvedPath.Path)
  $apiList = Find-ApiListSheet -Workbook $workbook
  if ($null -eq $apiList) {
    throw "Api_List worksheet was not found."
  }

  $originalName = [string]$apiList.Name
  $originalIndex = [int]$apiList.Index
  $lastRow = Get-LastTextRow -Worksheet $apiList -MaxColumn $lastColumn
  if ($lastRow -lt 1) {
    throw "Api_List worksheet is empty."
  }

  $unsafeIssues = Test-UnsafeSheetContent -Worksheet $apiList -LastRow $lastRow -LastColumn $lastColumn
  if ($unsafeIssues.Count -gt 0 -and -not $ForceRebuild) {
    throw ("Api_List contains content that is unsafe to rebuild automatically: {0}. Re-run with -ForceRebuild only after user approval." -f ($unsafeIssues -join "; "))
  }

  $rows = Get-ApiListRows -Worksheet $apiList -LastRow $lastRow -LastColumn $lastColumn
  if ($rows.Count -eq 0) {
    throw "No Api_List data rows were extracted."
  }

  $backendSynced = 0
  foreach ($row in $rows) {
    $targetSheet = Find-MatchingApiSheet -Workbook $workbook -Method ([string]$row.Method) -CurrentTargetSheet ([string]$row.TargetSheet)
    if ($targetSheet) {
      $row.TargetSheet = $targetSheet
      $row.HyperlinkSubAddress = Get-SafeSheetSubAddress -SheetName $targetSheet
    }
    if (-not $NoBackendSourceSync -and $targetSheet) {
      $backendSource = Get-BackendSourceFromApiSheet -Workbook $workbook -SheetName $targetSheet
      if ($backendSource.Trim().Length -gt 0) {
        $row.Values[8] = $backendSource
        $backendSynced++
      }
    }
  }

  $sortedRows = @($rows | Sort-Object SortKey, OriginalRow)

  $apiList.Delete() | Out-Null
  if ($workbook.Worksheets.Count -eq 0) {
    $newSheet = $workbook.Worksheets.Add()
  } elseif ($originalIndex -gt $workbook.Worksheets.Count) {
    $missing = [System.Type]::Missing
    $newSheet = $workbook.Worksheets.Add($missing, $workbook.Worksheets.Item($workbook.Worksheets.Count))
  } else {
    $newSheet = $workbook.Worksheets.Add($workbook.Worksheets.Item($originalIndex))
  }
  $newSheet.Name = [string]$apiListConfig.sheetName

  $columns = @("A","B","C","D","E","F","G","H","I","J")
  for ($col = 1; $col -le $lastColumn; $col++) {
    $letter = $columns[$col - 1]
    $newSheet.Cells.Item(1, $col).Value2 = [string]$apiListConfig.columns.$letter.label
  }

  $outputRow = 2
  foreach ($row in $sortedRows) {
    for ($col = 1; $col -le $lastColumn; $col++) {
      $newSheet.Cells.Item($outputRow, $col).Value2 = [string]$row.Values[$col - 1]
    }

    $methodCell = $newSheet.Cells.Item($outputRow, 5)
    while ($methodCell.Hyperlinks.Count -gt 0) {
      $methodCell.Hyperlinks.Item(1).Delete()
    }
    if (([string]$row.HyperlinkSubAddress).Length -gt 0) {
      $newSheet.Hyperlinks.Add($methodCell, "", ([string]$row.HyperlinkSubAddress)) | Out-Null
    }
    $outputRow++
  }

  $newLastRow = $outputRow - 1
  Set-ApiListStyles -Worksheet $newSheet -Config $config -LastRow $newLastRow

  $newSheet.Activate() | Out-Null
  try {
    if ($null -ne $excel.ActiveWindow) {
      $excel.ActiveWindow.DisplayGridlines = $true
      $excel.ActiveWindow.SplitRow = 1
      $excel.ActiveWindow.FreezePanes = $true
    }
  } catch {
  }

  $workbook.Save()

  [PSCustomObject]@{
    Path = $resolvedPath.Path
    ConfigPath = $resolvedConfig.Path
    OriginalSheetName = $originalName
    RebuiltSheetName = [string]$newSheet.Name
    OriginalIndex = $originalIndex
    RowsExtracted = $rows.Count
    RowsWritten = $sortedRows.Count
    BackendSourcesSynced = $backendSynced
    HyperlinksRestored = @($sortedRows | Where-Object { ([string]$_.HyperlinkSubAddress).Length -gt 0 }).Count
    UnsafeIssuesIgnoredByForce = if ($ForceRebuild) { $unsafeIssues.Count } else { 0 }
    Range = ("A1:J{0}" -f $newLastRow)
  } | ConvertTo-Json -Depth 5
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
