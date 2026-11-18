# Copyright (C) 2026 Steve Prud'Homme
# SPDX-License-Identifier: GPL-3.0-or-later
# Nécessite TeX Live : XeLaTeX, Biber, biblatex-apa et les polices TeX Gyre.
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$sourceFolder = Join-Path $projectRoot 'docs/article-satellites'
$buildFolder = Join-Path $projectRoot 'local/article-build'
New-Item -ItemType Directory -Force -Path $buildFolder | Out-Null
$previousTemp = $env:TEMP
$previousTmp = $env:TMP
$env:TEMP = Join-Path $buildFolder 'temp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force -Path $env:TEMP | Out-Null
Push-Location $sourceFolder
try {
    & xelatex -interaction=nonstopmode -halt-on-error "-output-directory=$buildFolder" article.tex
    if ($LASTEXITCODE -ne 0) { throw 'Première compilation LaTeX échouée.' }
    & biber "--input-directory=$buildFolder" "--output-directory=$buildFolder" article
    if ($LASTEXITCODE -ne 0) { throw 'Construction de la bibliographie échouée.' }
    1..2 | ForEach-Object {
        & xelatex -interaction=nonstopmode -halt-on-error "-output-directory=$buildFolder" article.tex
        if ($LASTEXITCODE -ne 0) { throw 'Compilation finale LaTeX échouée.' }
    }
    Copy-Item -LiteralPath (Join-Path $buildFolder 'article.pdf') -Destination (Join-Path $sourceFolder 'article.pdf')
    Write-Output 'PDF construit. Vérifier son affichage avant publication.'
}
finally {
    Pop-Location
    $env:TEMP = $previousTemp
    $env:TMP = $previousTmp
}
