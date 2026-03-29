# Quick Verification Script for Dataset Downloads
Write-Host ("=" * 70)
Write-Host "Dataset Download Verification"
Write-Host ("=" * 70)

$baseDir = "C:\Krishna_USA\Learning\DS\Masters\Research_papers\safesql\data\datasets"

# Check Spider
Write-Host "`nSpider Dataset:"
$spiderDir = Join-Path $baseDir "spider"
if (Test-Path $spiderDir) {
    $dev = Test-Path (Join-Path $spiderDir "dev.json")
    $train = Test-Path (Join-Path $spiderDir "train_spider.json")
    $tables = Test-Path (Join-Path $spiderDir "tables.json")
    $db = Test-Path (Join-Path $spiderDir "database")
    $dbCount = if ($db) { (Get-ChildItem (Join-Path $spiderDir "database") -Directory | Measure-Object).Count } else { 0 }
    
    Write-Host "  dev.json: $(if($dev){'FOUND'}else{'MISSING'})"
    Write-Host "  train_spider.json: $(if($train){'FOUND'}else{'MISSING'})"
    Write-Host "  tables.json: $(if($tables){'FOUND'}else{'MISSING'})"
    Write-Host "  database folder: $(if($db){'FOUND'}else{'MISSING'})"
    Write-Host "  Database count: $dbCount (expected: 200)"
    
    if ($dev -and $train -and $tables -and $db -and $dbCount -eq 200) {
        Write-Host "  Status: COMPLETE" -ForegroundColor Green
    } else {
        Write-Host "  Status: INCOMPLETE" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Status: DIRECTORY NOT FOUND" -ForegroundColor Red
}

# Check BIRD
Write-Host "`nBIRD Dataset:"
$birdDir = Join-Path $baseDir "bird"
if (Test-Path $birdDir) {
    $trainJson = Test-Path (Join-Path $birdDir "train\train.json")
    $devJson = Test-Path (Join-Path $birdDir "dev\dev.json")
    $dbDir = Test-Path (Join-Path $birdDir "dev_databases")
    $dbCount = if ($dbDir) { (Get-ChildItem (Join-Path $birdDir "dev_databases") -Directory | Measure-Object).Count } else { 0 }
    
    Write-Host "  train/train.json: $(if($trainJson){'FOUND'}else{'MISSING'})"
    Write-Host "  dev/dev.json: $(if($devJson){'FOUND'}else{'MISSING'})"
    Write-Host "  dev_databases folder: $(if($dbDir){'FOUND'}else{'MISSING'})"
    Write-Host "  Database count: $dbCount (expected: 95)"
    
    if ($trainJson -and $devJson -and $dbDir -and $dbCount -eq 95) {
        Write-Host "  Status: COMPLETE" -ForegroundColor Green
    } else {
        Write-Host "  Status: INCOMPLETE" -ForegroundColor Yellow
    }
} else {
    Write-Host "  Status: DIRECTORY NOT FOUND" -ForegroundColor Red
}

Write-Host ("`n" + ("=" * 70))
