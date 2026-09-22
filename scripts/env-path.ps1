# Prepend Python and Node to PATH for this PowerShell session.
# Cursor shells started before install (or with a truncated PATH) often miss them.
# Docker is not required.

$pythonCandidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python314",
    "$env:LOCALAPPDATA\Programs\Python\Python313",
    "$env:LOCALAPPDATA\Programs\Python\Python312",
    "$env:LOCALAPPDATA\Programs\Python\Python311",
    "$env:ProgramFiles\Python314",
    "$env:ProgramFiles\Python313"
)
$nodeCandidates = @(
    "$env:ProgramFiles\nodejs"
)

foreach ($dir in $pythonCandidates) {
    if (Test-Path (Join-Path $dir "python.exe")) {
        $scripts = Join-Path $dir "Scripts"
        $env:PATH = "$dir;$scripts;" + $env:PATH
        break
    }
}

foreach ($dir in $nodeCandidates) {
    if (Test-Path (Join-Path $dir "node.exe")) {
        $env:PATH = "$dir;" + $env:PATH
        break
    }
}

function Get-OrqelisPython {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python -and $python.Source -notmatch "WindowsApps") {
        return $python.Source
    }
    if (Test-Path "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe") {
        return "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
    }
    if ($pyLauncher) {
        return $pyLauncher.Source
    }
    if ($python) {
        return $python.Source
    }
    throw "Python 3.11+ is not on PATH. Install it from https://www.python.org/downloads/ then re-run."
}
