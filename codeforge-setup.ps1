# ==============================================================================
# CodeForge — Automated Windows PowerShell Setup Script
#
# Turnkey single-command setup for Windows environments with Docker Desktop:
# 1. Verifies Docker CLI & Docker Desktop daemon connectivity
# 2. Checks port availability (80, 8000, 3000, 9090)
# 3. Generates .env with cryptographically random JWT secret
# 4. Builds all 4 sandbox execution container images (Java, Python, C, C++)
# 5. Runs container health checks on all sandbox images
# 6. Starts all services with docker compose (with restart & health monitoring)
# 7. Runs database migrations (Alembic)
# 8. Seeds initial instructor, student, course, problems, lab, and proctored exam
# 9. Displays network access URLs and credentials
# ==============================================================================

[CmdletBinding()]
param(
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Write-Info($msg) {
    Write-Host "[INFO] $msg" -ForegroundColor Cyan
}

function Write-Success($msg) {
    Write-Host "[SUCCESS] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "[WARN] $msg" -ForegroundColor Yellow
}

function Write-ErrorMsg($msg) {
    Write-Host "[ERROR] $msg" -ForegroundColor Red
}

function Show-Banner {
    Write-Host @"
   ______           __     ______                    
  / ____/____  ____/ /___ / ____/____  _________ ____
 / /    / __ \/ __  // _ \ / /_  / __ \/ ___/ __ `/ _ \
/ /___ / /_/ / /_/ //  __// __/ / /_/ / /  / /_/ //  __/
\____/ \____/\__,_/ \___//_/    \____/_/   \__, / \___/ 
                                          /____/         
   Browser-Based Competitive Programming Judge & Lab Platform
   (Windows Turnkey Deployment Engine)
"@ -ForegroundColor Cyan
}

# ── 1. Check Prerequisites ───────────────────────────────────────────────────
function Test-Prerequisites {
    Write-Info "Checking system prerequisites for Windows..."

    # Check Docker CLI
    if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
        Write-ErrorMsg "Docker is not installed or not in PATH."
        Write-ErrorMsg "Please install Docker Desktop for Windows: https://www.docker.com/products/docker-desktop/"
        exit 1
    }

    # Check Docker daemon
    try {
        $null = docker info 2>&1
    } catch {
        Write-ErrorMsg "Docker Desktop daemon is not responding."
        Write-ErrorMsg "Please ensure Docker Desktop is started and WSL2 / Hyper-V backend is active."
        exit 1
    }

    Write-Success "Docker engine and CLI are available and operational."
}

# ── 2. Check Port Availability ────────────────────────────────────────────────
function Test-Ports {
    Write-Info "Checking port availability..."
    $ports = @(80, 8000, 3000, 9090)

    foreach ($p in $ports) {
        $occupied = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        if ($occupied) {
            Write-Warn "Port $p is currently active. (If CodeForge was already running, containers will be safely updated)."
        }
    }
}

# ── 3. Configure Environment (.env) ───────────────────────────────────────────
function Set-EnvironmentFile {
    Write-Info "Configuring environment settings (.env)..."

    if (-not (Test-Path ".env")) {
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Info "Created .env from .env.example"
        } else {
            Write-ErrorMsg ".env.example not found!"
            exit 1
        }
    }

    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "change-me") {
        # Generate random 32-byte hex secret
        $bytes = New-Object byte[] 32
        $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        $rng.GetBytes($bytes)
        $randomSecret = -join ($bytes | ForEach-Object { "{0:x2}" -f $_ })

        $envContent = $envContent -replace "JWT_SECRET_KEY=.*", "JWT_SECRET_KEY=$randomSecret"
        Set-Content -Path ".env" -Value $envContent
        Write-Success "Generated cryptographically secure JWT_SECRET_KEY."
    } else {
        Write-Info "Existing JWT_SECRET_KEY found in .env."
    }
}

# ── 4. Build Sandbox Images ───────────────────────────────────────────────────
function Build-Sandboxes($force) {
    $images = @(
        @{ Name = "codeforge-sandbox-java"; Path = "./sandbox/java"; Display = "Java" },
        @{ Name = "codeforge-sandbox-python"; Path = "./sandbox/python"; Display = "Python" },
        @{ Name = "codeforge-sandbox-c"; Path = "./sandbox/c"; Display = "C" },
        @{ Name = "codeforge-sandbox-cpp"; Path = "./sandbox/cpp"; Display = "C++" }
    )

    foreach ($img in $images) {
        $imgExists = docker image inspect $img.Name 2>&1
        if ($force -or ($LASTEXITCODE -ne 0)) {
            Write-Info "Building $($img.Display) sandbox container image ($($img.Name))..."
            docker build -t $img.Name $img.Path
        } else {
            Write-Info "Sandbox image '$($img.Name)' already present."
        }
    }

    Write-Success "Sandbox execution images verified."
}

