#!/usr/bin/env bash
# ==============================================================================
# CodeForge — Automated Cross-Platform Deployment & Setup Script
#
# Turnkey single-command setup for server and desktop environments:
# 1. Auto-detects Operating System (Linux, macOS, WSL2)
# 2. Verifies Docker & Docker Desktop daemon connectivity
# 3. Checks port availability (80, 8000, 3000, 9090)
# 4. Generates .env with cryptographically random JWT secret
# 5. Builds all 4 sandbox execution container images (Java, Python, C, C++)
# 6. Runs container health checks on all sandbox images
# 7. Starts all services with docker compose (with restart & health monitoring)
# 8. Runs database migrations (Alembic)
# 9. Seeds initial instructor, student, course, problems, lab, and proctored exam
# 10. Displays network access URLs and credentials
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# ── Color codes for console output ────────────────────────────────────────────
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m" # No Color

info() {
    echo -e "${BLUE}${BOLD}[INFO]${NC} $*"
}

success() {
    echo -e "${GREEN}${BOLD}[SUCCESS]${NC} $*"
}

warn() {
    echo -e "${YELLOW}${BOLD}[WARN]${NC} $*"
}

error() {
    echo -e "${RED}${BOLD}[ERROR]${NC} $*" >&2
}

banner() {
    echo -e "${CYAN}${BOLD}"
    cat << "EOF"
   ______           __     ______                    
  / ____/____  ____/ /___ / ____/____  _________ ____
 / /    / __ \/ __  // _ \ / /_  / __ \/ ___/ __ `/ _ \
/ /___ / /_/ / /_/ //  __// __/ / /_/ / /  / /_/ //  __/
\____/ \____/\__,_/ \___//_/    \____/_/   \__, / \___/ 
                                          /____/         
   Browser-Based Competitive Programming Judge & Lab Platform
EOF
    echo -e "${NC}"
}

# ── 1. OS Auto-Detection & Prerequisites ──────────────────────────────────────
detect_os() {
    OS_NAME="Linux"
    IS_WSL="false"
    IS_MACOS="false"

    local uname_out
    uname_out="$(uname -s 2>/dev/null || echo 'Unknown')"
    case "${uname_out}" in
        Linux*)
            if grep -qi -E "(microsoft|wsl)" /proc/version 2>/dev/null; then
                OS_NAME="Windows (WSL2)"
                IS_WSL="true"
            else
                OS_NAME="Linux ($(uname -r))"
            fi
            ;;
        Darwin*)
            OS_NAME="macOS ($(sw_vers -productVersion 2>/dev/null || echo 'Darwin'))"
            IS_MACOS="true"
            ;;
        *)
            OS_NAME="${uname_out}"
            ;;
    esac
    info "Detected Operating System: ${BOLD}${OS_NAME}${NC}"
}

check_prerequisites() {
    info "Checking system prerequisites..."

    # Check Docker CLI
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker is not installed. Please install Docker first: https://docs.docker.com/get-docker/"
        if [ "${IS_MACOS}" = "true" ] || [ "${IS_WSL}" = "true" ]; then
            error "Download Docker Desktop: https://www.docker.com/products/docker-desktop/"
        fi
        exit 1
    fi

    # Check Docker daemon connectivity
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running or the current user lacks permission to connect to /var/run/docker.sock."
        if [ "${IS_WSL}" = "true" ] || [ "${IS_MACOS}" = "true" ]; then
            error "Ensure Docker Desktop is started and 'Use the Docker daemon with WSL2 / macOS' is enabled in Settings."
        else
            error "Try running: sudo systemctl start docker && sudo usermod -aG docker \$USER"
        fi
        exit 1
    fi

    if [ "${IS_WSL}" = "true" ] || [ "${IS_MACOS}" = "true" ]; then
        if docker info 2>/dev/null | grep -qi "Desktop"; then
            info "Docker Desktop integration detected and operational."
        fi
    fi

    # Check Docker Compose (v2 plugin or standalone v1)
    if docker compose version >/dev/null 2>&1; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    else
        error "Docker Compose is required but neither 'docker compose' nor 'docker-compose' was found."
        exit 1
    fi

    success "Docker engine (${COMPOSE_CMD}) is available and operational."
}

