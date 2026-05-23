param(
  [Parameter(Mandatory = $true)]
  [string]$VsdxPath,

  [int]$MinTopLevelShapes = 2,

  [switch]$AllowNoConnects,

  [switch]$AllowMissingTheme
)

$ErrorActionPreference = 'Stop'

function Resolve-FullPath([string]$Path) {
  $executionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Path)
}

function Get-ShapeTextSafe($Shape) {
  try { return ([string]$Shape.Text).Trim() } catch { return '' }
}

function Get-ShapeTreeTextSafe($Shape) {
  $parts = @()
  $ownText = Get-ShapeTextSafe $Shape
  if (-not [string]::IsNullOrWhiteSpace($ownText)) { $parts += $ownText }
  try {
    foreach ($child in @($Shape.Shapes)) {
      $childText = Get-ShapeTreeTextSafe $child
      if (-not [string]::IsNullOrWhiteSpace($childText)) { $parts += $childText }
    }
  } catch { }
  return ($parts -join "`n").Trim()
}

function Get-ShapeMasterNameSafe($Shape) {
  try { return [string]$Shape.Master.NameU } catch { return '' }
}

function Get-CellFormulaSafe($Shape, [string]$CellName) {
  try { return ([string]$Shape.CellsU($CellName).FormulaU).Trim() } catch { return '' }
}

function Get-CellResultSafe($Shape, [string]$CellName) {
  try { return [double]$Shape.CellsU($CellName).ResultIU } catch { return $null }
}

function Get-ShapeBoundsSafe($Shape) {
  $pinX = Get-CellResultSafe $Shape 'PinX'
  $pinY = Get-CellResultSafe $Shape 'PinY'
  $width = Get-CellResultSafe $Shape 'Width'
  $height = Get-CellResultSafe $Shape 'Height'
  if ($null -eq $pinX -or $null -eq $pinY -or $null -eq $width -or $null -eq $height) { return $null }
  $halfWidth = [Math]::Abs([double]$width) / 2.0
  $halfHeight = [Math]::Abs([double]$height) / 2.0
  return [pscustomobject]@{
    Left = [double]$pinX - $halfWidth
    Right = [double]$pinX + $halfWidth
    Top = [double]$pinY + $halfHeight
    Bottom = [double]$pinY - $halfHeight
  }
}

$script:NativeConnectionPointUnit = 0.25

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
    $candidateMaster = Get-ShapeMasterNameSafe $candidate
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

function Test-OnNativeConnectionGrid([double]$Value, [double]$Tolerance = 0.035) {
  $unit = Get-NativeConnectionPointUnit
  if ($unit -le 0) { return $true }
  $nearest = [Math]::Round(($Value / $unit), 0, [MidpointRounding]::AwayFromZero) * $unit
  return ([Math]::Abs($Value - $nearest) -le $Tolerance)
}

function Test-HorizontalSpansOverlap([double]$LeftA, [double]$RightA, [double]$LeftB, [double]$RightB, [double]$Padding = 0.0) {
  $aLeft = [Math]::Min($LeftA, $RightA)
  $aRight = [Math]::Max($LeftA, $RightA)
  $bLeft = [Math]::Min($LeftB, $RightB) - $Padding
  $bRight = [Math]::Max($LeftB, $RightB) + $Padding
  return ($aRight -ge $bLeft -and $aLeft -le $bRight)
}

function Measure-NativeLabelWidth([string]$Text, [double]$MinWidth = 1.0, [double]$MaxWidth = 3.2) {
  $width = 0.24
  foreach ($char in $Text.ToCharArray()) {
    if ([int][char]$char -gt 255) {
      $width += 0.20
    }
    else {
      $width += 0.085
    }
  }
  return [Math]::Min([Math]::Max($MinWidth, $width), $MaxWidth)
}

function Test-BoundsInsideBoundsSafe($Inner, $Outer, [double]$Tolerance = 0.03) {
  if ($null -eq $Inner -or $null -eq $Outer) { return $false }
  return (
    [double]$Inner.Left -ge ([double]$Outer.Left - $Tolerance) -and
    [double]$Inner.Right -le ([double]$Outer.Right + $Tolerance) -and
    [double]$Inner.Top -le ([double]$Outer.Top + $Tolerance) -and
    [double]$Inner.Bottom -ge ([double]$Outer.Bottom - $Tolerance)
  )
}

function Test-BoundsCenterInsideBoundsSafe($Inner, $Outer, [double]$Inset = 0.02) {
  if ($null -eq $Inner -or $null -eq $Outer) { return $false }
  $centerX = ([double]$Inner.Left + [double]$Inner.Right) / 2.0
  $centerY = ([double]$Inner.Top + [double]$Inner.Bottom) / 2.0
  return (
    $centerX -ge ([double]$Outer.Left + $Inset) -and
    $centerX -le ([double]$Outer.Right - $Inset) -and
    $centerY -ge ([double]$Outer.Bottom + $Inset) -and
    $centerY -le ([double]$Outer.Top - $Inset)
  )
}

function Test-MessageArrowTooCloseToVisualBounds($BeginX, $EndX, $BeginY, $EndY, $Bounds, [double]$RequiredGap) {
  if ($null -eq $BeginX -or $null -eq $EndX -or $null -eq $BeginY -or $null -eq $EndY -or $null -eq $Bounds) { return $false }
  $messageLeft = [Math]::Min([double]$BeginX, [double]$EndX)
  $messageRight = [Math]::Max([double]$BeginX, [double]$EndX)
  if (-not (Test-HorizontalSpansOverlap $messageLeft $messageRight ([double]$Bounds.Left) ([double]$Bounds.Right) 0.02)) { return $false }
  $messageYMin = [Math]::Min([double]$BeginY, [double]$EndY)
  $messageYMax = [Math]::Max([double]$BeginY, [double]$EndY)
  foreach ($edgeY in @([double]$Bounds.Top, [double]$Bounds.Bottom)) {
    if ($edgeY -gt ($messageYMin - $RequiredGap) -and $edgeY -lt ($messageYMax + $RequiredGap)) { return $true }
  }
  return $false
}

function Test-NativeFragmentFrameShapeSafe([string]$MasterName) {
  return ($MasterName -match '(?i)(Alternative fragment|Optional fragment|Loop fragment|Other fragment)')
}

function Get-ShapeGeometryExtentsSafe($Shape) {
  try {
    $rowCount = [int]$Shape.RowCount(10)
    if ($rowCount -le 0) { return $null }
    $maxX = $null
    $maxY = $null
    for ($row = 0; $row -lt $rowCount; $row++) {
      try {
        $x = [double]$Shape.CellsSRC(10, $row, 0).ResultIU
        if ($null -eq $maxX -or $x -gt $maxX) { $maxX = $x }
      } catch { }
      try {
        $y = [double]$Shape.CellsSRC(10, $row, 1).ResultIU
        if ($null -eq $maxY -or $y -gt $maxY) { $maxY = $y }
      } catch { }
    }
    if ($null -eq $maxX -or $null -eq $maxY) { return $null }
    return [pscustomobject]@{
      MaxX = [double]$maxX
      MaxY = [double]$maxY
    }
  } catch {
    return $null
  }
}

function Get-NativeFragmentTitleChildSafe($Shape) {
  $fallback = $null
  try {
    foreach ($child in @($Shape.Shapes)) {
      $childText = Get-ShapeTextSafe $child
      if ($childText -match '^(alt|opt|ref|loop)$') { return $child }
      if ($null -eq $fallback -and -not [string]::IsNullOrWhiteSpace($childText) -and $childText -notmatch '^\[[^\]]+\]$') {
        $fallback = $child
      }
    }
  } catch { }
  return $fallback
}

function Test-FormulaIsOne([string]$Formula) {
  if ([string]::IsNullOrWhiteSpace($Formula)) { return $false }
  return ($Formula.Trim() -match '(?i)^(1|TRUE|GUARD\(1\))$')
}

function Get-SectionDividerPartKind($Shape, [string]$Text, [string]$MasterName) {
  if (-not [string]::IsNullOrWhiteSpace($MasterName)) { return '' }
  $width = Get-CellResultSafe $Shape 'Width'
  $height = Get-CellResultSafe $Shape 'Height'
  if ($null -eq $width -or $null -eq $height) { return '' }
  $lineColor = Get-CellFormulaSafe $Shape 'LineColor'
  $hasDividerGreen = ($lineColor -match '(?i)RGB\(30\s*,\s*80\s*,\s*84\)')
  if (-not $hasDividerGreen) { return '' }
  if ([string]::IsNullOrWhiteSpace($Text) -and $width -gt 6.0 -and $height -lt 0.08) { return 'line' }
  if (-not [string]::IsNullOrWhiteSpace($Text) -and $width -gt 0.5 -and $height -le 0.65) {
    if ($Text -notmatch '^\[[^\]]+\]$' -and $Text -notin @('alt', 'opt', 'ref', 'loop')) { return 'title' }
  }
  return ''
}

function Get-ContainerMemberIdsSafe($Shape) {
  try { return @($Shape.ContainerProperties.GetMemberShapes(1)) } catch { return @() }
}

function Get-ContainerListMemberIdsSafe($Shape) {
  try { return @($Shape.ContainerProperties.GetListMembers()) } catch { return @() }
}

function Test-ShapeIsMemberOfMasterName($Page, $MemberShape, [string]$MasterNamePattern) {
  $memberId = $null
  try { $memberId = [int]$MemberShape.ID } catch { return $false }
  foreach ($candidate in @($Page.Shapes)) {
    $candidateMaster = Get-ShapeMasterNameSafe $candidate
    if ($candidateMaster -notmatch $MasterNamePattern) { continue }
    foreach ($id in (Get-ContainerMemberIdsSafe $candidate)) {
      try {
        if ([int]$id -eq $memberId) { return $true }
      } catch { }
    }
  }
  return $false
}

function Test-ShapeTreeHasBracketConditionText($Shape) {
  if ((Get-ShapeTextSafe $Shape) -match '\[[^\]]+\]') { return $true }
  try {
    foreach ($child in @($Shape.Shapes)) {
      if (Test-ShapeTreeHasBracketConditionText $child) { return $true }
    }
  } catch { }
  return $false
}

function Test-ShapeTextColorIsBlack($Shape) {
  $formulas = @()
  try { $formulas += [string]$Shape.CellsU('Char.Color').FormulaU } catch { }
  try {
    $charRows = $Shape.RowCount(3)
    for ($row = 0; $row -lt $charRows; $row++) {
      try { $formulas += [string]$Shape.CellsSRC(3, $row, 1).FormulaU } catch { }
    }
  } catch { }
  $formulas = @($formulas | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_) } | Select-Object -Unique)
  if ($formulas.Count -eq 0) { return $false }
  foreach ($formula in $formulas) {
    if ($formula -notmatch '(?i)^(RGB\(0,0,0\)|0)$') { return $false }
  }
  return $true
}

function Test-FragmentHasNativeConditionMember($Page, $FrameShape) {
  if (Test-ShapeTreeHasBracketConditionText $FrameShape) { return $true }
  foreach ($id in (Get-ContainerMemberIdsSafe $FrameShape)) {
    try {
      $member = $Page.Shapes.ItemFromID([int]$id)
      if ((Get-ShapeMasterNameSafe $member) -like 'Interaction operand*' -and (Get-ShapeTextSafe $member) -match '^\[[^\]]+\]') {
        return $true
      }
    } catch { }
  }
  return $false
}

