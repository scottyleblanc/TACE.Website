#Requires -Version 7.0
<#
.SYNOPSIS
    Marks a training day as completed in DynamoDB.
.DESCRIPTION
    Updates the training-plan table to set completed=true and completed_date
    for a given date. Use this to retroactively check off a session that was
    not logged in the tracker UI.

    Reads the current item first and reports its state before writing.
    Supports -WhatIf to preview without writing.
.PARAMETER Date
    ISO date of the training day to mark complete (e.g. 2026-07-01).
    Defaults to yesterday.
.PARAMETER Table
    DynamoDB table name. Defaults to training-plan.
.PARAMETER Profile
    AWS CLI profile name. Defaults to tace-aws-admin.
.PARAMETER Region
    AWS region. Defaults to ca-central-1.
.EXAMPLE
    .\Complete-TrainingDay.ps1
    Marks yesterday complete.
.EXAMPLE
    .\Complete-TrainingDay.ps1 -Date 2026-07-01
.EXAMPLE
    .\Complete-TrainingDay.ps1 -Date 2026-07-01 -WhatIf
    Shows what would be updated without writing to DynamoDB.
.NOTES
    completed_date is set to the training date (not today) for retroactive accuracy.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string] $Date    = (Get-Date).AddDays(-1).ToString('yyyy-MM-dd'),
    [string] $Table   = 'training-plan',
    [string] $Profile = 'tace-aws-admin',
    [string] $Region  = 'ca-central-1'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$key        = '{"date":{"S":"' + $Date + '"}}'
$sharedArgs = @('--profile', $Profile, '--region', $Region)

# --- Read current state ---
Write-Host "[INFO]  Fetching $Date from '$Table'..."

$getArgs    = @('dynamodb', 'get-item', '--table-name', $Table, '--key', $key) + $sharedArgs
$getRaw     = aws @getArgs 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "[ERROR] AWS CLI failed: $getRaw"
}
$getResult = $getRaw | ConvertFrom-Json

if (-not $getResult.Item) {
    Write-Error "[ERROR] No training day found for '$Date'. Verify the date and table name."
}

$item        = $getResult.Item
$sessionType = $item.session_type.S
$isActive    = $item.is_active_day.BOOL
$completed   = $item.completed.BOOL

Write-Host "[INFO]  Date    : $Date"
Write-Host "[INFO]  Session : $sessionType"
Write-Host "[INFO]  Active  : $isActive"
Write-Host "[INFO]  Done    : $completed"

if (-not $isActive) {
    Write-Warning "$Date is a rest day -- marking it complete anyway."
}

if ($completed) {
    Write-Host "[INFO]  Already marked complete. Nothing to do."
    return
}

# --- Write ---
$exprValues = '{":c":{"BOOL":true},":d":{"S":"' + $Date + '"}}'

$updateArgs = @(
    'dynamodb', 'update-item',
    '--table-name',                 $Table,
    '--key',                        $key,
    '--update-expression',          'SET completed = :c, completed_date = :d',
    '--expression-attribute-values', $exprValues,
    '--condition-expression',       'attribute_exists(#pk)',
    '--expression-attribute-names', '{"#pk":"date"}',
    '--return-values',              'ALL_NEW'
) + $sharedArgs

if ($PSCmdlet.ShouldProcess("$Date ($sessionType)", 'Mark complete in DynamoDB')) {
    $updated      = aws @updateArgs | ConvertFrom-Json
    $newCompleted = $updated.Attributes.completed.BOOL
    $newDate      = $updated.Attributes.completed_date.S
    Write-Host "[OK]    $Date marked complete. completed=$newCompleted  completed_date=$newDate"
}