# ── 2. Check Port Availability ────────────────────────────────────────────────
check_ports() {
    info "Checking port availability..."
    local ports=(80 8000 3000 9090)

    for port in "${ports[@]}"; do
        if command -v ss >/dev/null 2>&1; then
            if ss -tlpn "sport = :${port}" 2>/dev/null | grep -q "LISTEN"; then
                warn "Port ${port} is currently bound. (If CodeForge was already running, containers will be safely updated)."
            fi
        elif command -v netstat >/dev/null 2>&1; then
            if netstat -tlpn 2>/dev/null | grep -q ":${port} "; then
                warn "Port ${port} is currently bound. (If CodeForge was already running, containers will be safely updated)."
            fi
        fi
    done
}

# ── 3. Configure Environment (.env) ───────────────────────────────────────────
configure_env() {
    info "Configuring environment settings (.env)..."

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            info "Created .env from .env.example"
        else
            error ".env.example not found!"
            exit 1
        fi
    fi

    # Check if JWT_SECRET_KEY needs a random value generated
    if grep -q "change-me" .env || grep -q "change-me-to-a-random-secret" .env; then
        local random_secret=""
        if command -v openssl >/dev/null 2>&1; then
            random_secret=$(openssl rand -hex 32)
        elif command -v python3 >/dev/null 2>&1; then
            random_secret=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        else
            random_secret=$(head -c 32 /dev/urandom | xxd -p | head -n 1)
        fi

        sed -i.bak "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=${random_secret}/" .env && rm -f .env.bak
        success "Generated cryptographically secure JWT_SECRET_KEY."
    else
        info "Existing JWT_SECRET_KEY found in .env."
    fi
}

# ── 4. Build Sandbox Images ───────────────────────────────────────────────────
build_sandboxes() {
    local force_build="${1:-false}"

    if [ "${force_build}" = "true" ] || ! docker image inspect codeforge-sandbox-java >/dev/null 2>&1; then
        info "Building Java sandbox container image (codeforge-sandbox-java)..."
        docker build -t codeforge-sandbox-java ./sandbox/java
    else
        info "Sandbox image 'codeforge-sandbox-java' already present."
    fi

    if [ "${force_build}" = "true" ] || ! docker image inspect codeforge-sandbox-python >/dev/null 2>&1; then
        info "Building Python sandbox container image (codeforge-sandbox-python)..."
        docker build -t codeforge-sandbox-python ./sandbox/python
    else
        info "Sandbox image 'codeforge-sandbox-python' already present."
    fi

    if [ "${force_build}" = "true" ] || ! docker image inspect codeforge-sandbox-c >/dev/null 2>&1; then
        info "Building C sandbox container image (codeforge-sandbox-c)..."
        docker build -t codeforge-sandbox-c ./sandbox/c
    else
        info "Sandbox image 'codeforge-sandbox-c' already present."
    fi

    if [ "${force_build}" = "true" ] || ! docker image inspect codeforge-sandbox-cpp >/dev/null 2>&1; then
        info "Building C++ sandbox container image (codeforge-sandbox-cpp)..."
        docker build -t codeforge-sandbox-cpp ./sandbox/cpp
    else
        info "Sandbox image 'codeforge-sandbox-cpp' already present."
    fi

    success "Sandbox execution images built."
}

# ── 5. Verify Sandbox Images Health ───────────────────────────────────────────
verify_sandboxes() {
    info "Verifying health of sandbox execution environments..."
    local failed=0

    if docker run --rm --network none codeforge-sandbox-java java -version >/dev/null 2>&1; then
        info "  ✔ Java sandbox operational"
    else
        warn "  ✘ Java sandbox verification issue"
        failed=$((failed + 1))
    fi

    if docker run --rm --network none codeforge-sandbox-python python3 --version >/dev/null 2>&1; then
        info "  ✔ Python sandbox operational"
    else
        warn "  ✘ Python sandbox verification issue"
        failed=$((failed + 1))
    fi

    if docker run --rm --network none codeforge-sandbox-c gcc --version >/dev/null 2>&1; then
        info "  ✔ C sandbox operational"
    else
        warn "  ✘ C sandbox verification issue"
        failed=$((failed + 1))
    fi

    if docker run --rm --network none codeforge-sandbox-cpp g++ --version >/dev/null 2>&1; then
        info "  ✔ C++ sandbox operational"
    else
        warn "  ✘ C++ sandbox verification issue"
        failed=$((failed + 1))
    fi

    if [ "${failed}" -eq 0 ]; then
        success "All 4 sandbox containers verified and functional."
    else
        warn "${failed} sandbox container(s) reported warnings during verification."
    fi
}