function Test-MessageIntersectsRefBounds($Shape, $RefBounds) {
  $beginX = Get-CellResultSafe $Shape 'BeginX'
  $endX = Get-CellResultSafe $Shape 'EndX'
  $beginY = Get-CellResultSafe $Shape 'BeginY'
  $endY = Get-CellResultSafe $Shape 'EndY'
  if ($null -eq $beginX -or $null -eq $endX -or $null -eq $beginY -or $null -eq $endY) { return $false }
  $xMin = [Math]::Min([double]$beginX, [double]$endX)
  $xMax = [Math]::Max([double]$beginX, [double]$endX)
  $yMin = [Math]::Min([double]$beginY, [double]$endY)
  $yMax = [Math]::Max([double]$beginY, [double]$endY)
  $tol = 0.02
  $overlapsX = ($xMax -ge ([double]$RefBounds.Left - $tol) -and $xMin -le ([double]$RefBounds.Right + $tol))
  $overlapsY = ($yMax -ge ([double]$RefBounds.Bottom - $tol) -and $yMin -le ([double]$RefBounds.Top + $tol))
  return ($overlapsX -and $overlapsY)
}

function Test-CommonMethodMessageText([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match '(?m)^\s*(CommonFunc|CommonUtil)[/.][A-Za-z0-9_]+')
}

function Test-CommonFuncSlashNotation([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match '(?m)^\s*CommonFunc/[A-Za-z0-9_]+')
}

function Test-CommonUtilDotNotation([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return $false }
  return ($Text -match '(?m)^\s*CommonUtil\.[A-Za-z0-9_]+')
}

function Get-CommonMethodNameFromText([string]$Text) {
  if ([string]::IsNullOrWhiteSpace($Text)) { return '' }
  $match = [regex]::Match($Text, '(?m)^\s*(CommonFunc|CommonUtil)[/.]([A-Za-z0-9_]+)')
  if ($match.Success) { return $match.Groups[2].Value }
  return ''
}

function Test-AllowedRefSelfMessage($Shape, $RefBounds, [string]$Text, [string]$MasterName) {
  if ($MasterName -notmatch '^Self Message') { return $false }
  if (-not (Test-CommonMethodMessageText $Text)) { return $false }
  $beginX = Get-CellResultSafe $Shape 'BeginX'
  $endX = Get-CellResultSafe $Shape 'EndX'
  $beginY = Get-CellResultSafe $Shape 'BeginY'
  $endY = Get-CellResultSafe $Shape 'EndY'
  if ($null -eq $beginX -or $null -eq $endX -or $null -eq $beginY -or $null -eq $endY) { return $false }
  $tol = 0.05
  $xMin = [Math]::Min([double]$beginX, [double]$endX)
  $xMax = [Math]::Max([double]$beginX, [double]$endX)
  $yMin = [Math]::Min([double]$beginY, [double]$endY)
  $yMax = [Math]::Max([double]$beginY, [double]$endY)
  return (
    $xMin -ge ([double]$RefBounds.Left - $tol) -and
    $xMax -le ([double]$RefBounds.Right + $tol) -and
    $yMin -ge ([double]$RefBounds.Bottom - $tol) -and
    $yMax -le ([double]$RefBounds.Top + $tol)
  )
}

function Test-HorizontalBoundsOverlap($A, $B, [double]$MinRatio = 0.25) {
  if ($null -eq $A -or $null -eq $B) { return $false }
  $aWidth = [Math]::Max(0.01, [double]$A.Right - [double]$A.Left)
  $bWidth = [Math]::Max(0.01, [double]$B.Right - [double]$B.Left)
  $overlap = [Math]::Min([double]$A.Right, [double]$B.Right) - [Math]::Max([double]$A.Left, [double]$B.Left)
  return ($overlap -ge ([Math]::Min($aWidth, $bWidth) * $MinRatio))
}

function New-UnicodeText([int[]]$CodePoints) {
  return -join ($CodePoints | ForEach-Object { [char]$_ })
}

function Test-TextContainsAnyTerm([string]$Text, [string[]]$Terms) {
  foreach ($term in @($Terms)) {
    if (-not [string]::IsNullOrWhiteSpace($term) -and $Text.Contains($term)) { return $true }
  }
  return $false
}

$script:SuccessLikeOperandTerms = @(
  (New-UnicodeText @(0x7B26, 0x5408)),
  (New-UnicodeText @(0x901A, 0x904E)),
  (New-UnicodeText @(0x6210, 0x529F)),
  (New-UnicodeText @(0x6709, 0x6548)),
  (New-UnicodeText @(0x6709, 0x8CC7, 0x6599)),
  (New-UnicodeText @(0x53EF, 0x4F7F, 0x7528)),
  (New-UnicodeText @(0x6B63, 0x5E38)),
  (New-UnicodeText @(0x5DF2, 0x5B8C, 0x6210))
)
$script:IrisInterestTargetTerms = @(
  (New-UnicodeText @(0x7D44, 0x88DD, 0x7D2F, 0x8A08, 0x4E2D, 0x5229, 0x606F)),
  (New-UnicodeText @(0x986F, 0x793A, 0x7D2F, 0x8A08, 0x4E2D, 0x5229, 0x606F))
)
$script:IrisInterestResponseTerms = @(
  (New-UnicodeText @(0x7121, 0x8A08, 0x606F, 0x8CC7, 0x6599)),
  (New-UnicodeText @(0x8A08, 0x606F, 0x8CC7, 0x6599))
)
$script:IrisInterestSystemAbnormalTerm = New-UnicodeText @(0x7CFB, 0x7D71, 0x7570, 0x5E38)
$script:InterestDetailPageTerm = New-UnicodeText @(0x8A08, 0x606F, 0x660E, 0x7D30)
$script:IrisInterestQueryGroupTerm = New-UnicodeText @(0x67E5, 0x8A62, 0x8A08, 0x606F, 0x8CC7, 0x6599)

function Test-SuccessLikeOperandText([string]$Text) {
  return (Test-TextContainsAnyTerm $Text $script:SuccessLikeOperandTerms)
}

function Test-SignificantBranchContentShape([string]$MasterName, [string]$Text) {
  if ($MasterName -match '(?i)^Interaction operand') { return $false }
  if ($MasterName -match '(?i)^(Actor lifeline|Object lifeline)') { return $false }
  if ($Text -in @('User', 'APP', 'Enterprise', 'IRIS', 'DB', 'Redis')) { return $false }
  if ($MasterName -match '(?i)^(Message|Self Message|Return Message)') { return $true }
  if (Test-NativeFragmentFrameShapeSafe $MasterName) { return $true }
  return $false
}

$full = Resolve-FullPath $VsdxPath
if (-not (Test-Path -LiteralPath $full)) {
  throw "VSDX not found: $full"
}

$errors = New-Object System.Collections.Generic.List[string]
$mediaCount = 0
$embeddingCount = 0
$foreignDataXmlCount = 0
$shapeCount = 0
$connectCount = 0
$masterNames = @()
$hasTheme = $false
$hasThemeRelationship = $false
$altFragmentCount = 0
$altFragmentsWithoutMembers = 0
$altFragmentsMissingOperandListMembers = 0
$altFragmentsMissingNativeOperandList = 0
$altNativeOperandListMembers = 0
$altFragmentsWithMemberOverflow = 0
$altSuccessBranchContentOutsideFrame = 0
$altFragmentsMissingResizeControl = 0
$optFragmentCount = 0
$optFragmentsWithoutMembers = 0
$optFragmentsMissingCondition = 0
$plainConditionLabelCount = 0
$conditionOperandCount = 0
$conditionOperandsWithoutBrackets = 0
$conditionOperandsWithoutResizeBinding = 0
$conditionOperandTextMisaligned = 0
$altOperandVerticalFormulaLock = 0
$diagonalDashedPathCount = 0
$manualFragmentOverlayCount = 0
$refFragmentCount = 0
$refFragmentsNotSixConnectionPoints = 0
$messagesInsideRefFragments = 0
$allowedRefSelfMessages = 0
$refDisplayNamesWithSvgExtension = 0
$refDisplayNamesMissingChineseDescription = 0
$refDisplayNamesMissingPointerPrefix = 0
$commonRefSelfMessagesWithoutPointer = 0
$commonFuncSlashNotation = 0
$commonUtilDotNotation = 0
$allowedRefSelfMessageMethods = @()
$refPointerDisplayMethods = @()
$fragmentEdgesOffConnectionGrid = 0
$fragmentSideClearanceTooTight = 0
$childFragmentParentSpacingTooSmall = 0
$fragmentSiblingOverlaps = 0
$fragmentFrameGeometryMismatch = 0
$fragmentTitleMisaligned = 0
$emptyGroupFragmentCount = 0
$sectionFragmentSpacingTooSmall = 0
$participantNativeCount = 0
$participantNonNativeCount = 0
$participantLifelinesWithExtraConnectionPoints = 0
$participantLifelinesWithSparseConnectionPoints = 0
$participantLifelinesWithNonUniformConnectionPointGap = 0
$textBearingMessageCount = 0
$messagesWithoutConnectorGlue = 0
$messageArrowsOffConnectionGrid = 0
$commonMethodMessagesOutsideRef = 0
$messageArrowGapsTooSmall = 0
$selfMessageDoubleSpacingViolations = 0
$messageArrowsTooCloseToOtherShapes = 0
$messagesCrossingAltOperandSeparators = 0
$messageLabelsNotAboveArrow = 0
$messageLabelsNotBlack = 0
$selfMessagesWithoutTextControl = 0
$selfMessagesWithCenteredText = 0
$selfMessagesNotOneConnectionPoint = 0
$objectLifelineCount = 0
$objectLifelinesWithSparseConnectionPoints = 0
$objectLifelinesWithClusteredConnectionPoints = 0
$minObjectLifelineConnectionPointGap = $null
$pageDrawingResizeType = ''
$pageResizePage = ''
$sectionDividerPartCount = 0
$sectionDividerPartsUnlocked = 0
$sectionDividerTitleBoxCount = 0
$sectionDividerTitleBoxesLockedForResize = 0
$sectionDividerTitleBoxesTooNarrow = 0
$irisInterestJudgmentContentOutsideAlt = 0
$irisInterestJudgmentAltOutsideQueryGroup = 0
$messageArrowRows = @()
$spacingDebugRows = @()

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = $null
try {
  $zip = [System.IO.Compression.ZipFile]::OpenRead($full)
  foreach ($entry in $zip.Entries) {
    $name = $entry.FullName -replace '\\', '/'
    if ($name -like 'visio/media/*') { $mediaCount++ }
    if ($name -like 'visio/embeddings/*') { $embeddingCount++ }
    if ($name -eq 'visio/theme/theme1.xml') { $hasTheme = $true }
    if ($name -like 'visio/*.xml' -or $name -like 'visio/*/*.xml' -or $name -eq 'visio/_rels/document.xml.rels') {
      $reader = $null
      try {
        $reader = New-Object System.IO.StreamReader($entry.Open())
        $text = $reader.ReadToEnd()
        if ($text -match '<ForeignData\b|ForeignData') { $foreignDataXmlCount++ }
        if ($name -eq 'visio/_rels/document.xml.rels' -and $text -match 'officeDocument/2006/relationships/theme') {
          $hasThemeRelationship = $true
        }
      }
      finally {
        if ($reader -ne $null) { $reader.Close() }
      }
    }
    $visualProbePath = Join-Path ([System.IO.Path]::GetTempPath()) ("native-visio-diagonal-probe-{0}-{1}.svg" -f ([System.Guid]::NewGuid().ToString('N')), $pageInspectIndex)
    try {
      $page.Export($visualProbePath) | Out-Null
      $svgText = Get-Content -Raw -Encoding UTF8 -LiteralPath $visualProbePath
      $dashedClasses = @{}
      foreach ($styleMatch in [regex]::Matches($svgText, '\.(st\d+)\s*\{[^}]*stroke-dasharray[^}]*\}')) {
        $dashedClasses[[string]$styleMatch.Groups[1].Value] = $true
      }
      foreach ($pathMatch in [regex]::Matches($svgText, '<path d="M\s*([0-9.\-]+)\s+([0-9.\-]+)\s+L\s*([0-9.\-]+)\s+([0-9.\-]+)[^"]*"\s+class="(st\d+)"')) {
        $className = [string]$pathMatch.Groups[5].Value
        if (-not $dashedClasses.ContainsKey($className)) { continue }
        $x1 = [double]::Parse([string]$pathMatch.Groups[1].Value, [Globalization.CultureInfo]::InvariantCulture)
        $y1 = [double]::Parse([string]$pathMatch.Groups[2].Value, [Globalization.CultureInfo]::InvariantCulture)
        $x2 = [double]::Parse([string]$pathMatch.Groups[3].Value, [Globalization.CultureInfo]::InvariantCulture)
        $y2 = [double]::Parse([string]$pathMatch.Groups[4].Value, [Globalization.CultureInfo]::InvariantCulture)
        if ([Math]::Abs($x1 - $x2) -gt 5.0 -and [Math]::Abs($y1 - $y2) -gt 5.0) {
          $diagonalDashedPathCount++
        }
      }
    }
    catch { }
    finally {
      Remove-Item -LiteralPath $visualProbePath -Force -ErrorAction SilentlyContinue
    }
  }
}
finally {
  if ($zip -ne $null) { $zip.Dispose() }
}

