# Bibliometric Analysis System - Windows installer constants
$script:BibliometricsConfig = @{
    GitHubRepoUrl      = 'https://github.com/LuisMRaimundo/Bibliometrics'
    AppName            = 'Bibliometric Analysis System v16'
    PythonVersion      = '3.11'
    PythonMinMinor     = 10
    PythonMaxMinor     = 12
    PythonInstallerUrl = 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe'
    VenvFolder         = '.venv'
    PipExtras          = 'network,dashboard,enrichment'
    RunBatName         = 'run.bat'
}
