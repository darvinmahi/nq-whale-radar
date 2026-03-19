$basePath = 'C:\Users\FxDarvin\.gemini\antigravity\skills'
if (!(Test-Path $basePath)) { New-Item -ItemType Directory -Force -Path $basePath }

$tempDir = Join-Path $basePath "temp_large_collection"
if (Test-Path $tempDir) { Remove-Item -Path $tempDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $tempDir

$repoUrl = "https://github.com/sickn33/antigravity-awesome-skills/archive/refs/heads/main.zip"
$repoZip = Join-Path $tempDir "repo_large.zip"

Write-Host "Downloading the massive skills collection (946+ skills) from $repoUrl..."
try {
    # Large download might take time
    Invoke-WebRequest -Uri $repoUrl -OutFile $repoZip -ErrorAction Stop
    
    Write-Host "Extracting collection..."
    Expand-Archive -Path $repoZip -DestinationPath $tempDir -Force
    
    $extractedRepoDir = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -like "antigravity-awesome-skills-main" }
    $sourceSkillsDir = Join-Path $extractedRepoDir.FullName "skills"
    
    if (Test-Path $sourceSkillsDir) {
        Write-Host "Copying all skills to the global directory..."
        # Copying many small folders
        Get-ChildItem -Path $sourceSkillsDir -Directory | ForEach-Object {
            $destPath = Join-Path $basePath $_.Name
            Write-Host "Installing $($_.Name)..."
            if (Test-Path $destPath) { Remove-Item -Path $destPath -Recurse -Force }
            Copy-Item -Path $_.FullName -Destination $basePath -Recurse -Force
        }
        Write-Host "Successfully installed the entire collection."
    } else {
        Write-Error "Source skills directory not found in the repository archive."
    }
} catch {
    Write-Error "Failed to process the massive collection: $($_.Exception.Message)"
} finally {
    Write-Host "Cleaning up temporary files..."
    if (Test-Path $tempDir) { Remove-Item -Path $tempDir -Recurse -Force }
}