if ($mediaCount -gt 0) { $errors.Add("visio/media entries detected: $mediaCount") }
if ($embeddingCount -gt 0) { $errors.Add("visio/embeddings entries detected: $embeddingCount") }
if ($foreignDataXmlCount -gt 0) { $errors.Add("ForeignData detected in Visio XML entries: $foreignDataXmlCount") }
if (-not $AllowMissingTheme -and (-not $hasTheme -or -not $hasThemeRelationship)) {
  $errors.Add("project Visio theme is missing; expected visio/theme/theme1.xml and a document theme relationship so UML THEMEVAL colors match the project template")
}

$visio = $null
$doc = $null
try {
  $visio = New-Object -ComObject Visio.Application
  $visio.Visible = $false
  $visio.AlertResponse = 7
  $doc = $visio.Documents.OpenEx($full, 128)
  $page = $doc.Pages.Item(1)
  $shapeCount = $page.Shapes.Count
  $connectCount = $page.Connects.Count
  $pageDrawingResizeType = Get-CellFormulaSafe $page.PageSheet 'DrawingResizeType'
  $pageResizePage = Get-CellFormulaSafe $page.PageSheet 'ResizePage'
  foreach ($master in @($doc.Masters)) {
    try { $masterNames += [string]$master.NameU } catch { }
  }
  $pageInspectIndex = 0
  foreach ($pageToInspect in @($doc.Pages)) {
    $page = $pageToInspect
    $pageInspectIndex++
    $pageNameForChecks = ''
    try { $pageNameForChecks = [string]$page.Name } catch { }
    $pageIsInterestDetail = $pageNameForChecks.Contains($script:InterestDetailPageTerm)
    $pageHeightForChecks = Get-CellResultSafe $page.PageSheet 'PageHeight'
    Set-NativeConnectionPointUnit (Get-PageParticipantConnectionPointUnit $page)
    $pageParticipantXs = @()
    foreach ($participantShape in @($page.Shapes)) {
      $participantMaster = Get-ShapeMasterNameSafe $participantShape
      if ($participantMaster -match '(?i)^(Actor lifeline|Object lifeline)') {
        $participantX = Get-CellResultSafe $participantShape 'PinX'
        if ($null -ne $participantX) { $pageParticipantXs += [double]$participantX }
      }
    }
    $pageRefBounds = @()
    $pageAltOperandSeparatorYs = @()
    foreach ($refCandidate in @($page.Shapes)) {
      $refMasterName = Get-ShapeMasterNameSafe $refCandidate
      if (-not (Test-NativeFragmentFrameShapeSafe $refMasterName)) { continue }
      if ((Get-ShapeTextSafe $refCandidate) -ne 'ref') { continue }
      $refBounds = Get-ShapeBoundsSafe $refCandidate
      if ($null -ne $refBounds) { $pageRefBounds += $refBounds }
    }
    foreach ($operandCandidate in @($page.Shapes)) {
      $operandMasterName = Get-ShapeMasterNameSafe $operandCandidate
      if ($operandMasterName -notlike 'Interaction operand*') { continue }
      if ((Get-ShapeTextSafe $operandCandidate) -notmatch '^\[[^\]]+\]') { continue }
      $linePattern = Get-CellFormulaSafe $operandCandidate 'LinePattern'
      if ($linePattern -match '^(0|GUARD\(0\))$') { continue }
      $operandBounds = Get-ShapeBoundsSafe $operandCandidate
      if ($null -ne $operandBounds) { $pageAltOperandSeparatorYs += [double]$operandBounds.Top }
    }
    $pageMessageSpacingTargetBounds = @()
    $pageSectionDividerTitleRows = @()
    $pageFragmentFrameBounds = @()
    $pageAltFrameBounds = @()
    $pageIrisInterestJudgmentAltBounds = @()
    $pageIrisInterestQueryGroupBounds = @()
    $pageIrisInterestTargetBounds = @()
    $pageIrisEdMessageBounds = @()
    $pageHasIrisInterestEd0005 = $false
    $pageHasIrisInterestEd0009 = $false
    foreach ($targetCandidate in @($page.Shapes)) {
      $targetText = Get-ShapeTextSafe $targetCandidate
      $targetMasterName = Get-ShapeMasterNameSafe $targetCandidate
      $targetName = ''
      try { $targetName = [string]$targetCandidate.NameU } catch { }
      if ($targetMasterName -match '^(Message|Self Message|Return Message|Actor lifeline|Object lifeline|Activation)') { continue }
      $targetSectionKind = Get-SectionDividerPartKind $targetCandidate $targetText $targetMasterName
      $isSpacingTarget = $false
      if (Test-NativeFragmentFrameShapeSafe $targetMasterName) { $isSpacingTarget = $true }
      elseif ($targetMasterName -like 'Interaction operand*') { $isSpacingTarget = $true }
      elseif ($targetSectionKind -in @('line', 'title')) { $isSpacingTarget = $true }
      elseif ($targetMasterName -match '^(Note|Rounded Rectangle)') { $isSpacingTarget = $true }
      elseif ($targetName -match '(?i)(orange|pointer|section|title|group|ref|alt|note)') { $isSpacingTarget = $true }
      if (-not $isSpacingTarget) { continue }
      $targetBounds = Get-ShapeBoundsSafe $targetCandidate
      if ($null -eq $targetBounds) { continue }
      $targetId = $null
      try { $targetId = [int]$targetCandidate.ID } catch { }
      $pageMessageSpacingTargetBounds += [pscustomobject]@{
        Id = $targetId
        Bounds = $targetBounds
        Text = $targetText
        MasterName = $targetMasterName
        Name = $targetName
      }
    }
    foreach ($shape in @($page.Shapes)) {
    try {
      $text = Get-ShapeTextSafe $shape
      $masterName = Get-ShapeMasterNameSafe $shape
      $shapeName = ''
      try { $shapeName = [string]$shape.NameU } catch { }
      $treeText = $text
      if ($masterName -match '(?i)^Other fragment') { $treeText = Get-ShapeTreeTextSafe $shape }
      if ($pageIsInterestDetail -and $masterName -match '(?i)^Other fragment' -and $treeText.Contains($script:IrisInterestQueryGroupTerm)) {
        $queryGroupBounds = Get-ShapeBoundsSafe $shape
        if ($null -ne $queryGroupBounds) { $pageIrisInterestQueryGroupBounds += $queryGroupBounds }
      }
      $isIrisInterestTargetText = ($text -match 'IRIS\.ED0005|IRIS\.ED0009|CommonFunc/GetCENCurrFunc|Response 9001') -or (Test-TextContainsAnyTerm $text $script:IrisInterestTargetTerms)
      if (-not $isIrisInterestTargetText -and $text -match '^Response\b') {
        $isIrisInterestTargetText = Test-TextContainsAnyTerm $text $script:IrisInterestResponseTerms
      }
      if ($text -match 'IRIS\.ED0005|IRIS\.ED0009') {
        if ($text -match 'IRIS\.ED0005') { $pageHasIrisInterestEd0005 = $true }
        if ($text -match 'IRIS\.ED0009') { $pageHasIrisInterestEd0009 = $true }
        $irisEdBounds = Get-ShapeBoundsSafe $shape
        if ($null -ne $irisEdBounds) { $pageIrisEdMessageBounds += $irisEdBounds }
      }
      if ($isIrisInterestTargetText -and $masterName -match '^(Message|Self Message|Return Message)') {
        $irisTargetBounds = Get-ShapeBoundsSafe $shape
        if ($null -ne $irisTargetBounds) { $pageIrisInterestTargetBounds += $irisTargetBounds }
      }
      if ($shapeName -match '^(manual-alt|manual-ref)-') {
        $manualFragmentOverlayCount++
      }
      if (Test-CommonFuncSlashNotation $text) {
        $commonFuncSlashNotation++
      }
      if (Test-CommonUtilDotNotation $text) {
        $commonUtilDotNotation++
      }
      if ($text -match '\d+_(?:CommonFunc|CommonUtil)\.') {
        if ($text -match '(?i)\.svg\b') {
          $refDisplayNamesWithSvgExtension++
        }
        if ($text -notmatch '循序圖請參考[:：]') {
          $refDisplayNamesMissingPointerPrefix++
        }
        $compactRefText = $text -replace '\s+', ''
        if ($compactRefText -notmatch '\d+_(?:CommonFunc|CommonUtil)\.[A-Za-z0-9_]+[一-龥]') {
          $refDisplayNamesMissingChineseDescription++
        }
        $pointerMethodMatch = [regex]::Match($compactRefText, '\d+_(?:CommonFunc|CommonUtil)\.([A-Za-z0-9_]+).*?[一-龥]')
        if ($pointerMethodMatch.Success) {
          $refPointerDisplayMethods += [pscustomobject]@{
            PageIndex = $pageInspectIndex
            Method = $pointerMethodMatch.Groups[1].Value
          }
        }
      }
      if (Test-NativeFragmentFrameShapeSafe $masterName) {
        $fragmentBounds = Get-ShapeBoundsSafe $shape
        if ($null -ne $fragmentBounds -and $null -ne $pageHeightForChecks) {
          $fragmentShapeId = $null
          try { $fragmentShapeId = [int]$shape.ID } catch { }
          $fragmentWidth = Get-CellResultSafe $shape 'Width'
          $fragmentHeight = Get-CellResultSafe $shape 'Height'
          $geometryExtents = Get-ShapeGeometryExtentsSafe $shape
          if ($null -ne $fragmentWidth -and $null -ne $fragmentHeight -and $null -ne $geometryExtents) {
            if (
              [double]$geometryExtents.MaxX -lt ([double]$fragmentWidth - 0.04) -or
              [double]$geometryExtents.MaxY -lt ([double]$fragmentHeight - 0.04)
            ) {
              $fragmentFrameGeometryMismatch++
            }
          }
          $titleChild = Get-NativeFragmentTitleChildSafe $shape
          if ($null -ne $titleChild -and $null -ne $fragmentWidth -and $null -ne $fragmentHeight) {
            $titlePinX = Get-CellResultSafe $titleChild 'PinX'
            $titlePinY = Get-CellResultSafe $titleChild 'PinY'
            $titleWidth = Get-CellResultSafe $titleChild 'Width'
            $titleLocPinX = Get-CellResultSafe $titleChild 'LocPinX'
            if (
              $null -ne $titlePinX -and
              $null -ne $titlePinY -and
              $null -ne $titleWidth -and
              $null -ne $titleLocPinX -and
              (
                [Math]::Abs([double]$titlePinY - [double]$fragmentHeight) -gt 0.04 -or
                [Math]::Abs([double]$titlePinX - ([double]$fragmentWidth / 2.0)) -gt 0.04 -or
                [double]$titleWidth -lt ([double]$fragmentWidth - 0.04) -or
                [Math]::Abs([double]$titleLocPinX - ([double]$fragmentWidth / 2.0)) -gt 0.04
              )
            ) {
              $fragmentTitleMisaligned++
            }
          }
          $pageFragmentFrameBounds += [pscustomobject]@{
            Id = $fragmentShapeId
            Bounds = $fragmentBounds
            Text = if ([string]::IsNullOrWhiteSpace($text)) { $treeText } else { $text }
            MasterName = $masterName
          }
          $topDistance = [double]$pageHeightForChecks - [double]$fragmentBounds.Top
          $bottomDistance = [double]$pageHeightForChecks - [double]$fragmentBounds.Bottom
          $bottomDistanceForGrid = $bottomDistance
          $bottomOnGrid = Test-OnNativeConnectionGrid $bottomDistance
          if ($text -eq 'alt' -and $masterName -like 'Alternative fragment*' -and @(Get-ContainerListMemberIdsSafe $shape).Count -gt 0) {
            $bottomDistanceForGrid = $bottomDistance + 0.08
            $bottomOnGrid = $bottomOnGrid -or (Test-OnNativeConnectionGrid $bottomDistanceForGrid 0.12)
          }
          if (-not (Test-OnNativeConnectionGrid $topDistance) -or -not $bottomOnGrid) {
            $fragmentEdgesOffConnectionGrid++
          }
          foreach ($participantX in $pageParticipantXs) {
            if ($participantX -lt [double]$fragmentBounds.Left -or $participantX -gt [double]$fragmentBounds.Right) { continue }
            if (([double]$participantX - [double]$fragmentBounds.Left) -lt 0.30 -or ([double]$fragmentBounds.Right - [double]$participantX) -lt 0.30) {
              $fragmentSideClearanceTooTight++
              break
            }
          }
          if ($text -eq 'ref') {
            $refFragmentCount++
            $expectedRefHeight = (Get-NativeConnectionPointUnit) * 6.0
            $actualRefHeight = [double]$fragmentBounds.Top - [double]$fragmentBounds.Bottom
            if ([Math]::Abs($actualRefHeight - $expectedRefHeight) -gt 0.04) {
              $refFragmentsNotSixConnectionPoints++
            }
          }
        }
      }
      $sectionDividerKind = Get-SectionDividerPartKind $shape $text $masterName
      if ($sectionDividerKind -eq 'line') {
        $sectionDividerPartCount++
        $lockWidth = Get-CellFormulaSafe $shape 'LockWidth'
        $lockHeight = Get-CellFormulaSafe $shape 'LockHeight'
        $lockCalcWH = Get-CellFormulaSafe $shape 'LockCalcWH'
        $lockAspect = Get-CellFormulaSafe $shape 'LockAspect'
        $lockMoveX = Get-CellFormulaSafe $shape 'LockMoveX'
        $lockMoveY = Get-CellFormulaSafe $shape 'LockMoveY'
        if (-not (Test-FormulaIsOne $lockWidth) -or
            -not (Test-FormulaIsOne $lockHeight) -or
            -not (Test-FormulaIsOne $lockCalcWH) -or
            -not (Test-FormulaIsOne $lockAspect) -or
            -not (Test-FormulaIsOne $lockMoveX) -or
            (Test-FormulaIsOne $lockMoveY)) {
          $sectionDividerPartsUnlocked++
        }
      }
      elseif ($sectionDividerKind -eq 'title') {
        $sectionDividerTitleBoxCount++
        $lockWidth = Get-CellFormulaSafe $shape 'LockWidth'
        $lockHeight = Get-CellFormulaSafe $shape 'LockHeight'
        $lockCalcWH = Get-CellFormulaSafe $shape 'LockCalcWH'
        if ((Test-FormulaIsOne $lockWidth) -or (Test-FormulaIsOne $lockHeight) -or (Test-FormulaIsOne $lockCalcWH)) {
          $sectionDividerTitleBoxesLockedForResize++
        }
        $titleWidth = Get-CellResultSafe $shape 'Width'
        if ($null -ne $titleWidth) {
          $requiredTitleWidth = Measure-NativeLabelWidth $text 1.0 3.2
          if ([double]$titleWidth -lt ([double]$requiredTitleWidth - 0.05)) {
            $sectionDividerTitleBoxesTooNarrow++
          }
        }
        $titleBounds = Get-ShapeBoundsSafe $shape
        if ($null -ne $titleBounds -and $null -ne $pageHeightForChecks) {
          $titleCenterY = (([double]$titleBounds.Top + [double]$titleBounds.Bottom) / 2.0)
          $pageSectionDividerTitleRows += [pscustomobject]@{
            Bounds = $titleBounds
            TopDistance = [double]$pageHeightForChecks - $titleCenterY
            Text = $text
          }
        }
      }
      if ($text -in @('User', 'APP', 'Enterprise', 'IRIS', 'DB', 'Redis')) {
        $expectedParticipantMaster = if ($text -eq 'User') { '^Actor lifeline' } else { '^Object lifeline' }
        if ($masterName -match $expectedParticipantMaster) {
          $participantNativeCount++
        }
        else {
          $participantNonNativeCount++
        }
        $participantConnectionRows = 0
        try { $participantConnectionRows = [int]$shape.RowCount(7) } catch { $participantConnectionRows = 0 }
        $connectionRows = 0
        $lifelineExtent = 0.0
        $connectionYs = @()
        try { $connectionRows = [int]$shape.RowCount(7) } catch { $connectionRows = 0 }
        try { $lifelineExtent = [Math]::Abs([double]$shape.CellsU('Controls.Row_1.Y').ResultIU) } catch { $lifelineExtent = 0.0 }
        try {
          for ($row = 0; $row -lt $connectionRows; $row++) {
            $connectionYs += [double]$shape.CellsSRC(7, $row, 1).ResultIU
          }
        } catch { }
        $nativeUnitForRows = Get-NativeConnectionPointUnit
        $expectedRows = if ($nativeUnitForRows -gt 0.03) {
          [Math]::Max(10, [Math]::Floor($lifelineExtent / $nativeUnitForRows) + 1)
        }
        else {
          10
        }
        $isSparse = ($connectionRows -lt $expectedRows)
        if ($isSparse) {
          $participantLifelinesWithSparseConnectionPoints++
        }
        if ($connectionRows -gt ($expectedRows + 2)) {
          $participantLifelinesWithExtraConnectionPoints++
        }
        $hasClusteredRows = $false
        $hasNonUniformRows = $false
        $orderedConnectionYs = @($connectionYs | Sort-Object -Descending)
        for ($rowIndex = 0; $rowIndex -lt ($orderedConnectionYs.Count - 1); $rowIndex++) {
          $gap = [Math]::Abs([double]$orderedConnectionYs[$rowIndex] - [double]$orderedConnectionYs[$rowIndex + 1])
          if ($nativeUnitForRows -gt 0.03 -and [Math]::Abs($gap - $nativeUnitForRows) -gt 0.04) {
            $hasNonUniformRows = $true
          }
          if ($gap -lt ([Math]::Max(0.08, $nativeUnitForRows * 0.5))) {
            $hasClusteredRows = $true
          }
          if ($masterName -match '^Object lifeline') {
            if ($null -eq $minObjectLifelineConnectionPointGap -or $gap -lt $minObjectLifelineConnectionPointGap) {
              $minObjectLifelineConnectionPointGap = $gap
            }
          }
        }
        if ($hasNonUniformRows) {
          $participantLifelinesWithNonUniformConnectionPointGap++
        }
        if ($masterName -match '^Object lifeline') {
          $objectLifelineCount++
          if ($isSparse) { $objectLifelinesWithSparseConnectionPoints++ }
          if ($hasClusteredRows) { $objectLifelinesWithClusteredConnectionPoints++ }
        }
      }
      if ($masterName -match '^(Message|Self Message|Return Message)') {
        if (-not [string]::IsNullOrWhiteSpace($text)) {
          $textBearingMessageCount++
          if (-not (Test-ShapeTextColorIsBlack $shape)) {
            $messageLabelsNotBlack++
          }
        }
        $beginFormula = ''
        $beginYFormula = ''
        $endFormula = ''
        $endYFormula = ''
        try { $beginFormula = [string]$shape.CellsU('BeginX').FormulaU } catch { }
        try { $beginYFormula = [string]$shape.CellsU('BeginY').FormulaU } catch { }
        try { $endFormula = [string]$shape.CellsU('EndX').FormulaU } catch { }
        try { $endYFormula = [string]$shape.CellsU('EndY').FormulaU } catch { }
        $hasConnectorGlue = ($beginFormula -match '(?i)PAR\(PNT\(' -and $beginYFormula -match '(?i)PAR\(PNT\(' -and $endFormula -match '(?i)PAR\(PNT\(' -and $endYFormula -match '(?i)PAR\(PNT\(')
        if (-not $hasConnectorGlue) {
          $messagesWithoutConnectorGlue++
        }
        $beginXResult = Get-CellResultSafe $shape 'BeginX'
        $beginYResult = Get-CellResultSafe $shape 'BeginY'
        $endXResult = Get-CellResultSafe $shape 'EndX'
        $endYResult = Get-CellResultSafe $shape 'EndY'
        if ($null -ne $beginYResult -and $null -ne $pageHeightForChecks) {
          $arrowTopDistance = [double]$pageHeightForChecks - [double]$beginYResult
          $beginTopDistance = [double]$pageHeightForChecks - [double]$beginYResult
          $endTopDistance = if ($null -ne $endYResult) { [double]$pageHeightForChecks - [double]$endYResult } else { $beginTopDistance }
          $messageArrowRows += [pscustomobject]@{
            PageIndex = $pageInspectIndex
            TopDistance = $arrowTopDistance
            TopDistanceMin = [Math]::Min($beginTopDistance, $endTopDistance)
            TopDistanceMax = [Math]::Max($beginTopDistance, $endTopDistance)
            IsSelfMessage = ($masterName -match '^Self Message')
            Text = $text
            MasterName = $masterName
          }
          if (-not $hasConnectorGlue -and -not (Test-OnNativeConnectionGrid $arrowTopDistance)) {
            $messageArrowsOffConnectionGrid++
          }
        }
        if ($masterName -match '^Self Message' -and $null -ne $beginYResult -and $null -ne $endYResult) {
          $expectedSelfHeight = Get-NativeConnectionPointUnit
          $actualSelfHeight = [Math]::Abs([double]$beginYResult - [double]$endYResult)
          if ([Math]::Abs($actualSelfHeight - $expectedSelfHeight) -gt 0.04) {
            $selfMessagesNotOneConnectionPoint++
          }
        }
        $isAllowedRefSelfMessage = $false
        foreach ($refBounds in $pageRefBounds) {
          if (Test-MessageIntersectsRefBounds $shape $refBounds) {
            if (Test-AllowedRefSelfMessage $shape $refBounds $text $masterName) {
              $allowedRefSelfMessages++
              $commonMethodName = Get-CommonMethodNameFromText $text
              if (-not [string]::IsNullOrWhiteSpace($commonMethodName)) {
                $allowedRefSelfMessageMethods += [pscustomobject]@{
                  PageIndex = $pageInspectIndex
                  Method = $commonMethodName
                }
              }
              $isAllowedRefSelfMessage = $true
            }
            else {
              $messagesInsideRefFragments++
            }
            break
          }
        }
        if ((Test-CommonMethodMessageText $text) -and -not $isAllowedRefSelfMessage) {
          $commonMethodMessagesOutsideRef++
        }
        if (-not $isAllowedRefSelfMessage) {
          foreach ($separatorY in $pageAltOperandSeparatorYs) {
            if ($null -eq $beginYResult -or $null -eq $endYResult) { continue }
            $messageYMin = [Math]::Min([double]$beginYResult, [double]$endYResult)
            $messageYMax = [Math]::Max([double]$beginYResult, [double]$endYResult)
            $separatorClearance = if ($masterName -match '^Self Message') { (Get-NativeConnectionPointUnit) * 2.0 } else { Get-NativeConnectionPointUnit }
            if ($separatorY -gt ($messageYMin - $separatorClearance) -and $separatorY -lt ($messageYMax + $separatorClearance)) {
              $messagesCrossingAltOperandSeparators++
              if ($masterName -match '^Self Message') { $selfMessageDoubleSpacingViolations++ }
              if ($env:VSDX_DEBUG_SPACING -eq '1') {
                $spacingDebugRows += [pscustomobject]@{
                  Type = 'separator'
                  Page = $pageInspectIndex
                  ShapeId = $shapeId
                  Master = $masterName
                  Text = $text
                  BeginY = $beginYResult
                  EndY = $endYResult
                  Target = $separatorY
                }
              }
              break
            }
          }
        }
        $shapeId = $null
        try { $shapeId = [int]$shape.ID } catch { }
        $requiredVisualGap = if ($masterName -match '^Self Message') { (Get-NativeConnectionPointUnit) * 2.0 } else { Get-NativeConnectionPointUnit }
        if (-not $isAllowedRefSelfMessage) {
          foreach ($spacingTarget in $pageMessageSpacingTargetBounds) {
            if ($null -ne $shapeId -and $null -ne $spacingTarget.Id -and $shapeId -eq $spacingTarget.Id) { continue }
            if (Test-MessageArrowTooCloseToVisualBounds $beginXResult $endXResult $beginYResult $endYResult $spacingTarget.Bounds $requiredVisualGap) {
              $messageArrowsTooCloseToOtherShapes++
              if ($masterName -match '^Self Message') { $selfMessageDoubleSpacingViolations++ }
              if ($env:VSDX_DEBUG_SPACING -eq '1') {
                $spacingDebugRows += [pscustomobject]@{
                  Type = 'bounds'
                  Page = $pageInspectIndex
                  ShapeId = $shapeId
                  Master = $masterName
                  Text = $text
                  BeginY = $beginYResult
                  EndY = $endYResult
                  Target = ("{0}#{1} {2}" -f $spacingTarget.MasterName, $spacingTarget.Id, $spacingTarget.Text)
                }
              }
              break
            }
          }
        }
        if ($masterName -notmatch '^Self Message' -and -not [string]::IsNullOrWhiteSpace($text)) {
          $controlYFormula = Get-CellFormulaSafe $shape 'Controls.TextPosition.Y'
          $txtPinYFormula = Get-CellFormulaSafe $shape 'TxtPinY'
          $controlYResult = Get-CellResultSafe $shape 'Controls.TextPosition.Y'
          $shapeHeightResult = Get-CellResultSafe $shape 'Height'
          $aboveArrowPattern = '(?i)Height\*0\.5\s*\+\s*TxtHeight\*0\.5\s*\+\s*0\.(02|04|06)\s*in'
          $labelIsAboveArrow = $false
          if ($null -ne $controlYResult -and $null -ne $shapeHeightResult) {
            $labelIsAboveArrow = ([double]$controlYResult -gt (([double]$shapeHeightResult / 2.0) + 0.015))
          }
          if (-not $labelIsAboveArrow -and $controlYFormula -notmatch $aboveArrowPattern -and $txtPinYFormula -notmatch $aboveArrowPattern) {
            $messageLabelsNotAboveArrow++
          }
        }
        if ($masterName -match '^Self Message' -and -not [string]::IsNullOrWhiteSpace($text)) {
          $hasTextControl = $false
          try { $hasTextControl = ($shape.CellExistsU('Controls.TextPosition.X', 0) -ne 0 -and $shape.CellExistsU('Controls.TextPosition.Y', 0) -ne 0) } catch { }
          $txtPinX = ''
          $txtPinY = ''
          $horzAlign = ''
          try { $txtPinX = [string]$shape.CellsU('TxtPinX').FormulaU } catch { }
          try { $txtPinY = [string]$shape.CellsU('TxtPinY').FormulaU } catch { }
          try { $horzAlign = [string]$shape.CellsU('Para.HorzAlign').FormulaU } catch { }
          if (-not $hasTextControl -or $txtPinX -notmatch '(?i)SETATREF\(Controls\.TextPosition' -or $txtPinY -notmatch '(?i)SETATREF\(Controls\.TextPosition\.Y') {
            $selfMessagesWithoutTextControl++
          }
          if ($horzAlign -eq '1') {
            $selfMessagesWithCenteredText++
          }
        }
      }
      if ($text -match '^\[[^\]]+\]' -and $masterName -notlike 'Interaction operand*' -and $masterName -notlike 'Optional fragment*') {
        $plainConditionLabelCount++
      }
      if ($text -match '^\[[^\]]+\]' -and $masterName -like 'Interaction operand*') {
        $conditionOperandCount++
        $widthFormula = ''
        $pinYFormula = ''
        $heightFormula = ''
        $locPinYFormula = ''
        try { $widthFormula = [string]$shape.CellsU('Width').FormulaU } catch { }
        try { $pinYFormula = [string]$shape.CellsU('PinY').FormulaU } catch { }
        try { $heightFormula = [string]$shape.CellsU('Height').FormulaU } catch { }
        try { $locPinYFormula = [string]$shape.CellsU('LocPinY').FormulaU } catch { }
        $operandHeight = Get-CellResultSafe $shape 'Height'
        $operandTxtPinY = Get-CellResultSafe $shape 'TxtPinY'
        if ($null -ne $operandHeight -and $null -ne $operandTxtPinY -and [Math]::Abs([double]$operandTxtPinY - [double]$operandHeight) -gt 0.04) {
          $conditionOperandTextMisaligned++
        }
        $belongsToOptionalFragment = Test-ShapeIsMemberOfMasterName $page $shape '^Optional fragment'
        if (-not $belongsToOptionalFragment -and $widthFormula -notmatch '(?i)SETATREF\(.+!Controls\.Row_1|LISTSHEETREF\(\)!Controls\.ROW_1') {
          $conditionOperandsWithoutResizeBinding++
        }
        $belongsToAlternativeFragment = Test-ShapeIsMemberOfMasterName $page $shape '^Alternative fragment'
        $verticalFormula = "$pinYFormula $heightFormula $locPinYFormula"
        if ($belongsToAlternativeFragment -and $verticalFormula -match '(?i)Sheet\.\d+!(Height|PinY|LocPinY)') {
          $altOperandVerticalFormulaLock++
        }
      }
      elseif (-not [string]::IsNullOrWhiteSpace($text) -and $masterName -like 'Interaction operand*') {
        $conditionOperandsWithoutBrackets++
      }
      if ($text -eq 'alt' -and $masterName -like 'Alternative fragment*') {
        $altFragmentCount++
        $memberIds = Get-ContainerMemberIdsSafe $shape
        $listMemberIds = Get-ContainerListMemberIdsSafe $shape
        $memberIdSet = @{}
        foreach ($knownMemberId in @($memberIds + $listMemberIds)) {
          try { $memberIdSet[[int]$knownMemberId] = $true } catch { }
        }
        $memberCount = @($memberIds).Count
        if ($memberCount -le 0) { $altFragmentsWithoutMembers++ }
        $operandMemberCount = 0
        $operandListMemberCount = 0
        $operandListInfos = @()
        $frameBounds = Get-ShapeBoundsSafe $shape
        if ($null -ne $frameBounds) { $pageAltFrameBounds += $frameBounds }
        $memberOverflowDetected = $false
        foreach ($memberId in $memberIds) {
          try {
            $member = $page.Shapes.ItemFromID([int]$memberId)
            $memberMasterName = Get-ShapeMasterNameSafe $member
            if ($memberMasterName -like 'Interaction operand*') {
              $operandMemberCount++
            }
            $memberBounds = Get-ShapeBoundsSafe $member
            if ($null -ne $frameBounds -and $null -ne $memberBounds -and $memberMasterName -notmatch '(?i)lifeline') {
              if (
                [double]$memberBounds.Left -lt ([double]$frameBounds.Left - 0.03) -or
                [double]$memberBounds.Right -gt ([double]$frameBounds.Right + 0.03) -or
                [double]$memberBounds.Top -gt ([double]$frameBounds.Top + 0.03) -or
                [double]$memberBounds.Bottom -lt ([double]$frameBounds.Bottom - 0.03)
              ) {
                $memberOverflowDetected = $true
              }
            }
          } catch { }
        }
        foreach ($listMemberId in $listMemberIds) {
          try {
            $listMember = $page.Shapes.ItemFromID([int]$listMemberId)
            if ((Get-ShapeMasterNameSafe $listMember) -like 'Interaction operand*') {
              $operandListMemberCount++
              $listMemberBounds = Get-ShapeBoundsSafe $listMember
              if ($null -ne $listMemberBounds -and $null -ne $pageHeightForChecks) {
                $operandListInfos += [pscustomobject]@{
                  Shape = $listMember
                  Text = Get-ShapeTextSafe $listMember
                  Bounds = $listMemberBounds
                  TopDistance = [double]$pageHeightForChecks - [double]$listMemberBounds.Top
                }
              }
            }
          } catch { }
        }
        $hasIrisInterestJudgmentOperand = $false
        foreach ($operandInfo in @($operandListInfos)) {
          $operandText = [string]$operandInfo.Text
          if (($operandText -match 'ED0005') -and ($operandText -match 'ED0009') -and (Test-TextContainsAnyTerm $operandText @($script:IrisInterestSystemAbnormalTerm))) {
            $hasIrisInterestJudgmentOperand = $true
            break
          }
        }
        if ($hasIrisInterestJudgmentOperand -and $null -ne $frameBounds) {
          $pageIrisInterestJudgmentAltBounds += $frameBounds
        }
        $altNativeOperandListMembers += $operandListMemberCount
        if ($operandListMemberCount -lt 2) {
          $altFragmentsMissingNativeOperandList++
        }
        if ($operandMemberCount -gt 0 -and @($listMemberIds).Count -lt $operandMemberCount) {
          $altFragmentsMissingOperandListMembers++
        }
        if ($memberOverflowDetected) { $altFragmentsWithMemberOverflow++ }
        if ($null -ne $frameBounds -and $null -ne $pageHeightForChecks -and $operandListInfos.Count -ge 2) {
          $sortedOperands = @($operandListInfos | Sort-Object TopDistance)
          $lastOperand = $sortedOperands[$sortedOperands.Count - 1]
          if (Test-SuccessLikeOperandText ([string]$lastOperand.Text)) {
            $frameBottomDistance = [double]$pageHeightForChecks - [double]$frameBounds.Bottom
            $unit = Get-NativeConnectionPointUnit
            $continuousGap = [Math]::Max($unit * 2.1, 0.50)
            $reachableBottomDistance = $frameBottomDistance
            $candidateRows = @()
            foreach ($candidate in @($page.Shapes)) {
              $candidateId = $null
              try { $candidateId = [int]$candidate.ID } catch { continue }
              $shapeId = $null
              try { $shapeId = [int]$shape.ID } catch { }
              if ($null -ne $shapeId -and $candidateId -eq $shapeId) { continue }
              if ($memberIdSet.ContainsKey($candidateId)) { continue }
              $candidateText = Get-ShapeTextSafe $candidate
              $candidateMaster = Get-ShapeMasterNameSafe $candidate
              if (-not (Test-SignificantBranchContentShape $candidateMaster $candidateText)) { continue }
              $candidateBounds = Get-ShapeBoundsSafe $candidate
              if ($null -eq $candidateBounds) { continue }
              $candidateTopDistance = [double]$pageHeightForChecks - [double]$candidateBounds.Top
              if ($candidateTopDistance -le ([double]$lastOperand.TopDistance + 0.05)) { continue }
              if (-not (Test-HorizontalBoundsOverlap $candidateBounds $frameBounds 0.25)) { continue }
              $candidateBottomDistance = [double]$pageHeightForChecks - [double]$candidateBounds.Bottom
              $candidateRows += [pscustomobject]@{
                Bounds = $candidateBounds
                TopDistance = $candidateTopDistance
                BottomDistance = $candidateBottomDistance
              }
            }
            foreach ($candidateRow in @($candidateRows | Sort-Object TopDistance)) {
              if ([double]$candidateRow.TopDistance -gt ($reachableBottomDistance + $continuousGap)) { continue }
              if ([double]$candidateRow.BottomDistance -gt ($frameBottomDistance + 0.04)) {
                $altSuccessBranchContentOutsideFrame++
                break
              }
              $reachableBottomDistance = [Math]::Max($reachableBottomDistance, [double]$candidateRow.BottomDistance)
            }
          }
        }
        $hasResizeControl = $false
        try { $hasResizeControl = ($shape.CellExistsU('Controls.Row_1.X', 0) -ne 0 -or $shape.CellExistsU('Controls.Row_1', 0) -ne 0) } catch { }
        if (-not $hasResizeControl) { $altFragmentsMissingResizeControl++ }
      }
      if ($masterName -like 'Optional fragment*' -or ($text -eq 'opt' -and $masterName -like 'Alternative fragment*')) {
        $optFragmentCount++
        $memberCount = 0
        try { $memberCount = @(Get-ContainerMemberIdsSafe $shape).Count } catch { $memberCount = 0 }
        if ($masterName -like 'Alternative fragment*' -and $memberCount -le 0) { $optFragmentsWithoutMembers++ }
        if (-not (Test-FragmentHasNativeConditionMember $page $shape)) {
          $optFragmentsMissingCondition++
        }
      }
    } catch { }
    }
    $unitForChildFragmentGap = Get-NativeConnectionPointUnit
    for ($fragmentIndex = 0; $fragmentIndex -lt $pageFragmentFrameBounds.Count; $fragmentIndex++) {
      $fragmentA = $pageFragmentFrameBounds[$fragmentIndex]
      for ($otherFragmentIndex = $fragmentIndex + 1; $otherFragmentIndex -lt $pageFragmentFrameBounds.Count; $otherFragmentIndex++) {
        $fragmentB = $pageFragmentFrameBounds[$otherFragmentIndex]
        $boundsA = $fragmentA.Bounds
        $boundsB = $fragmentB.Bounds
        $overlapX = [Math]::Min([double]$boundsA.Right, [double]$boundsB.Right) - [Math]::Max([double]$boundsA.Left, [double]$boundsB.Left)
        $overlapY = [Math]::Min([double]$boundsA.Top, [double]$boundsB.Top) - [Math]::Max([double]$boundsA.Bottom, [double]$boundsB.Bottom)
        if ($overlapX -le 0.03 -or $overlapY -le 0.03) { continue }

        $aContainsB = Test-BoundsInsideBoundsSafe $boundsB $boundsA 0.03
        $bContainsA = Test-BoundsInsideBoundsSafe $boundsA $boundsB 0.03
        if (-not ($aContainsB -or $bContainsA)) {
          $fragmentSiblingOverlaps++
        }
      }
    }
    foreach ($childFragment in @($pageFragmentFrameBounds)) {
      $childBounds = $childFragment.Bounds
      $bestParentFragment = $null
      $bestParentArea = $null
      foreach ($parentFragment in @($pageFragmentFrameBounds)) {
        if ($null -ne $childFragment.Id -and $null -ne $parentFragment.Id -and $childFragment.Id -eq $parentFragment.Id) { continue }
        $parentBounds = $parentFragment.Bounds
        if (-not (Test-BoundsInsideBoundsSafe $childBounds $parentBounds 0.04)) { continue }
        $parentWidth = [Math]::Max(0.01, [double]$parentBounds.Right - [double]$parentBounds.Left)
        $parentHeight = [Math]::Max(0.01, [double]$parentBounds.Top - [double]$parentBounds.Bottom)
        $parentArea = $parentWidth * $parentHeight
        if ($null -eq $bestParentFragment -or $parentArea -lt $bestParentArea) {
          $bestParentFragment = $parentFragment
          $bestParentArea = $parentArea
        }
      }
      if ($null -eq $bestParentFragment) { continue }
      $parentBounds = $bestParentFragment.Bounds
      $parentWidthForGap = [Math]::Max(0.01, [double]$parentBounds.Right - [double]$parentBounds.Left)
      $childWidthForGap = [Math]::Max(0.01, [double]$childBounds.Right - [double]$childBounds.Left)
      $leftGap = [double]$childBounds.Left - [double]$parentBounds.Left
      $rightGap = [double]$parentBounds.Right - [double]$childBounds.Right
      $topGap = [double]$parentBounds.Top - [double]$childBounds.Top
      $bottomGap = [double]$childBounds.Bottom - [double]$parentBounds.Bottom
      $isBroadChildFragment = (($childWidthForGap / $parentWidthForGap) -ge 0.75)
      if (
        ($isBroadChildFragment -and ($leftGap -lt 0.08 -or $rightGap -lt 0.08 -or $topGap -lt (($unitForChildFragmentGap * 2.0) - 0.04))) -or
        (-not $isBroadChildFragment -and ($leftGap -lt 0.08 -or $rightGap -lt 0.08 -or $topGap -lt 0.08 -or $bottomGap -lt 0.08))
      ) {
        $childFragmentParentSpacingTooSmall++
      }
    }
    foreach ($groupFragment in @($pageFragmentFrameBounds)) {
      $groupText = ([string]$groupFragment.Text).Trim()
      if ([string]::IsNullOrWhiteSpace($groupText)) { continue }
      if ($groupText -in @('alt', 'opt', 'ref', 'loop')) { continue }
      if ([string]$groupFragment.MasterName -notmatch '(?i)^Other fragment') { continue }
      $groupBounds = $groupFragment.Bounds
      if ($null -eq $groupBounds) { continue }
      $hasBusinessContent = $false
      foreach ($candidate in @($page.Shapes)) {
        $candidateId = $null
        try { $candidateId = [int]$candidate.ID } catch { }
        if ($null -ne $candidateId -and $null -ne $groupFragment.Id -and $candidateId -eq [int]$groupFragment.Id) { continue }
        $candidateMaster = Get-ShapeMasterNameSafe $candidate
        if ($candidateMaster -match '(?i)^(Actor lifeline|Object lifeline|Activation|Interaction operand)') { continue }
        $candidateText = Get-ShapeTextSafe $candidate
        $candidateName = ''
        try { $candidateName = [string]$candidate.NameU } catch { }
        $candidateSectionKind = Get-SectionDividerPartKind $candidate $candidateText $candidateMaster
        if ($candidateSectionKind -in @('line', 'title')) { continue }
        if ($candidateText -in @('User', 'APP', 'Enterprise', 'IRIS', 'DB', 'Redis')) { continue }
        $candidateBounds = Get-ShapeBoundsSafe $candidate
        if ($null -eq $candidateBounds) { continue }
        if (Test-NativeFragmentFrameShapeSafe $candidateMaster) {
          if (Test-BoundsInsideBoundsSafe $candidateBounds $groupBounds 0.04) {
            $hasBusinessContent = $true
            break
          }
          continue
        }
        if ($candidateMaster -match '^(Message|Self Message|Return Message)' -or -not [string]::IsNullOrWhiteSpace($candidateText) -or $candidateName -match '(?i)(orange|pointer|note)') {
          if (Test-BoundsCenterInsideBoundsSafe $candidateBounds $groupBounds 0.02) {
            $hasBusinessContent = $true
            break
          }
        }
      }
      if (-not $hasBusinessContent) {
        $emptyGroupFragmentCount++
      }
    }
    $unitForSectionFragmentGap = Get-NativeConnectionPointUnit
    foreach ($sectionRow in @($pageSectionDividerTitleRows)) {
      $nearestFragmentGap = $null
      foreach ($fragmentRow in @($pageFragmentFrameBounds)) {
        $fragmentTopDistance = [double]$pageHeightForChecks - [double]$fragmentRow.Bounds.Top
        $gapAfterSection = $fragmentTopDistance - [double]$sectionRow.TopDistance
        if ($gapAfterSection -lt -0.03) { continue }
        if (-not (Test-HorizontalBoundsOverlap $sectionRow.Bounds $fragmentRow.Bounds 0.05)) { continue }
        if ($null -eq $nearestFragmentGap -or $gapAfterSection -lt $nearestFragmentGap) {
          $nearestFragmentGap = $gapAfterSection
        }
      }
      if ($null -ne $nearestFragmentGap -and $nearestFragmentGap -lt (($unitForSectionFragmentGap * 2.0) - 0.04)) {
        $sectionFragmentSpacingTooSmall++
      }
    }
    $pageHasIrisInterestEdMessages = $pageIsInterestDetail -and $pageHasIrisInterestEd0005 -and $pageHasIrisInterestEd0009
    if ($pageHasIrisInterestEdMessages -and @($pageIrisEdMessageBounds).Count -gt 0) {
      $geometryJudgmentAltBounds = @()
      foreach ($altBounds in @($pageAltFrameBounds)) {
        $containsAllEdMessages = $true
        foreach ($edBounds in @($pageIrisEdMessageBounds)) {
          if (-not (Test-BoundsInsideBoundsSafe $edBounds $altBounds 0.04)) {
            $containsAllEdMessages = $false
            break
          }
        }
        if ($containsAllEdMessages) { $geometryJudgmentAltBounds += $altBounds }
      }
      if (@($geometryJudgmentAltBounds).Count -gt 0) { $pageIrisInterestJudgmentAltBounds = $geometryJudgmentAltBounds }
    }
    if ($pageHasIrisInterestEdMessages -and @($pageIrisInterestJudgmentAltBounds).Count -eq 0) {
      $irisInterestJudgmentContentOutsideAlt += @($pageIrisInterestTargetBounds).Count
    }
    elseif (@($pageIrisInterestJudgmentAltBounds).Count -gt 0 -and @($pageIrisInterestTargetBounds).Count -gt 0) {
      foreach ($targetBounds in @($pageIrisInterestTargetBounds)) {
        $insideJudgmentAlt = $false
        foreach ($altBounds in @($pageIrisInterestJudgmentAltBounds)) {
          if (Test-BoundsInsideBoundsSafe $targetBounds $altBounds 0.04) {
            $insideJudgmentAlt = $true
            break
          }
        }
        if (-not $insideJudgmentAlt) { $irisInterestJudgmentContentOutsideAlt++ }
      }
    }
    if ($pageHasIrisInterestEdMessages) {
      if (@($pageIrisInterestQueryGroupBounds).Count -eq 0) {
        $irisInterestJudgmentAltOutsideQueryGroup++
      }
      else {
        foreach ($altBounds in @($pageIrisInterestJudgmentAltBounds)) {
          $insideQueryGroup = $false
          foreach ($groupBounds in @($pageIrisInterestQueryGroupBounds)) {
            if (Test-BoundsInsideBoundsSafe $altBounds $groupBounds 0.04) {
              $insideQueryGroup = $true
              break
            }
          }
          if (-not $insideQueryGroup) { $irisInterestJudgmentAltOutsideQueryGroup++ }
        }
      }
    }
  }
}
finally {
  if ($doc -ne $null) { $doc.Close() }
  if ($visio -ne $null) { $visio.Quit() }
}

