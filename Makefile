# STAB Payment API - UV Native Makefile
.PHONY: help install install-dev add add-dev remove sync lock dev dev-debug prod test test-cov test-file format lint typecheck security quality fix-imports migrate rollback migration seed seed-clear db-stats clean pre-commit

# Variables
PROJECT := app
TESTS := tests
SCRIPTS := scripts

# Default
help:
	@echo "🚀 STAB Payment API - UV Commands"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📦 Setup & Dependencies:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make install        Install production dependencies only"
	@echo "  make install-dev    Install all + setup pre-commit"
	@echo "  make add pkg=NAME   Add package (e.g: make add pkg=fastapi)"
	@echo "  make add-dev pkg=NAME Add dev package"
	@echo "  make remove pkg=NAME Remove package"
	@echo "  make sync           Sync dependencies from lock"
	@echo "  make lock           Update lock file"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 Development:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make dev            Run dev server (port 8006)"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧪 Testing:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make test           Run all tests"
	@echo "  make test-cov       Run tests with coverage"
	@echo "  make test-file file=PATH Test specific file"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎨 Code Quality:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make format         Format code (ruff format)"
	@echo "  make lint           Run linter (ruff check)"
	@echo "  make lint-fix       Run linter with auto-fix"
	@echo "  make typecheck      Type checking (mypy)"
	@echo "  make security       Security scan (bandit)"
	@echo "  make quality        Run all quality checks"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🗄️ Database:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make migrate        Apply migrations"
	@echo "  make rollback       Rollback last migration"
	@echo "  make migration msg=TEXT Create new migration"
	@echo "  make seed           Seed database"
	@echo "  make seed-clear     Clear and reseed"
	@echo "  make db-stats       Show database statistics"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧹 Utilities:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make clean          Clean cache files"
	@echo "  make pre-commit     Run pre-commit hooks"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ==================== SETUP ====================
# Install production dependencies only
install:
	@echo "📦 Installing production dependencies..."
	@uv sync --no-dev
	@echo "✅ Production dependencies installed!"

# Install all dependencies (production + dev) with pre-commit
install-dev:
	@echo "📦 Installing all dependencies (production + dev)..."
	@uv sync
	@echo "🔧 Setting up pre-commit hooks..."
	@uv run pre-commit install
	@echo "✅ Development environment ready!"

# ==================== PACKAGE MANAGEMENT ====================
add:
	@test -n "$(pkg)" || (echo "❌ Error: pkg is required. Example: make add pkg=fastapi" && exit 1)
	@echo "➕ Adding $(pkg)..."
	@uv add $(pkg)

add-dev:
	@test -n "$(pkg)" || (echo "❌ Error: pkg is required. Example: make add-dev pkg=pytest" && exit 1)
	@echo "➕ Adding dev dependency $(pkg)..."
	@uv add --dev $(pkg)

remove:
	@test -n "$(pkg)" || (echo "❌ Error: pkg is required" && exit 1)
	@echo "➖ Removing $(pkg)..."
	@uv remove $(pkg)

sync:
	@echo "🔄 Syncing dependencies from lock file..."
	@uv sync
	@echo "✅ Dependencies synced!"

lock:
	@echo "🔒 Updating lock file..."
	@uv lock

# ==================== DEVELOPMENT ====================
dev:
	@echo "🚀 Starting development server on http://localhost:8000"
	@uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload


# ==================== TESTING ====================
test:
	@echo "🧪 Running tests..."
	@uv run pytest

test-cov:
	@echo "📊 Running tests with coverage..."
	@uv run pytest --cov=$(PROJECT) --cov-report=term-missing

test-file:
	@test -n "$(file)" || (echo "❌ Error: file is required. Example: make test-file file=tests/api/test_psps.py" && exit 1)
	@echo "🧪 Testing $(file)..."
	@uv run pytest $(file) -v

# ==================== CODE QUALITY ====================
format:
	@echo "✨ Formatting code with ruff..."
	@uv run ruff format $(PROJECT) $(TESTS) $(SCRIPTS)

lint:
	@echo "🔍 Running ruff check..."
	@uv run ruff check $(PROJECT) $(TESTS) $(SCRIPTS)

lint-fix:
	@echo "🔧 Running ruff check with auto-fix..."
	@uv run ruff check --fix $(PROJECT) $(TESTS) $(SCRIPTS)

typecheck:
	@echo "🔍 Type checking with mypy..."
	@uv run mypy $(PROJECT)

security:
	@echo "🔒 Running security scan with bandit..."
	@uv run bandit -r $(PROJECT) -ll --skip B101,B601

quality: format lint typecheck security
	@echo "✅ All quality checks passed!"

# ==================== DATABASE ====================
migrate:
	@echo "📤 Applying migrations..."
	@uv run alembic upgrade head

rollback:
	@echo "📥 Rolling back last migration..."
	@uv run alembic downgrade -1

migration:
	@test -n "$(msg)" || (echo "❌ Error: msg is required. Example: make migration msg='Add user table'" && exit 1)
	@echo "📝 Creating migration: $(msg)"
	@uv run alembic revision --autogenerate -m "$(msg)"

seed:
	@echo "🌱 Seeding database..."
	@uv run python scripts/seed_database.py seed

seed-clear:
	@echo "🔄 Clearing and reseeding database..."
	@uv run python scripts/seed_database.py seed --clear

db-stats:
	@echo "📊 Database statistics:"
	@uv run python scripts/seed_database.py stats

# ==================== UTILITIES ====================
clean:
	@echo "🧹 Cleaning cache files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name ".coverage" -delete
	@find . -type f -name "coverage.xml" -delete
	@echo "✨ Cleaned!"

pre-commit:
	@echo "🔍 Running pre-commit hooks..."
	@uv run pre-commit run --all-files