# ── 6. Launch CodeForge Services ──────────────────────────────────────────────
start_services() {
    local force_build="${1:-false}"
    info "Launching CodeForge service stack with ${COMPOSE_CMD}..."

    if [ "${force_build}" = "true" ]; then
        ${COMPOSE_CMD} up -d --build
    else
        ${COMPOSE_CMD} up -d
    fi

    info "Waiting for PostgreSQL database to be healthy..."
    local attempts=0
    local max_attempts=30

    until ${COMPOSE_CMD} exec -T db pg_isready -U codeforge -d codeforge >/dev/null 2>&1; do
        attempts=$((attempts + 1))
        if [ "${attempts}" -ge "${max_attempts}" ]; then
            error "Database took too long to become healthy."
            exit 1
        fi
        sleep 1
    done

    success "All service containers are up and database is healthy."
}

# ── 7. Run Migrations & Seeding ────────────────────────────────────────────────
run_migrations_and_seed() {
    info "Applying database migrations (Alembic)..."
    if ! ${COMPOSE_CMD} exec -T api alembic upgrade head; then
        warn "Direct exec failed, retrying via run..."
        ${COMPOSE_CMD} run --rm api alembic upgrade head
    fi
    success "Database schema is at HEAD."

    info "Seeding initial platform data (instructors, course, problems, lab, exam)..."
    if ! ${COMPOSE_CMD} exec -T api python -m app.seed; then
        warn "Direct exec failed, retrying via run..."
        ${COMPOSE_CMD} run --rm api python -m app.seed
    fi
    success "Database seeding complete."
}

# ── 8. Display Summary ────────────────────────────────────────────────────────
print_summary() {
    local host_ip="127.0.0.1"
    if command -v hostname >/dev/null 2>&1; then
        local ip_cand
        ip_cand=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ -n "${ip_cand}" ]; then
            host_ip="${ip_cand}"
        fi
    fi

    echo ""
    echo -e "${GREEN}${BOLD}========================================================================${NC}"
    echo -e "${GREEN}${BOLD}             CodeForge Platform Setup Completed Successfully!           ${NC}"
    echo -e "${GREEN}${BOLD}========================================================================${NC}"
    echo ""
    echo -e "${BOLD}Platform Access URLs:${NC}"
    echo -e "  - ${BOLD}Web Application:${NC}   http://${host_ip} (or http://localhost)"
    echo -e "  - ${BOLD}API Docs (Swagger):${NC}http://${host_ip}:8000/docs"
    echo -e "  - ${BOLD}API Health Check:${NC}  http://${host_ip}:8000/health"
    echo -e "  - ${BOLD}API Readiness:${NC}     http://${host_ip}:8000/health/ready"
    echo -e "  - ${BOLD}Grafana Dashboard:${NC} http://${host_ip}:3000 (admin / admin)"
    echo -e "  - ${BOLD}Prometheus Metrics:${NC}http://${host_ip}:9090"
    echo ""
    echo -e "${BOLD}Default User Credentials:${NC}"
    echo -e "  - ${BOLD}Instructor Account:${NC} admin@codeforge.local / changeme"
    echo -e "  - ${BOLD}Student Account:${NC}    student@codeforge.local / changeme"
    echo ""
    echo -e "${BOLD}Pre-Loaded Demo Data:${NC}"
    echo -e "  - ${BOLD}Course:${NC}         CS101: Introduction to Programming (Invite Code: CS101A)"
    echo -e "  - ${BOLD}Problems:${NC}       hello-world, two-sum, reverse-string, fizzbuzz"
    echo -e "  - ${BOLD}Active Lab:${NC}     Lab 1: Programming Basics & Warm-up (live badges enabled)"
    echo -e "  - ${BOLD}Proctored Exam:${NC} CS101 Midterm Proctored Assessment (anti-cheat enabled)"
    echo ""
    echo -e "${BOLD}Supported Languages:${NC}"
    echo -e "  - Python (3.12), Java (OpenJDK 21), C (GCC 13), C++ (G++ 13, C++20)"
    echo ""
    echo -e "${BOLD}Platform Control Commands:${NC}"
    echo -e "  - Stop platform:      ./codeforge-setup.sh --stop"
    echo -e "  - Factory reset:      ./codeforge-setup.sh --reset"
    echo -e "  - Service status:     ./codeforge-setup.sh --status"
    echo -e "  - Run full tests:     ./codeforge-setup.sh --test"
    echo -e "  - Re-seed demo data:  ./codeforge-setup.sh --seed"
    echo -e "  - Rebuild & launch:   ./codeforge-setup.sh --build"
    echo ""
    echo -e "${BOLD}Docker Direct Commands:${NC}"
    echo -e "  - View API logs:      ${COMPOSE_CMD} logs -f api"
    echo -e "  - View Worker logs:   ${COMPOSE_CMD} logs -f worker"
    echo -e "  - Check containers:   ${COMPOSE_CMD} ps"
    echo ""
    echo -e "${GREEN}${BOLD}========================================================================${NC}"
}