foreach ($group in @($messageArrowRows | Group-Object PageIndex)) {
  $rows = @($group.Group | Sort-Object TopDistanceMin)
  for ($rowIndex = 0; $rowIndex -lt ($rows.Count - 1); $rowIndex++) {
    $current = $rows[$rowIndex]
    $next = $rows[$rowIndex + 1]
    $gap = [double]$next.TopDistanceMin - [double]$current.TopDistanceMax
    $requiredGap = if ($current.IsSelfMessage -or $next.IsSelfMessage) { (Get-NativeConnectionPointUnit) * 2.0 } else { Get-NativeConnectionPointUnit }
    if ($gap -lt ($requiredGap - 0.035)) {
      $messageArrowGapsTooSmall++
      if ($current.IsSelfMessage -or $next.IsSelfMessage) { $selfMessageDoubleSpacingViolations++ }
    }
  }
}

foreach ($refSelfMethod in @($allowedRefSelfMessageMethods)) {
  $hasPointer = $false
  foreach ($pointerMethod in @($refPointerDisplayMethods)) {
    if ([int]$pointerMethod.PageIndex -eq [int]$refSelfMethod.PageIndex -and [string]$pointerMethod.Method -eq [string]$refSelfMethod.Method) {
      $hasPointer = $true
      break
    }
  }
  if (-not $hasPointer) { $commonRefSelfMessagesWithoutPointer++ }
}

