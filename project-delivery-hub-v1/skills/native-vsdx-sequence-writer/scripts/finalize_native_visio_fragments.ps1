param(
  [Parameter(Mandatory = $true)]
  [string]$VsdxPath,

  [string]$PreviewPng = ''
  ,
  [string]$SpecPath = ''
)

$ErrorActionPreference = 'Stop'

$vsdxFull = (Resolve-Path $VsdxPath).Path
$previewFull = $null
$previewDir = $null
if (-not [string]::IsNullOrWhiteSpace($PreviewPng)) {
  $previewFull = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($PreviewPng)
  $previewDir = Split-Path -Parent $previewFull
  if (-not (Test-Path $previewDir)) {
    New-Item -ItemType Directory -Path $previewDir -Force | Out-Null
  }
}

$defaultConditionPlaceholder = ('[{0}{1}]' -f [char]0x689D, [char]0x4EF6)
$dashedSelfMessageTexts = @{}
$visibleSeparatorTexts = @{}
$frameLists = @()

function Normalize-MessageText([string]$Text) {
  return (($Text -replace '\s+', ' ').Trim())
}

function Format-ConditionOperandText([string]$Text) {
  $trimmed = Normalize-MessageText $Text
  if ([string]::IsNullOrWhiteSpace($trimmed)) { return '' }
  if ($trimmed.StartsWith('[') -and $trimmed.EndsWith(']')) { return $trimmed }
  return "[$trimmed]"
}

if (-not [string]::IsNullOrWhiteSpace($SpecPath) -and (Test-Path -LiteralPath $SpecPath)) {
  $spec = Get-Content -Raw -Encoding UTF8 -LiteralPath $SpecPath | ConvertFrom-Json
  $messageLists = @()
  $separatorLists = @()
  if ($null -ne $spec.pages) {
    foreach ($page in @($spec.pages)) {
      $messageLists += ,@($page.messages)
      $separatorLists += ,@($page.separators)
      $frameLists += ,@($page.frames)
    }
  }
  else {
    $messageLists += ,@($spec.messages)
    $separatorLists += ,@($spec.separators)
    $frameLists += ,@($spec.frames)
  }
  foreach ($messageList in $messageLists) {
    foreach ($message in @($messageList)) {
      if ([string]$message.kind -eq 'self' -and [bool]$message.dashed) {
        $textKey = Normalize-MessageText ([string]$message.text)
        if (-not [string]::IsNullOrWhiteSpace($textKey)) {
          $dashedSelfMessageTexts[$textKey] = $true
        }
      }
    }
  }
  foreach ($separatorList in $separatorLists) {
    foreach ($separator in @($separatorList)) {
      $textKey = Normalize-MessageText ([string]$separator.label)
      if (-not [string]::IsNullOrWhiteSpace($textKey)) {
        $visibleSeparatorTexts[$textKey] = $true
        $visibleSeparatorTexts[(Format-ConditionOperandText $textKey)] = $true
      }
    }
  }
}

function Hide-DefaultOperandPlaceholder($Shape) {
  try { $Shape.Text = '' } catch { }
  foreach ($cellName in @('LinePattern', 'FillPattern')) {
    try { $Shape.CellsU($cellName).FormulaU = '0' } catch { }
  }
  try { $Shape.CellsU('Width').FormulaU = '0.01 in' } catch { }
  try { $Shape.CellsU('Height').FormulaU = '0.01 in' } catch { }
  try { $Shape.CellsU('PinX').FormulaU = '-100 in' } catch { }
  try { $Shape.CellsU('PinY').FormulaU = '-100 in' } catch { }
}

function Hide-DefaultInteractionOperandPlaceholders($ShapeCollection) {
  $hidden = 0
  foreach ($shape in @($ShapeCollection)) {
    try {
      $masterName = ''
      try { $masterName = [string]$shape.Master.NameU } catch { }
      $text = ''
      try { $text = ([string]$shape.Text).Trim() } catch { }
      if ($masterName -match '(?i)^Interaction operand' -and $text -eq $script:defaultConditionPlaceholder) {
        Hide-DefaultOperandPlaceholder $shape
        $hidden++
      }
      try {
        if ($shape.Shapes.Count -gt 0) {
          $hidden += Hide-DefaultInteractionOperandPlaceholders $shape.Shapes
        }
      } catch { }
    } catch { }
  }
  return $hidden
}