show_help() {
    cat << EOF
CodeForge CLI & Turnkey Platform Manager

Usage:
  ./codeforge-setup.sh [COMMAND | OPTION]

Commands & Options:
  (no args)             Launch or update the CodeForge platform stack
  --build, -b           Rebuild application containers (api, web) and launch
  --stop, stop, down    Gracefully stop all platform containers
  --reset, reset        Completely wipe all containers and data volumes (-v),
                        re-launch, run migrations, and re-seed clean demo data
  --status, status, ps  Show running container statuses and test API readiness probe
  --test, test          Run the complete 145-test automated pytest suite
  --seed, seed          Re-seed the database without restarting containers
  --help, -h            Show this help reference

Examples:
  ./codeforge-setup.sh          # Quick launch
  ./codeforge-setup.sh --stop   # Stop everything
  ./codeforge-setup.sh --reset  # Clean factory reset
  ./codeforge-setup.sh --status # Check health & container status
EOF
}

# ── Main Flow ─────────────────────────────────────────────────────────────────
main() {
    local cmd="${1:-}"

    case "${cmd}" in
        --help|-h|help)
            banner
            show_help
            exit 0
            ;;
        --stop|stop|--down|down)
            banner
            detect_os
            check_prerequisites
            info "Stopping CodeForge service stack..."
            ${COMPOSE_CMD} down
            success "All CodeForge services have been gracefully stopped."
            exit 0
            ;;
        --status|status|ps)
            banner
            detect_os
            check_prerequisites
            info "Checking CodeForge service status..."
            ${COMPOSE_CMD} ps
            echo ""
            info "Testing API readiness probe..."
            if command -v curl >/dev/null 2>&1; then
                curl -s http://localhost:8000/health/ready || echo "API not responding"
                echo ""
            fi
            exit 0
            ;;
        --test|test)
            banner
            detect_os
            check_prerequisites
            info "Running complete CodeForge automated test suite (145 tests)..."
            ${COMPOSE_CMD} run --rm api pytest -v
            exit 0
            ;;
        --seed|seed)
            banner
            detect_os
            check_prerequisites
            info "Re-seeding database with demo data..."
            ${COMPOSE_CMD} exec -T api python manage.py seed
            success "Database re-seeded successfully."
            exit 0
            ;;
        --reset|reset)
            banner
            detect_os
            check_prerequisites
            warn "Initiating full platform reset (wiping database, redis, and container volumes)..."
            ${COMPOSE_CMD} down -v
            success "All data volumes cleared."
            info "Re-launching platform from clean state..."
            check_ports
            configure_env
            build_sandboxes "false"
            verify_sandboxes
            start_services "false"
            run_migrations_and_seed
            print_summary
            exit 0
            ;;
        --build|-b)
            banner
            detect_os
            check_prerequisites
            check_ports
            configure_env
            build_sandboxes "true"
            verify_sandboxes
            start_services "true"
            run_migrations_and_seed
            print_summary
            exit 0
            ;;
        "")
            banner
            detect_os
            check_prerequisites
            check_ports
            configure_env
            build_sandboxes "false"
            verify_sandboxes
            start_services "false"
            run_migrations_and_seed
            print_summary
            ;;
        *)
            error "Unknown option or command: ${cmd}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

main "$@"