if ($shapeCount -lt $MinTopLevelShapes) {
  $errors.Add("top-level Page.Shapes.Count is $shapeCount; expected at least $MinTopLevelShapes. This usually means SVG-import group output.")
}
if ($altFragmentCount -gt 0 -and $altFragmentsWithoutMembers -gt 0) {
  $errors.Add("native Alternative fragment alt containers without members detected: $altFragmentsWithoutMembers of $altFragmentCount")
}
if ($altFragmentCount -gt 0 -and $altFragmentsMissingOperandListMembers -gt 0) {
  $errors.Add("native Alternative fragment alt operands are container members but not list members: $altFragmentsMissingOperandListMembers of $altFragmentCount; use InsertListMember so selecting an if/else region highlights the owning alt")
}
if ($altFragmentCount -gt 0 -and $altFragmentsMissingNativeOperandList -gt 0) {
  $errors.Add("native Alternative fragment alt containers without two native Interaction operand list members detected: $altFragmentsMissingNativeOperandList of $altFragmentCount; alt must remain a real Visio UML Alternative fragment with if/else operands")
}
if ($altFragmentCount -gt 0 -and $altFragmentsWithMemberOverflow -gt 0) {
  $errors.Add("native Alternative fragment alt frames do not cover all member shapes: $altFragmentsWithMemberOverflow of $altFragmentCount; restore frame width/height after InsertListMember and keep branch content inside the owning alt")
}
if ($altSuccessBranchContentOutsideFrame -gt 0) {
  $errors.Add("success-like else branch content starts immediately below an alt frame instead of inside it: $altSuccessBranchContentOutsideFrame; extend the owning alt/Interaction operand to cover the success branch and add the nested group/ref/messages as members")
}
if ($altFragmentsMissingResizeControl -gt 0) {
  $errors.Add("native alt fragments missing right-side resize control points: $altFragmentsMissingResizeControl of $altFragmentCount")
}
if ($optFragmentCount -gt 0 -and $optFragmentsWithoutMembers -gt 0) {
  $errors.Add("native opt fragment containers without members detected: $optFragmentsWithoutMembers of $optFragmentCount")
}
if ($optFragmentsMissingCondition -gt 0) {
  $errors.Add("native opt fragment containers missing native condition operand text: $optFragmentsMissingCondition of $optFragmentCount")
}
if ($plainConditionLabelCount -gt 0) {
  $errors.Add("plain condition label text boxes detected: $plainConditionLabelCount; alt/else condition labels must use native Interaction operand shapes")
}
if ($conditionOperandsWithoutResizeBinding -gt 0) {
  $errors.Add("native condition operands without alt resize-control width binding detected: $conditionOperandsWithoutResizeBinding")
}
if ($conditionOperandTextMisaligned -gt 0) {
  $errors.Add("native condition operand labels are not pinned to the top of their operand: $conditionOperandTextMisaligned; resized alt/else/opt operands must sync TxtPinY to Height so [條件] text stays under the separator")
}
if ($diagonalDashedPathCount -gt 0) {
  $errors.Add("diagonal dashed connector/operand separator artifacts detected in exported visual probe: $diagonalDashedPathCount; resized native Interaction operand geometry must keep separator lines horizontal")
}
if ($conditionOperandsWithoutBrackets -gt 0) {
  $errors.Add("native alt/else Interaction operand labels without square brackets detected: $conditionOperandsWithoutBrackets; branch condition labels must use [條件] format")
}
if ($altOperandVerticalFormulaLock -gt 0) {
  $errors.Add("native alt Interaction operand vertical formulas still depend on other operand cells: $altOperandVerticalFormulaLock; freeze operand PinY/Height/LocPinY after layout so Visio native member handles drag in the expected direction")
}
if ($manualFragmentOverlayCount -gt 0) {
  $errors.Add("manual alt/ref overlay frames detected: $manualFragmentOverlayCount; formal delivery must use native UML fragment title areas instead of manual header boxes")
}
if ($refFragmentsNotSixConnectionPoints -gt 0) {
  $errors.Add("native ref fragments not sized to six connection-point intervals detected: $refFragmentsNotSixConnectionPoints of $refFragmentCount")
}
if ($messagesInsideRefFragments -gt 0) {
  $errors.Add("native ref fragments contain non-reference message arrows or self messages: $messagesInsideRefFragments; ref may contain only the CommonFunc/CommonUtil reference self-call, not main-flow request/response messages")
}
if ($refDisplayNamesWithSvgExtension -gt 0) {
  $errors.Add("native ref visible CommonFunc/CommonUtil display names still include .svg: $refDisplayNamesWithSvgExtension; use basename plus Chinese description on the orange pointer strip")
}
if ($refDisplayNamesMissingChineseDescription -gt 0) {
  $errors.Add(("native ref visible CommonFunc/CommonUtil display names missing Chinese descriptions: {0}; orange pointer strip must show '循序圖請參考：basename 中文說明'" -f $refDisplayNamesMissingChineseDescription))
}
if ($refDisplayNamesMissingPointerPrefix -gt 0) {
  $errors.Add(("native ref visible CommonFunc/CommonUtil display names missing '循序圖請參考：' prefix: {0}; orange pointer strip must show '循序圖請參考：basename 中文說明'" -f $refDisplayNamesMissingPointerPrefix))
}
if ($commonRefSelfMessagesWithoutPointer -gt 0) {
  $errors.Add("native CommonFunc/CommonUtil ref self-calls without matching orange pointer strip detected: $commonRefSelfMessagesWithoutPointer; every common ref must include a basename-plus-Chinese reference strip for the same method")
}
if ($commonFuncSlashNotation -gt 0) {
  $errors.Add("native CommonFunc ref self-call labels using slash notation detected: $commonFuncSlashNotation; internal CommonFunc methods must use CommonFunc.MethodName")
}
if ($commonUtilDotNotation -gt 0) {
  $errors.Add("native CommonUtil ref self-call labels using dot notation detected: $commonUtilDotNotation; CommonUtil references should keep CommonUtil/MethodName")
}
if ($fragmentEdgesOffConnectionGrid -gt 0) {
  $errors.Add("native fragment top/bottom edges not aligned to connection-point grid detected: $fragmentEdgesOffConnectionGrid")
}
if ($fragmentSideClearanceTooTight -gt 0) {
  $errors.Add("native fragment left/right edges too close to participant lifelines detected: $fragmentSideClearanceTooTight")
}
if ($childFragmentParentSpacingTooSmall -gt 0) {
  $errors.Add("native child fragments too close to their parent fragment edges detected: $childFragmentParentSpacingTooSmall; nested group/alt/ref frames need visible parent-child inset, especially under alt/else branches")
}
if ($fragmentSiblingOverlaps -gt 0) {
  $errors.Add("visible sibling fragment frames overlap each other: $fragmentSiblingOverlaps; consecutive opt/alt/ref/group blocks must keep clear vertical spacing unless one is a true parent of the other")
}
if ($fragmentFrameGeometryMismatch -gt 0) {
  $errors.Add("native fragment frame geometry does not match shape width/height: $fragmentFrameGeometryMismatch; resized alt/opt/ref/group frames must sync visible Geometry rows with the actual frame bounds")
}
if ($fragmentTitleMisaligned -gt 0) {
  $errors.Add("native fragment title tabs do not follow resized frame bounds: $fragmentTitleMisaligned; alt/opt/ref/group title child shapes must stay pinned to the top-left header area after resizing")
}
if ($emptyGroupFragmentCount -gt 0) {
  $errors.Add("native business group fragments without enclosed content detected: $emptyGroupFragmentCount; group frames must wrap at least one real message/ref/alt/opt/group item, otherwise use a section divider instead of an empty group")
}
if ($sectionFragmentSpacingTooSmall -gt 0) {
  $errors.Add("native section title to first fragment spacing is too small: $sectionFragmentSpacingTooSmall; keep at least two participant connection-point intervals between a section divider title and the next business fragment")
}
if ($conditionOperandCount -gt 0 -and ($altFragmentCount + $optFragmentCount) -eq 0) {
  $errors.Add("native condition operands detected but no visible native alt/opt fragment containers were found; restore Alternative/Optional fragment text instead of hiding native UML fragments")
}
if ($participantNonNativeCount -gt 0) {
  $errors.Add("participant labels not backed by native UML lifeline masters detected: $participantNonNativeCount")
}
if ($participantLifelinesWithExtraConnectionPoints -gt 0) {
  $errors.Add("native participant lifelines with excessive connection-point rows detected: $participantLifelinesWithExtraConnectionPoints; use one full uniform UML-native grid, not per-message generated rows")
}
if ($participantLifelinesWithSparseConnectionPoints -gt 0) {
  $errors.Add("native participant lifelines with sparse connection-point rows detected: $participantLifelinesWithSparseConnectionPoints; use a full UML-native default connection-point grid along every lifeline")
}
if ($participantLifelinesWithNonUniformConnectionPointGap -gt 0) {
  $errors.Add("native participant lifelines with non-uniform connection-point gaps detected: $participantLifelinesWithNonUniformConnectionPointGap; all lifeline connection points must use the UML-native default interval")
}
if ($messagesWithoutConnectorGlue -gt 0) {
  $errors.Add("native message arrows without connector glue detected: $messagesWithoutConnectorGlue; every message/return/self-call head and tail must be glued to existing participant connection points")
}
if ($messageArrowsOffConnectionGrid -gt 0) {
  $errors.Add("native message arrows off the participant connection-point grid detected: $messageArrowsOffConnectionGrid; snap all message endpoints to UML-native connection rows")
}
if ($commonMethodMessagesOutsideRef -gt 0) {
  $errors.Add("CommonFunc/CommonUtil methods drawn outside native ref fragments detected: $commonMethodMessagesOutsideRef; common methods must be modeled as a ref fragment with only the compact reference self-call inside")
}
if ($messageArrowGapsTooSmall -gt 0) {
  $errors.Add("native message arrows closer than required connector spacing detected: $messageArrowGapsTooSmall; normal messages need one connection-point interval and any spacing involving a self message needs two intervals")
}
if ($selfMessageDoubleSpacingViolations -gt 0) {
  $errors.Add("native self messages without double vertical spacing detected: $selfMessageDoubleSpacingViolations; self-message folded arrows must reserve two connection-point intervals above and below")
}
if ($messageArrowsTooCloseToOtherShapes -gt 0) {
  $errors.Add("native message arrows too close to fragment/frame/title/orange-pointer shapes detected: $messageArrowsTooCloseToOtherShapes; normal messages need one connection-point interval from other visual shapes and self messages need two")
}
if ($messagesCrossingAltOperandSeparators -gt 0) {
  $errors.Add("native messages crossing or touching alt/else Interaction operand separator lines detected: $messagesCrossingAltOperandSeparators; branch messages must leave connector-point spacing, and self messages must leave double spacing, inside their owning if/else operand")
}
if ($messageLabelsNotAboveArrow -gt 0) {
  $errors.Add("native message/return labels not positioned directly above the arrow detected: $messageLabelsNotAboveArrow")
}
if ($messageLabelsNotBlack -gt 0) {
  $errors.Add("native message/self/return labels not using black font detected: $messageLabelsNotBlack")
}
if ($selfMessagesWithoutTextControl -gt 0) {
  $errors.Add("native self-message labels without editable text-position controls detected: $selfMessagesWithoutTextControl")
}
if ($selfMessagesWithCenteredText -gt 0) {
  $errors.Add("native self-message labels with centered text detected: $selfMessagesWithCenteredText; labels should be left/right aligned next to the folded arrow")
}
if ($selfMessagesNotOneConnectionPoint -gt 0) {
  $errors.Add("native self-message folded arrows not one connection-point interval tall detected: $selfMessagesNotOneConnectionPoint")
}
if ($objectLifelinesWithClusteredConnectionPoints -gt 0) {
  $errors.Add("native object lifelines with clustered connection-point rows near message endpoints detected: $objectLifelinesWithClusteredConnectionPoints of $objectLifelineCount")
}
if ($objectLifelinesWithSparseConnectionPoints -gt 0) {
  $errors.Add("native object lifelines with sparse connection-point rows detected: $objectLifelinesWithSparseConnectionPoints of $objectLifelineCount")
}
if ($pageDrawingResizeType -ne '0') {
  $errors.Add("Visio page auto-resize is enabled: DrawingResizeType=$pageDrawingResizeType; formal VSDX should keep page size fixed during section-title border edits")
}
if ($pageResizePage -notmatch '(?i)^(FALSE|0)$') {
  $errors.Add("Visio page ResizePage is not disabled: ResizePage=$pageResizePage; formal VSDX should not resize the page when editing diagram parts")
}
if ($sectionDividerPartsUnlocked -gt 0) {
  $errors.Add("section divider line parts without fixed horizontal sizing/move locks detected: $sectionDividerPartsUnlocked of $sectionDividerPartCount")
}
if ($sectionDividerTitleBoxesLockedForResize -gt 0) {
  $errors.Add("section divider title boxes locked against border resizing detected: $sectionDividerTitleBoxesLockedForResize of $sectionDividerTitleBoxCount; title boxes should remain editable while page auto-resize is disabled")
}
if ($sectionDividerTitleBoxesTooNarrow -gt 0) {
  $errors.Add("section divider title boxes too narrow for their label text detected: $sectionDividerTitleBoxesTooNarrow; widen title boxes by label length instead of allowing Chinese labels to wrap")
}
if ($irisInterestJudgmentContentOutsideAlt -gt 0) {
  $errors.Add("IRIS interest-query judgment content outside ED0005/ED0009 native alt detected: $irisInterestJudgmentContentOutsideAlt; the ED0005/ED0009 request/response, CommonFunc ref, and interest assembly content must be wrapped by the same native alt")
}
if ($irisInterestJudgmentAltOutsideQueryGroup -gt 0) {
  $errors.Add("IRIS interest-query judgment alt outside its query group detected: $irisInterestJudgmentAltOutsideQueryGroup; the ED0005/ED0009 native alt must be inside the native query-interest group, not a sibling or parent of that group")
}