function Get-ShapeBounds($Shape) {
  try {
    $pinX = [double]$Shape.CellsU('PinX').ResultIU
    $pinY = [double]$Shape.CellsU('PinY').ResultIU
    $width = [double]$Shape.CellsU('Width').ResultIU
    $height = [double]$Shape.CellsU('Height').ResultIU
    return [pscustomobject]@{
      Left = $pinX - ($width / 2.0)
      Right = $pinX + ($width / 2.0)
      Bottom = $pinY - ($height / 2.0)
      Top = $pinY + ($height / 2.0)
      CenterX = $pinX
      CenterY = $pinY
      Area = [Math]::Max(0.0001, [Math]::Abs($width * $height))
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

function Set-NativeShapeByTopDistances($Page, $Shape, [double]$Left, [double]$Right, [double]$TopDistance, [double]$BottomDistance) {
  $pageHeight = [double]$Page.PageSheet.CellsU('PageHeight').ResultIU
  $width = [Math]::Max(0.1, $Right - $Left)
  $height = [Math]::Max(0.05, $BottomDistance - $TopDistance)
  try { $Shape.CellsU('LocPinX').FormulaU = 'Width*0.5' } catch { }
  try { $Shape.CellsU('LocPinY').FormulaU = 'Height*0.5' } catch { }
  try { $Shape.CellsU('PinX').FormulaU = ("{0} in" -f ($Left + ($width / 2.0))) } catch { }
  try { $Shape.CellsU('PinY').FormulaU = ("{0} in" -f ($pageHeight - $TopDistance - ($height / 2.0))) } catch { }
  try { $Shape.CellsU('Width').FormulaU = ("{0} in" -f $width) } catch { }
  try { $Shape.CellsU('Height').FormulaU = ("{0} in" -f $height) } catch { }
}

function Snap-NativeFragmentFramesToGrid($Page) {
  $unit = Get-NativeConnectionPointUnit
  $pageHeight = [double]$Page.PageSheet.CellsU('PageHeight').ResultIU
  $changed = 0
  foreach ($shape in @($Page.Shapes)) {
    if (-not (Test-NativeFragmentFrameShape $shape)) { continue }
    $bounds = Get-ShapeBounds $shape
    if ($null -eq $bounds) { continue }
    $topDistance = $pageHeight - [double]$bounds.Top
    $bottomDistance = $pageHeight - [double]$bounds.Bottom
    $topSnap = Snap-ToNativeConnectionPoint $topDistance 'floor'
    $bottomSnap = Snap-ToNativeConnectionPoint $bottomDistance 'ceil'
    if ((Get-ShapeTextTrimmed $shape) -eq 'ref') {
      $topSnap = Snap-ToNativeConnectionPoint $topDistance
      $bottomSnap = $topSnap + ($unit * 6.0)
    }
    if ($bottomSnap -le ($topSnap + 0.01)) { $bottomSnap = $topSnap + $unit }
    if (
      [Math]::Abs($topDistance - $topSnap) -gt 0.005 -or
      [Math]::Abs($bottomDistance - $bottomSnap) -gt 0.005
    ) {
      $changed++
    }
    Set-NativeShapeByTopDistances $Page $shape ([double]$bounds.Left) ([double]$bounds.Right) $topSnap $bottomSnap
  }
  return $changed
}

function Test-NativeOperandInsideFrameLane($OperandBounds, $FrameBounds) {
  if ($null -eq $OperandBounds -or $null -eq $FrameBounds) { return $false }
  $operandWidth = [Math]::Max(0.01, [double]$OperandBounds.Right - [double]$OperandBounds.Left)
  $frameWidth = [Math]::Max(0.01, [double]$FrameBounds.Right - [double]$FrameBounds.Left)
  $horizontalOverlap = [Math]::Min([double]$OperandBounds.Right, [double]$FrameBounds.Right) - [Math]::Max([double]$OperandBounds.Left, [double]$FrameBounds.Left)
  if ($horizontalOverlap -lt ([Math]::Min($operandWidth, $frameWidth) * 0.40)) { return $false }

  # A branch operand belongs to the fragment whose lane starts under the native
  # clipped title/header area. The header is not a fixed 0.10 in band after
  # Visio materializes a UML Alternative fragment, so allow several native
  # connection-point rows before rejecting the operand as belonging elsewhere.
  $topSlack = [Math]::Max(0.85, (Get-NativeConnectionPointUnit) * 3.0)
  if ([double]$OperandBounds.Top -gt ([double]$FrameBounds.Top + $topSlack)) { return $false }
  if ([double]$OperandBounds.Top -lt ([double]$FrameBounds.Bottom - 0.10)) { return $false }
  return $true
}

function Get-ShapeMasterName($Shape) {
  try { return [string]$Shape.Master.NameU } catch { return '' }
}

function Get-ShapeTextTrimmed($Shape) {
  try { return ([string]$Shape.Text).Trim() } catch { return '' }
}

function Test-NativeFragmentFrameShape($Shape) {
  $masterName = Get-ShapeMasterName $Shape
  return ($masterName -match '(?i)(Alternative fragment|Optional fragment|Loop fragment|Other fragment)')
}

function Test-FrameSpecMatchesShape($FrameSpec, $ShapeInfo) {
  $kind = [string]$FrameSpec.kind
  $label = [string]$FrameSpec.label
  $text = [string]$ShapeInfo.Text
  $masterName = [string]$ShapeInfo.MasterName
  switch ($kind) {
    'alt' { return ($text -eq 'alt' -and $masterName -match '(?i)^Alternative fragment') }
    'opt' { return ($text -eq 'opt' -and $masterName -match '(?i)^Alternative fragment') }
    'ref' { return ($text -eq 'ref') }
    default {
      if ($label -in @('alt', 'opt', 'ref')) { return ($text -eq $label) }
      return ($masterName -match '(?i)^Other fragment')
    }
  }
}

function Restore-NativeFragmentFrameBoundsFromSpec($Page, $FrameSpecs) {
  $specFrames = @($FrameSpecs | Where-Object { $null -ne $_ } | Sort-Object { [double]$_.top })
  if ($specFrames.Count -eq 0) { return 0 }
  $pageHeight = [double]$Page.PageSheet.CellsU('PageHeight').ResultIU
  $shapeInfos = @()
  foreach ($shape in @($Page.Shapes)) {
    if (-not (Test-NativeFragmentFrameShape $shape)) { continue }
    $bounds = Get-ShapeBounds $shape
    if ($null -eq $bounds) { continue }
    $shapeInfos += [pscustomobject]@{
      Shape = $shape
      Bounds = $bounds
      TopDistance = [double]$pageHeight - [double]$bounds.Top
      Text = Get-ShapeTextTrimmed $shape
      MasterName = Get-ShapeMasterName $shape
      Used = $false
    }
  }
  $shapeInfos = @($shapeInfos | Sort-Object TopDistance)
  $restored = 0
  foreach ($frame in $specFrames) {
    $candidate = $null
    foreach ($info in $shapeInfos) {
      if ($info.Used) { continue }
      if (Test-FrameSpecMatchesShape $frame $info) {
        $candidate = $info
        break
      }
    }
    if ($null -eq $candidate) {
      foreach ($info in $shapeInfos) {
        if (-not $info.Used) {
          $candidate = $info
          break
        }
      }
    }
    if ($null -eq $candidate) { continue }
    $candidate.Used = $true
    $topDistance = Snap-ToNativeConnectionPoint ([double]$frame.top)
    $bottomDistance = $topDistance
    if ([string]$frame.kind -eq 'ref' -or [string]$frame.label -eq 'ref') {
      $bottomDistance = $topDistance + ((Get-NativeConnectionPointUnit) * 6.0)
    }
    else {
      $bottomDistance = Snap-ToNativeConnectionPoint ([double]$frame.top + [double]$frame.height)
      if ($bottomDistance -le ($topDistance + 0.01)) {
        $bottomDistance = $topDistance + (Get-NativeConnectionPointUnit)
      }
    }
    $left = [double]$frame.left
    $right = $left + [double]$frame.width
    Set-NativeShapeByTopDistances $Page $candidate.Shape $left $right $topDistance $bottomDistance
    $restored++
  }
  return $restored
}

function Test-NativeOperandOwnerFrame($Shape) {
  $text = Get-ShapeTextTrimmed $Shape
  $masterName = Get-ShapeMasterName $Shape
  return (
    ($text -eq 'alt' -and $masterName -match '(?i)^Alternative fragment') -or
    ($text -eq 'opt' -and $masterName -match '(?i)^(Alternative fragment|Optional fragment)')
  )
}

function Test-ExcludeFromFragmentMembership($Shape) {
  $masterName = Get-ShapeMasterName $Shape
  $text = Get-ShapeTextTrimmed $Shape
  if ($masterName -match '(?i)lifeline') { return $true }
  if ([string]::IsNullOrWhiteSpace($masterName) -and [string]::IsNullOrWhiteSpace($text)) {
    $width = 0.0
    $height = 0.0
    try { $width = [double]$Shape.CellsU('Width').ResultIU } catch { }
    try { $height = [double]$Shape.CellsU('Height').ResultIU } catch { }
    if ($width -gt 6.0 -and $height -lt 0.08) { return $true }
  }
  if ($text -in @('User', 'APP', 'Enterprise', 'BillHub', 'IRIS', 'DB', 'Redis')) { return $true }
  return $false
}

function Add-NativeFragmentMember($FrameShape, $MemberShape) {
  try { $FrameShape.ContainerProperties.LockMembership = $false } catch { }
  try { $FrameShape.ContainerProperties.ResizeAsNeeded = 0 } catch { }
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
    return $true
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

function Add-NativeFragmentMemberships($Page) {
  $added = 0
  $frames = @()
  foreach ($shape in @($Page.Shapes)) {
    if (Test-NativeFragmentFrameShape $shape) {
      $bounds = Get-ShapeBounds $shape
      if ($null -ne $bounds) {
        $frames += [pscustomobject]@{ Shape = $shape; Bounds = $bounds; Area = $bounds.Area }
      }
    }
  }
  if ($frames.Count -eq 0) { return 0 }

  $operandAssignments = @{}
  foreach ($frame in $frames) {
    try { $operandAssignments[[int]$frame.Shape.ID] = @() } catch { }
  }

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
      $alreadyNativeListOperand = $false
      if ($candidateIsOperand -and (Test-NativeOperandOwnerFrame $parent.Shape)) {
        $alreadyNativeListOperand = Test-NativeFragmentListMember $parent.Shape $candidate
      }
      if (-not $alreadyNativeListOperand) {
        if (Add-NativeFragmentMember $parent.Shape $candidate) { $added++ }
      }
      if ($candidateIsOperand -and (Test-NativeOperandOwnerFrame $parent.Shape)) {
        $parentId = [int]$parent.Shape.ID
        $operandAssignments[$parentId] = @($operandAssignments[$parentId]) + [pscustomobject]@{
          Shape = $candidate
          Bounds = $candidateBounds
        }
      }
    }
  }

  foreach ($frame in $frames) {
    if (-not (Test-NativeOperandOwnerFrame $frame.Shape)) { continue }
    $frameId = [int]$frame.Shape.ID
    $operands = @($operandAssignments[$frameId] | Sort-Object @{ Expression = { [double]$_.Bounds.Top }; Descending = $true })
    if ($operands.Count -eq 0) { continue }

    for ($i = 0; $i -lt $operands.Count; $i++) {
      $operandShape = $operands[$i].Shape
      if (-not (Insert-NativeFragmentListMember $frame.Shape $operandShape ($i + 1))) {
        continue
      }
      if ($i -eq 0) {
        try { $operandShape.CellsU('LinePattern').FormulaForceU = '0' } catch { }
      }
      else {
        try { $operandShape.CellsU('LinePattern').FormulaForceU = '2' } catch { }
        try { $operandShape.CellsU('LineColor').FormulaForceU = 'RGB(30,80,84)' } catch { }
      }
    }
    try { $frame.Shape.ContainerProperties.ResizeAsNeeded = 0 } catch { }
    try { $frame.Shape.ContainerProperties.LockMembership = $true } catch { }
  }
  return $added
}

function Apply-DashedSelfMessageOverrides($Page) {
  $changed = 0
  if ($script:dashedSelfMessageTexts.Count -le 0) { return 0 }
  foreach ($shape in @($Page.Shapes)) {
    $masterName = Get-ShapeMasterName $shape
    if ($masterName -notmatch '^Self Message') { continue }
    $textKey = Normalize-MessageText (Get-ShapeTextTrimmed $shape)
    if ($script:dashedSelfMessageTexts.ContainsKey($textKey)) {
      try { $shape.CellsU('LinePattern').FormulaForceU = '2' } catch { }
      try { $shape.CellsU('LineColor').FormulaForceU = 'RGB(176,21,19)' } catch { }
      $changed++
    }
  }
  return $changed
}

function Bring-VisualSeparatorsToFront($Page) {
  $changed = 0
  foreach ($shape in @($Page.Shapes)) {
    $nameU = ''
    try { $nameU = [string]$shape.NameU } catch { }
    if ($nameU -match '^section-divider-(line|title)-') {
      try { $shape.BringToFront() } catch { }
      $changed++
      continue
    }
    if ((Get-ShapeMasterName $shape) -notmatch '(?i)^Interaction operand') { continue }
    $textKey = Normalize-MessageText (Get-ShapeTextTrimmed $shape)
    if ($script:visibleSeparatorTexts.ContainsKey($textKey)) {
      try { $shape.CellsU('LinePattern').FormulaForceU = '2' } catch { }
      try { $shape.CellsU('LineColor').FormulaForceU = 'RGB(30,80,84)' } catch { }
      try { $shape.BringToFront() } catch { }
      $changed++
    }
  }
  return $changed
}

function Remove-PureYellowPreviewArtifacts([string]$ImagePath) {
  try { Add-Type -AssemblyName System.Drawing } catch { return 0 }
  $bitmap = $null
  $removed = 0
  try {
    $bitmap = [System.Drawing.Bitmap]::new($ImagePath)
    $white = [System.Drawing.Color]::FromArgb(255, 255, 255)
    for ($x = 0; $x -lt $bitmap.Width; $x++) {
      for ($y = 0; $y -lt $bitmap.Height; $y++) {
        $pixel = $bitmap.GetPixel($x, $y)
        if ($pixel.R -eq 255 -and $pixel.G -eq 255 -and $pixel.B -eq 0) {
          $bitmap.SetPixel($x, $y, $white)
          $removed++
        }
      }
    }
    if ($removed -gt 0) {
      $tempPath = [System.IO.Path]::Combine(
        [System.IO.Path]::GetDirectoryName($ImagePath),
        ([System.IO.Path]::GetFileNameWithoutExtension($ImagePath) + '.cleaning.tmp.png')
      )
      $bitmap.Save($tempPath, [System.Drawing.Imaging.ImageFormat]::Png)
      $bitmap.Dispose()
      $bitmap = $null
      Move-Item -LiteralPath $tempPath -Destination $ImagePath -Force
    }
  }
  finally {
    if ($bitmap -ne $null) { $bitmap.Dispose() }
  }
  return $removed
}

function Join-PngsVertical([string[]]$ImagePaths, [string]$OutputPath) {
  if ($ImagePaths.Count -le 0) { return }
  Add-Type -AssemblyName System.Drawing
  $bitmaps = @()
  $canvas = $null
  $graphics = $null
  try {
    foreach ($path in $ImagePaths) {
      $bitmaps += [System.Drawing.Bitmap]::new($path)
    }
    $width = 0
    $height = 0
    foreach ($bitmap in $bitmaps) {
      if ($bitmap.Width -gt $width) { $width = $bitmap.Width }
      $height += $bitmap.Height
    }
    $canvas = [System.Drawing.Bitmap]::new($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($canvas)
    $graphics.Clear([System.Drawing.Color]::White)
    $offsetY = 0
    foreach ($bitmap in $bitmaps) {
      $graphics.DrawImage($bitmap, 0, $offsetY, $bitmap.Width, $bitmap.Height)
      $offsetY += $bitmap.Height
    }
    $canvas.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)
  }
  finally {
    if ($graphics -ne $null) { $graphics.Dispose() }
    if ($canvas -ne $null) { $canvas.Dispose() }
    foreach ($bitmap in $bitmaps) {
      if ($bitmap -ne $null) { $bitmap.Dispose() }
    }
  }
}

$visio = $null
$doc = $null
try {
  $visio = New-Object -ComObject Visio.Application
  $visio.Visible = $false
  $visio.AlertResponse = 7
  $doc = $visio.Documents.OpenEx($vsdxFull, 128)
  $hidden = 0
  $membersAdded = 0
  $dashedSelfMessages = 0
  $visualSeparatorsRaised = 0
  $fragmentsSnapped = 0
  $framesRestored = 0
  for ($pageIndex = 1; $pageIndex -le $doc.Pages.Count; $pageIndex++) {
    $page = $doc.Pages.Item($pageIndex)
    Set-NativeConnectionPointUnit (Get-PageParticipantConnectionPointUnit $page)
    $membersAdded += Add-NativeFragmentMemberships $page
    $dashedSelfMessages += Apply-DashedSelfMessageOverrides $page
    $hidden += Hide-DefaultInteractionOperandPlaceholders $page.Shapes
    $membersAdded += Add-NativeFragmentMemberships $page
    $visualSeparatorsRaised += Bring-VisualSeparatorsToFront $page
  }
  if ($hidden -gt 0 -or $membersAdded -gt 0 -or $dashedSelfMessages -gt 0 -or $visualSeparatorsRaised -gt 0 -or $fragmentsSnapped -gt 0 -or $framesRestored -gt 0) {
    $doc.Save() | Out-Null
  }
  try { $visio.ActiveWindow.DeselectAll() | Out-Null } catch { }
  try { $visio.ActiveWindow.ShowShapeHandles = $false } catch { }
  $previewArtifactsRemoved = 0
  if ($previewFull -ne $null) {
    $pagePreviewFiles = @()
    $previewBase = [System.IO.Path]::Combine(
      $previewDir,
      ([System.IO.Path]::GetFileNameWithoutExtension($previewFull))
    )
    for ($pageIndex = 1; $pageIndex -le $doc.Pages.Count; $pageIndex++) {
      $page = $doc.Pages.Item($pageIndex)
      $pagePreview = ("{0}.page-{1:00}.tmp.png" -f $previewBase, $pageIndex)
      Remove-Item -LiteralPath $pagePreview -Force -ErrorAction SilentlyContinue
      $page.Export($pagePreview) | Out-Null
      $previewArtifactsRemoved += Remove-PureYellowPreviewArtifacts $pagePreview
      $pagePreviewFiles += $pagePreview
    }
    Join-PngsVertical $pagePreviewFiles $previewFull
    foreach ($pagePreview in $pagePreviewFiles) {
      Remove-Item -LiteralPath $pagePreview -Force -ErrorAction SilentlyContinue
    }
  }
  $previewStatus = if ($previewFull -ne $null) { "previewArtifactsRemoved=$previewArtifactsRemoved" } else { 'previewSkipped=true' }
  Write-Output "native-fragment-finalize: pages=$($doc.Pages.Count) membersAdded=$membersAdded dashedSelfMessages=$dashedSelfMessages fragmentsSnapped=$fragmentsSnapped framesRestored=$framesRestored visualSeparatorsRaised=$visualSeparatorsRaised hiddenDefaultOperands=$hidden $previewStatus"
}
finally {
  if ($doc -ne $null) { $doc.Close() }
  if ($visio -ne $null) { $visio.Quit() }
}
