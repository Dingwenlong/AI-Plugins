param(
  [Parameter(Mandatory = $true)]
  [string]$Path,

  [string[]]$Sheets,

  [switch]$AllSheets,

  [int]$VisibleColumnLimit = 7,

  [string]$EastAsianFont = ([string]::Concat([char]0x5FAE, [char]0x8EDF, [char]0x6B63, [char]0x9ED1, [char]0x9AD4)),

  [string]$LatinFont = "Times New Roman",

  [switch]$Visible
)

$ErrorActionPreference = "Stop"
$ExampleSectionLabel = [string]::Concat([char]0x7BC4, [char]0x4F8B)
$InternalLogicSectionLabel = "API" + [string]::Concat([char]0x5167, [char]0x90E8, [char]0x696D, [char]0x52D9, [char]0x908F, [char]0x8F2F)

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

function Set-FontProperty {
  param(
    [Parameter(Mandatory = $true)]$Font,
    [Parameter(Mandatory = $true)][string]$Property,
    [Parameter(Mandatory = $true)][string]$Value
  )

  try {
    $Font.$Property = $Value
  } catch {
    # Some Excel builds do not expose every script-specific font property.
  }
}

function Test-CjkCharacter {
  param([Parameter(Mandatory = $true)][string]$Char)

  $code = [int][char]$Char[0]
  return (
    ($code -ge 0x3400 -and $code -le 0x4DBF) -or
    ($code -ge 0x4E00 -and $code -le 0x9FFF) -or
    ($code -ge 0xF900 -and $code -le 0xFAFF) -or
    ($code -ge 0x3040 -and $code -le 0x30FF) -or
    ($code -ge 0x3100 -and $code -le 0x312F) -or
    ($code -ge 0xFF00 -and $code -le 0xFFEF)
  )
}

function Test-LatinCharacter {
  param([Parameter(Mandatory = $true)][string]$Char)

  return ($Char -match "^[A-Za-z0-9]$")
}

function Get-CharacterFontSample {
  param(
    [Parameter(Mandatory = $true)]$Range,
    [Parameter(Mandatory = $true)][string]$Kind
  )

  for ($row = 1; $row -le $Range.Rows.Count; $row++) {
    for ($col = 1; $col -le $Range.Columns.Count; $col++) {
      $cell = $Range.Cells.Item($row, $col)
      $value = $cell.Value2
      if ($null -eq $value) {
        continue
      }

      $text = [string]$value
      for ($index = 1; $index -le $text.Length; $index++) {
        $char = $text.Substring($index - 1, 1)
        $isMatch = if ($Kind -eq "CJK") {
          Test-CjkCharacter -Char $char
        } else {
          Test-LatinCharacter -Char $char
        }

        if ($isMatch) {
          $font = ""
          try {
            $font = [string]$cell.Characters($index, 1).Font.Name
          } catch {
            $font = [string]$cell.Font.Name
          }

          return [PSCustomObject]@{
            Found = $true
            Cell = $cell.Address($false, $false)
            Character = $char
            Font = $font
          }
        }
      }
    }
  }

  return [PSCustomObject]@{
    Found = $false
    Cell = ""
    Character = ""
    Font = ""
  }
}

function Test-CjkFontName {
  param(
    [string]$Actual,
    [string]$Expected
  )

  if ([string]::IsNullOrWhiteSpace($Actual)) {
    return $false
  }

  $accepted = @($Expected, "Microsoft JhengHei")
  return ($accepted | Where-Object { $_ -and $Actual.Trim().Equals($_, [System.StringComparison]::OrdinalIgnoreCase) }).Count -gt 0
}

function Test-LatinFontName {
  param(
    [string]$Actual,
    [string]$Expected
  )

  return (-not [string]::IsNullOrWhiteSpace($Actual) -and $Actual.Trim().Equals($Expected, [System.StringComparison]::OrdinalIgnoreCase))
}

if ($Sheets -and $Sheets.Count -gt 0 -and $AllSheets) {
  throw "Use either -Sheets or -AllSheets, not both."
}