$report = [pscustomobject]@{
  VsdxPath = $full
  TopLevelShapes = $shapeCount
  Connects = $connectCount
  PageDrawingResizeType = $pageDrawingResizeType
  PageResizePage = $pageResizePage
  SectionDividerParts = $sectionDividerPartCount
  SectionDividerPartsUnlocked = $sectionDividerPartsUnlocked
  SectionDividerTitleBoxes = $sectionDividerTitleBoxCount
  SectionDividerTitleBoxesLockedForResize = $sectionDividerTitleBoxesLockedForResize
  SectionDividerTitleBoxesTooNarrow = $sectionDividerTitleBoxesTooNarrow
  IrisInterestJudgmentContentOutsideAlt = $irisInterestJudgmentContentOutsideAlt
  IrisInterestJudgmentAltOutsideQueryGroup = $irisInterestJudgmentAltOutsideQueryGroup
  Media = $mediaCount
  Embeddings = $embeddingCount
  ForeignDataXmlEntries = $foreignDataXmlCount
  HasTheme = $hasTheme
  HasThemeRelationship = $hasThemeRelationship
  AltFragments = $altFragmentCount
  AltFragmentsWithoutMembers = $altFragmentsWithoutMembers
  AltFragmentsMissingOperandListMembers = $altFragmentsMissingOperandListMembers
  AltFragmentsMissingNativeOperandList = $altFragmentsMissingNativeOperandList
  AltNativeOperandListMembers = $altNativeOperandListMembers
  AltFragmentsWithMemberOverflow = $altFragmentsWithMemberOverflow
  AltSuccessBranchContentOutsideFrame = $altSuccessBranchContentOutsideFrame
  AltFragmentsMissingResizeControl = $altFragmentsMissingResizeControl
  OptFragments = $optFragmentCount
  OptFragmentsWithoutMembers = $optFragmentsWithoutMembers
  OptFragmentsMissingCondition = $optFragmentsMissingCondition
  PlainConditionLabels = $plainConditionLabelCount
  ConditionOperands = $conditionOperandCount
  ConditionOperandsWithoutBrackets = $conditionOperandsWithoutBrackets
  ConditionOperandsWithoutResizeBinding = $conditionOperandsWithoutResizeBinding
  ConditionOperandTextMisaligned = $conditionOperandTextMisaligned
  AltOperandVerticalFormulaLock = $altOperandVerticalFormulaLock
  DiagonalDashedPaths = $diagonalDashedPathCount
  ManualFragmentOverlays = $manualFragmentOverlayCount
  RefFragments = $refFragmentCount
  RefFragmentsNotSixConnectionPoints = $refFragmentsNotSixConnectionPoints
  MessagesInsideRefFragments = $messagesInsideRefFragments
  AllowedRefSelfMessages = $allowedRefSelfMessages
  RefDisplayNamesWithSvgExtension = $refDisplayNamesWithSvgExtension
  RefDisplayNamesMissingChineseDescription = $refDisplayNamesMissingChineseDescription
  RefDisplayNamesMissingPointerPrefix = $refDisplayNamesMissingPointerPrefix
  CommonRefSelfMessagesWithoutPointer = $commonRefSelfMessagesWithoutPointer
  CommonFuncSlashNotation = $commonFuncSlashNotation
  CommonUtilDotNotation = $commonUtilDotNotation
  FragmentEdgesOffConnectionGrid = $fragmentEdgesOffConnectionGrid
  FragmentSideClearanceTooTight = $fragmentSideClearanceTooTight
  ChildFragmentParentSpacingTooSmall = $childFragmentParentSpacingTooSmall
  FragmentSiblingOverlaps = $fragmentSiblingOverlaps
  FragmentFrameGeometryMismatch = $fragmentFrameGeometryMismatch
  FragmentTitleMisaligned = $fragmentTitleMisaligned
  EmptyGroupFragments = $emptyGroupFragmentCount
  SectionFragmentSpacingTooSmall = $sectionFragmentSpacingTooSmall
  NativeParticipants = $participantNativeCount
  NonNativeParticipants = $participantNonNativeCount
  ParticipantLifelinesWithExtraConnectionPoints = $participantLifelinesWithExtraConnectionPoints
  ParticipantLifelinesWithSparseConnectionPoints = $participantLifelinesWithSparseConnectionPoints
  ParticipantLifelinesWithNonUniformConnectionPointGap = $participantLifelinesWithNonUniformConnectionPointGap
  TextBearingMessages = $textBearingMessageCount
  MessagesWithoutConnectorGlue = $messagesWithoutConnectorGlue
  MessageArrowsOffConnectionGrid = $messageArrowsOffConnectionGrid
  CommonMethodMessagesOutsideRef = $commonMethodMessagesOutsideRef
  MessageArrowGapsTooSmall = $messageArrowGapsTooSmall
  SelfMessageDoubleSpacingViolations = $selfMessageDoubleSpacingViolations
  MessageArrowsTooCloseToOtherShapes = $messageArrowsTooCloseToOtherShapes
  MessagesCrossingAltOperandSeparators = $messagesCrossingAltOperandSeparators
  MessageLabelsNotAboveArrow = $messageLabelsNotAboveArrow
  MessageLabelsNotBlack = $messageLabelsNotBlack
  SelfMessagesWithoutTextControl = $selfMessagesWithoutTextControl
  SelfMessagesWithCenteredText = $selfMessagesWithCenteredText
  SelfMessagesNotOneConnectionPoint = $selfMessagesNotOneConnectionPoint
  ObjectLifelines = $objectLifelineCount
  ObjectLifelinesWithSparseConnectionPoints = $objectLifelinesWithSparseConnectionPoints
  ObjectLifelinesWithClusteredConnectionPoints = $objectLifelinesWithClusteredConnectionPoints
  MinObjectLifelineConnectionPointGap = $(if ($null -eq $minObjectLifelineConnectionPointGap) { $null } else { [Math]::Round([double]$minObjectLifelineConnectionPointGap, 4) })
  NativeConnectionPointUnit = [Math]::Round((Get-NativeConnectionPointUnit), 4)
  Masters = ($masterNames | Sort-Object -Unique) -join ', '
}

if ($errors.Count -gt 0) {
  $report | ConvertTo-Json -Depth 3 | Write-Output
  if ($env:VSDX_DEBUG_SPACING -eq '1' -and @($spacingDebugRows).Count -gt 0) {
    @($spacingDebugRows | Select-Object -First 30) | ConvertTo-Json -Depth 4 | Write-Output
  }
  throw "Native VSDX validation failed: $($errors -join '; ')"
}

$report | ConvertTo-Json -Depth 3 | Write-Output
Write-Output "native-visio validation passed: $full"