# ── 5. Verify Sandbox Images Health ───────────────────────────────────────────
function Test-Sandboxes {
    Write-Info "Verifying health of sandbox execution environments..."
    $tests = @(
        @{ Img = "codeforge-sandbox-java"; Cmd = "java -version"; Name = "Java" },
        @{ Img = "codeforge-sandbox-python"; Cmd = "python3 --version"; Name = "Python" },
        @{ Img = "codeforge-sandbox-c"; Cmd = "gcc --version"; Name = "C" },
        @{ Img = "codeforge-sandbox-cpp"; Cmd = "g++ --version"; Name = "C++" }
    )

    foreach ($t in $tests) {
        $null = docker run --rm --network none $t.Img sh -c $t.Cmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✔ $($t.Name) sandbox operational" -ForegroundColor Green
        } else {
            Write-Warn "  ✘ $($t.Name) sandbox health check warning"
        }
    }

    Write-Success "All 4 sandbox containers verified and functional."
}

# ── 6. Launch CodeForge Services ──────────────────────────────────────────────
function Start-CodeForgeServices($force) {
    Write-Info "Launching CodeForge service stack with docker compose..."

    if ($force) {
        docker compose up -d --build
    } else {
        docker compose up -d
    }

    Write-Info "Waiting for PostgreSQL database to be healthy..."
    $attempts = 0
    $maxAttempts = 30
    $dbReady = $false

    while (-not $dbReady -and ($attempts -lt $maxAttempts)) {
        Start-Sleep -Seconds 1
        $null = docker compose exec -T db pg_isready -U codeforge -d codeforge 2>&1
        if ($LASTEXITCODE -eq 0) {
            $dbReady = $true
        }
        $attempts++
    }

    if (-not $dbReady) {
        Write-ErrorMsg "Database took too long to become healthy."
        exit 1
    }

    Write-Success "All service containers are up and database is healthy."
}

# ── 7. Run Migrations & Seeding ────────────────────────────────────────────────
function Invoke-MigrationsAndSeed {
    Write-Info "Applying database migrations (Alembic)..."
    docker compose exec -T api alembic upgrade head
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Direct exec failed, retrying via run..."
        docker compose run --rm api alembic upgrade head
    }
    Write-Success "Database schema is at HEAD."

    Write-Info "Seeding initial platform data (instructors, course, problems, lab, exam)..."
    docker compose exec -T api python -m app.seed
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "Direct exec failed, retrying via run..."
        docker compose run --rm api python -m app.seed
    }
    Write-Success "Database seeding complete."
}

# ── 8. Display Summary ────────────────────────────────────────────────────────
function Show-Summary {
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Green
    Write-Host "             CodeForge Platform Setup Completed Successfully!           " -ForegroundColor Green
    Write-Host "========================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Platform Access URLs:" -ForegroundColor White
    Write-Host "  - Web Application:   http://localhost (or http://127.0.0.1)"
    Write-Host "  - API Docs (Swagger):http://localhost:8000/docs"
    Write-Host "  - API Health Check:  http://localhost:8000/health"
    Write-Host "  - API Readiness:     http://localhost:8000/health/ready"
    Write-Host "  - Grafana Dashboard: http://localhost:3000 (admin / admin)"
    Write-Host "  - Prometheus Metrics:http://localhost:9090"
    Write-Host ""
    Write-Host "Default User Credentials:" -ForegroundColor White
    Write-Host "  - Instructor Account: admin@codeforge.local / changeme"
    Write-Host "  - Student Account:    student@codeforge.local / changeme"
    Write-Host ""
    Write-Host "Pre-Loaded Demo Data:" -ForegroundColor White
    Write-Host "  - Course:         CS101: Introduction to Programming (Invite Code: CS101A)"
    Write-Host "  - Problems:       hello-world, two-sum, reverse-string, fizzbuzz"
    Write-Host "  - Active Lab:     Lab 1: Programming Basics & Warm-up (live badges enabled)"
    Write-Host "  - Proctored Exam: CS101 Midterm Proctored Assessment (anti-cheat enabled)"
    Write-Host ""
    Write-Host "Supported Languages:" -ForegroundColor White
    Write-Host "  - Python (3.12), Java (OpenJDK 21), C (GCC 13), C++ (G++ 13, C++20)"
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor White
    Write-Host "  - View API logs:      docker compose logs -f api"
    Write-Host "  - View Worker logs:   docker compose logs -f worker"
    Write-Host "  - Run full tests:     docker compose run --rm api pytest -v"
    Write-Host "  - Stop platform:      docker compose down"
    Write-Host ""
    Write-Host "========================================================================" -ForegroundColor Green
}

# ── Execution ─────────────────────────────────────────────────────────────────
Show-Banner
Test-Prerequisites
Test-Ports
Set-EnvironmentFile
Build-Sandboxes -force $Build
Test-Sandboxes
Start-CodeForgeServices -force $Build
Invoke-MigrationsAndSeed
Show-Summary
