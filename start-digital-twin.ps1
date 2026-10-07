param([int]$ApiPort = 8000, [int]$DashboardPort = 8501)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path $PSScriptRoot).Path
$ApiUrl = "http://127.0.0.1:$ApiPort"
$DashboardUrl = "http://127.0.0.1:$DashboardPort"
$Started = @()
function Resolve-ProjectPython {
  $candidates=@()
  if($env:DIGITAL_TWIN_PYTHON){$candidates+=@{source="DIGITAL_TWIN_PYTHON";path=$env:DIGITAL_TWIN_PYTHON}}
  if($env:CONDA_PREFIX){$candidates+=@{source="CONDA_PREFIX";path=(Join-Path $env:CONDA_PREFIX "python.exe")}}
  if($env:VIRTUAL_ENV){$candidates+=@{source="VIRTUAL_ENV";path=(Join-Path $env:VIRTUAL_ENV "Scripts\python.exe")}}
  foreach($n in @("python","py")){$c=Get-Command $n -ErrorAction SilentlyContinue;if($c){$candidates+=@{source="PATH $n";path=$c.Source}}}
  foreach($candidate in $candidates){
    if(-not(Test-Path -LiteralPath $candidate.path -PathType Leaf)){continue}
    $previous=$env:PYTHONPATH;$env:PYTHONPATH=Join-Path $Root "src"
    try{$old=$ErrorActionPreference;$ErrorActionPreference="Continue";& $candidate.path -c "import digital_twin, fastapi, streamlit, sqlalchemy, uvicorn" 2>&1|Out-Null;$code=$LASTEXITCODE;$ErrorActionPreference=$old;if($code-eq 0){Write-Host "Selected Python: $($candidate.path) [$($candidate.source)]";return $candidate.path}}finally{if($previous){$env:PYTHONPATH=$previous}else{Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue}}
  }
  throw "No usable project Python was found. Set DIGITAL_TWIN_PYTHON or activate the project environment; dependencies will not be installed automatically."
}
function Test-Http([string]$Url){try{return Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3}catch{return $null}}
function Test-Port([int]$Port){try{return [bool](Test-NetConnection 127.0.0.1 -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue)}catch{return $false}}
function Wait-For([scriptblock]$Check,[int]$Attempts=30){for($i=0;$i-lt$Attempts;$i++){if(& $Check){return $true};Start-Sleep 2};return $false}
function Get-ApiReady{$response=Test-Http "$ApiUrl/health/ready";if(-not$response-or$response.StatusCode-ne 200){return $false};try{$payload=$response.Content|ConvertFrom-Json;return $payload.service-eq"course-digital-twin-api"-and@("postgres","postgresql","sqlite")-contains[string]$payload.database_backend}catch{return $false}}
function Start-ServiceProcess([string]$Python,[string]$Arguments,[hashtable]$Environment){$info=[Diagnostics.ProcessStartInfo]::new($Python,$Arguments);$info.WorkingDirectory=$Root;$info.UseShellExecute=$false;foreach($key in $Environment.Keys){$info.Environment[$key]=[string]$Environment[$key]};$process=[Diagnostics.Process]::Start($info);$script:Started+=$process.Id}
$python=Resolve-ProjectPython
if(-not$env:DIGITAL_TWIN_DATABASE_URL){throw "DIGITAL_TWIN_DATABASE_URL is required. Start the intended PostgreSQL instance first; this launcher will not create, recreate, migrate, or reset a database."}
$common=@{PYTHONPATH=(Join-Path $Root "src")}
foreach($name in @("DIGITAL_TWIN_AUTH_FILE","DIGITAL_TWIN_API_KEY_FILE","DIGITAL_TWIN_PRESENTATION_ID")){$value=[Environment]::GetEnvironmentVariable($name);if($value){$common[$name]=$value}}
if((Test-Port $ApiPort)-and-not(Get-ApiReady)){throw "Port $ApiPort is occupied by a process that is not the expected Digital Twin API. Stop it manually before retrying."}
if(-not(Get-ApiReady)){$apiEnvironment=@{}+$common;$apiEnvironment["DIGITAL_TWIN_DATABASE_URL"]=$env:DIGITAL_TWIN_DATABASE_URL;Start-ServiceProcess $python "-m uvicorn digital_twin.api.app:app --app-dir src --host 127.0.0.1 --port $ApiPort" $apiEnvironment;if(-not(Wait-For {Get-ApiReady})){throw "API did not become ready at $ApiUrl. Inspect its process output; the launcher did not change the database."}}else{Write-Host "API already healthy at $ApiUrl"}
if((Test-Port $DashboardPort)-and-not(Test-Http "$DashboardUrl/_stcore/health")){throw "Port $DashboardPort is occupied by a process that is not the expected Streamlit dashboard. Stop it manually before retrying."}
if(-not(Test-Http "$DashboardUrl/_stcore/health")){$dashboardEnvironment=@{}+$common;$dashboardEnvironment["DIGITAL_TWIN_API_URL"]=$ApiUrl;Start-ServiceProcess $python "-m streamlit run src/digital_twin/dashboard/app.py --server.address 127.0.0.1 --server.port $DashboardPort --server.headless true --browser.gatherUsageStats false" $dashboardEnvironment;if(-not(Wait-For {Test-Http "$DashboardUrl/_stcore/health"})){throw "Dashboard did not become ready at $DashboardUrl. Inspect its process output."}}else{Write-Host "Dashboard already healthy at $DashboardUrl"}
Write-Host "Digital Twin empirical runtime is ready.";Write-Host "API: $ApiUrl";Write-Host "Dashboard: $DashboardUrl";if($Started.Count){Write-Host("Started PID(s): "+($Started-join", "))}else{Write-Host "Started PID(s): none; existing healthy services reused."}
