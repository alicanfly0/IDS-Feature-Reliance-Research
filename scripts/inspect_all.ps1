# Run the dataset inspection on every downloaded file and save the reports.
#
#   powershell -ExecutionPolicy Bypass -File scripts\inspect_all.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\inspect_all.ps1 -Only unsw_train,nf_v2
#
# Reports go to results\inspection\<name>.txt and .json. Files are inspected one
# at a time (not concatenated) to keep memory use per run to roughly 1-2 GB.
# Entries whose data is missing are skipped.
param([string[]]$Only = @())
$ErrorActionPreference = "Stop"
$Only = @($Only | ForEach-Object { $_ -split "," } | Where-Object { $_ })  # -File passes "a,b" as one string
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root ".venv\Scripts\python.exe"
$Out = Join-Path $Root "results\inspection"
New-Item -ItemType Directory -Force $Out | Out-Null

$Raw = Join-Path $Root "data\raw"
$UnswNames = Join-Path $Raw "unsw_nb15\NUSW-NB15_features.csv"
$Jobs = @(
    @{ name = "unsw_train";  path = "unsw_nb15\UNSW_NB15_training-set.csv"; args = @("--label", "label") },
    @{ name = "unsw_test";   path = "unsw_nb15\UNSW_NB15_testing-set.csv";  args = @("--label", "label") },
    @{ name = "unsw_full_1"; path = "unsw_nb15\UNSW-NB15_1.csv"; args = @("--label", "Label", "--names-from", $UnswNames) },
    @{ name = "unsw_full_2"; path = "unsw_nb15\UNSW-NB15_2.csv"; args = @("--label", "Label", "--names-from", $UnswNames) },
    @{ name = "unsw_full_3"; path = "unsw_nb15\UNSW-NB15_3.csv"; args = @("--label", "Label", "--names-from", $UnswNames) },
    @{ name = "unsw_full_4"; path = "unsw_nb15\UNSW-NB15_4.csv"; args = @("--label", "Label", "--names-from", $UnswNames) },
    @{ name = "nf_v2";       path = "nf_unsw_nb15_v2\extracted\fe6cb615d161452c_MOHANAD_A4706\data\NF-UNSW-NB15-v2.csv"; args = @("--label", "Label") }
)
# Engelen WTMC2021 corrected CICIDS2017: one report per day file.
$EngDir = Join-Path $Raw "cicids2017_engelen_wtmc2021\extracted"
if (Test-Path $EngDir) {
    foreach ($f in Get-ChildItem $EngDir -Filter *.csv | Sort-Object Name) {
        $short = ($f.BaseName -replace "-WorkingHours", "").ToLower()
        $Jobs += @{ name = "engelen_$short"; path = $f.FullName.Substring($Raw.Length + 1); args = @("--label", "Label") }
    }
}
# CIC-IDS2017 original: one report per capture-day file, for both CSV releases
# (MachineLearningCVE = no identifiers; TrafficLabelling = with Flow ID/IPs/ports/timestamp).
foreach ($pair in @(@("MachineLearningCVE", "cic2017_"), @("TrafficLabelling", "cic2017_glf_"))) {
    $CicDir = Join-Path $Raw "cicids2017_original\extracted\$($pair[0])"
    if (-not (Test-Path $CicDir)) { continue }
    foreach ($f in Get-ChildItem $CicDir -Filter *.csv | Sort-Object Name) {
        $short = ($f.BaseName -replace "\.pcap_ISCX$", "" -replace "-WorkingHours", "" -replace "workingHours", "").Trim("-").ToLower()
        $Jobs += @{ name = "$($pair[1])$short"; path = $f.FullName.Substring($Raw.Length + 1); args = @("--label", "Label") }
    }
}

foreach ($job in $Jobs) {
    if ($Only.Count -and $Only -notcontains $job.name) { continue }
    $path = Join-Path $Raw $job.path
    if (-not (Test-Path $path)) { Write-Host "skip $($job.name): $path not found"; continue }
    Write-Host "inspecting $($job.name) ..."
    $json = Join-Path $Out "$($job.name).json"
    & $Py -I -m src.data.inspection $path @($job.args) --json $json --txt (Join-Path $Out "$($job.name).txt") | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "inspection failed for $($job.name)" }
}
Write-Host "reports in $Out"