if ($VisibleColumnLimit -lt 1 -or $VisibleColumnLimit -gt 52) {
  throw "VisibleColumnLimit must be between 1 and 52."
}

$resolved = Resolve-Path -LiteralPath $Path
$excel = New-Object -ComObject Excel.Application
$excel.Visible = [bool]$Visible
$excel.DisplayAlerts = $false
$workbook = $null

try {
  $workbook = $excel.Workbooks.Open($resolved.Path)

  $targetSheets = New-Object System.Collections.Generic.List[object]
  if ($Sheets -and $Sheets.Count -gt 0) {
    foreach ($sheetName in $Sheets) {
      [void]$targetSheets.Add($workbook.Worksheets.Item($sheetName))
    }
  } elseif ($AllSheets) {
    foreach ($worksheet in $workbook.Worksheets) {
      [void]$targetSheets.Add($worksheet)
    }
  } else {
    foreach ($worksheet in $workbook.Worksheets) {
      if (Test-ApiDetailSheet -Worksheet $worksheet) {
        [void]$targetSheets.Add($worksheet)
      }
    }
  }

  if ($targetSheets.Count -eq 0) {
    throw "No target worksheets found. Pass -Sheets for explicit targets or -AllSheets for full-workbook repair."
  }

  $results = @()
  foreach ($worksheet in $targetSheets) {
    $lastContentRow = Get-LastContentRow -Worksheet $worksheet -MaxColumn $VisibleColumnLimit
    if ($lastContentRow -le 0) {
      $results += [PSCustomObject]@{
        Sheet = [string]$worksheet.Name
        Scope = ""
        Status = "SKIPPED_EMPTY"
        CjkStatus = "NO_SAMPLE"
        LatinStatus = "NO_SAMPLE"
      }
      continue
    }

    $range = $worksheet.Range($worksheet.Cells.Item(1, 1), $worksheet.Cells.Item($lastContentRow, $VisibleColumnLimit))

    # Mimic manual Excel operation:
    # 1) set selected text to Microsoft JhengHei so CJK has the desired Far East font;
    # 2) set Latin/script font to Times New Roman. Excel keeps CJK rendered by the Far East font.
    Set-FontProperty -Font $range.Font -Property "Name" -Value $EastAsianFont
    Set-FontProperty -Font $range.Font -Property "NameFarEast" -Value $EastAsianFont
    Set-FontProperty -Font $range.Font -Property "NameAscii" -Value $LatinFont
    Set-FontProperty -Font $range.Font -Property "NameOther" -Value $LatinFont
    Set-FontProperty -Font $range.Font -Property "Name" -Value $LatinFont

    $cjkSample = Get-CharacterFontSample -Range $range -Kind "CJK"
    $latinSample = Get-CharacterFontSample -Range $range -Kind "LATIN"
    $cjkStatus = if (-not $cjkSample.Found) {
      "NO_SAMPLE"
    } elseif (Test-CjkFontName -Actual $cjkSample.Font -Expected $EastAsianFont) {
      "PASS"
    } else {
      "VISIBLE_FONT_FAIL"
    }

    $latinStatus = if (-not $latinSample.Found) {
      "NO_SAMPLE"
    } elseif (Test-LatinFontName -Actual $latinSample.Font -Expected $LatinFont) {
      "PASS"
    } else {
      "VISIBLE_FONT_FAIL"
    }

    $results += [PSCustomObject]@{
      Sheet = [string]$worksheet.Name
      Scope = $range.Address($false, $false)
      Status = "APPLIED"
      CjkStatus = $cjkStatus
      CjkCell = $cjkSample.Cell
      CjkFont = $cjkSample.Font
      LatinStatus = $latinStatus
      LatinCell = $latinSample.Cell
      LatinFont = $latinSample.Font
    }
  }

  $workbook.Save()
  $workbook.Close($true)
  Write-Output "APPLIED_FONT_SCHEME path=$($resolved.Path) targetSheets=$($targetSheets.Count) visibleColumns=A:G"
  $results | ConvertTo-Json -Depth 4
} finally {
  if ($workbook) {
    try { $workbook.Close($false) } catch {}
  }
  $excel.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
}
