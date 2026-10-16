#!/usr/bin/env bash
# ==============================================================================
# CodeForge — Automated Deployment & Setup Script
#
# Idempotent single-command setup for server deployment:
# 1. Verifies Docker & Docker Compose prerequisites
# 2. Checks port availability
# 3. Generates .env with cryptographically random JWT secret
# 4. Builds sandbox execution container images (Java + Python)
# 5. Starts all services with docker compose
# 6. Runs database migrations (Alembic)
# 7. Seeds initial instructor, student, course, problems, and active lab session
# 8. Displays network access URLs and credentials
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# ── Color codes for console output ────────────────────────────────────────────
BOLD="\033[1m"
GREEN="\033[0;32m"
BLUE="\033[0;34m"
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
    echo -e "${BOLD}"
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

# ── 1. Check Prerequisites ───────────────────────────────────────────────────
check_prerequisites() {
    info "Checking system prerequisites..."

    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        error "Docker is not installed. Please install Docker first: https://docs.docker.com/engine/install/"
        exit 1
    fi

    # Check Docker daemon connectivity
    if ! docker info >/dev/null 2>&1; then
        error "Docker daemon is not running or the current user lacks permission to connect to /var/run/docker.sock."
        error "Try running: sudo systemctl start docker && sudo usermod -aG docker \$USER"
        exit 1
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

    success "Docker (${COMPOSE_CMD}) is available and operational."
}

# ── 2. Check Port Availability ────────────────────────────────────────────────
check_ports() {
    info "Checking port availability..."
    local ports=(80 8000 3000 9090)
    local port_busy=0

    for port in "${ports[@]}"; do
        # Check if port is in use by non-codeforge service
        if command -v ss >/dev/null 2>&1; then
            if ss -tlpn "sport = :${port}" 2>/dev/null | grep -q "LISTEN"; then
                warn "Port ${port} is currently bound. (If CodeForge was already running, this will be safely updated)."
            fi
        elif command -v netstat >/dev/null 2>&1; then
            if netstat -tlpn 2>/dev/null | grep -q ":${port} "; then
                warn "Port ${port} is currently bound. (If CodeForge was already running, this will be safely updated)."
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

        # Replace default placeholder with generated secret
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

    success "Sandbox execution images verified."
}

# ── 5. Launch CodeForge Services ──────────────────────────────────────────────
start_services() {
    local force_build="${1:-false}"
    info "Launching CodeForge services with ${COMPOSE_CMD}..."

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

# ── 6. Run Migrations & Seeding ────────────────────────────────────────────────
run_migrations_and_seed() {
    info "Applying database migrations (Alembic)..."
    if ! ${COMPOSE_CMD} exec -T api alembic upgrade head; then
        warn "Direct exec failed, retrying via run..."
        ${COMPOSE_CMD} run --rm api alembic upgrade head
    fi
    success "Database schema is at HEAD."

    info "Seeding initial platform data (instructors, course, problems, lab session)..."
    if ! ${COMPOSE_CMD} exec -T api python -m app.seed; then
        warn "Direct exec failed, retrying via run..."
        ${COMPOSE_CMD} run --rm api python -m app.seed
    fi
    success "Database seeding complete."
}

# ── 7. Display Summary ────────────────────────────────────────────────────────
print_summary() {
    # Detect host IP for network access
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
    echo -e "  - ${BOLD}Grafana Dashboard:${NC} http://${host_ip}:3000 (admin / admin)"
    echo -e "  - ${BOLD}Prometheus Metrics:${NC}http://${host_ip}:9090"
    echo ""
    echo -e "${BOLD}Default User Credentials:${NC}"
    echo -e "  - ${BOLD}Instructor Account:${NC} admin@codeforge.local / changeme"
    echo -e "  - ${BOLD}Student Account:${NC}    student@codeforge.local / changeme"
    echo ""
    echo -e "${BOLD}Pre-Loaded Demo Data:${NC}"
    echo -e "  - ${BOLD}Course:${NC}     CS101: Introduction to Programming"
    echo -e "  - ${BOLD}Invite Code:${NC}CS101A (Share with students to join)"
    echo -e "  - ${BOLD}Problems:${NC}   hello-world, two-sum, reverse-string, fizzbuzz"
    echo -e "  - ${BOLD}Active Lab:${NC} Lab 1: Programming Basics & Warm-up"
    echo -e "                (1 mandatory problem; extras automatically award badges!)"
    echo ""
    echo -e "${BOLD}Useful Commands:${NC}"
    echo -e "  - View API logs:      ${COMPOSE_CMD} logs -f api"
    echo -e "  - View Worker logs:   ${COMPOSE_CMD} logs -f worker"
    echo -e "  - Run test suite:     ${COMPOSE_CMD} run -v ./backend:/app --rm api pytest -v"
    echo -e "  - Stop platform:      ${COMPOSE_CMD} down"
    echo ""
    echo -e "${GREEN}${BOLD}========================================================================${NC}"
}

# ── Main Flow ─────────────────────────────────────────────────────────────────
main() {
    local rebuild="false"
    if [[ "${1:-}" == "--build" || "${1:-}" == "-b" ]]; then
        rebuild="true"
    fi

    banner
    check_prerequisites
    check_ports
    configure_env
    build_sandboxes "${rebuild}"
    start_services "${rebuild}"
    run_migrations_and_seed
    print_summary
}

main "$@"
