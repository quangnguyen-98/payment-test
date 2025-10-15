# Quick Start - GitHub Actions CI

## 🚀 Getting Started (3 Steps)

### 1. Verify Configuration ✅
```bash
cd stab-payment-api

# Check all configs exist
ls -l pyproject.toml    # ✅ ruff, pytest, bandit configs
ls -l Dockerfile        # ✅ Multi-stage build
ls -l .github/workflows/ci.yml  # ✅ CI pipeline
```

### 2. Test Locally 🧪
```bash
# Install dependencies
uv sync

# Run quality checks (Stage 1)
uv run ruff check .

# Run security scan (Stage 2)
uv run bandit -r app/ -ll

# Run tests (Stage 4)
uv run pytest tests/ --cov=app
```

### 3. Push and Monitor 📊
```bash
git add .github/
git commit -m "Add CI pipeline"
git push origin your-branch

# View in GitHub:
# Actions tab → CI Pipeline - Payment API
```

## 📋 CI Pipeline Overview

```
┌─────────────────┐
│  Push/PR Event  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Stage 1: Quality│  30s-1m   ruff lint + format
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Stage 2: Security│  1-2m    pip-audit + bandit
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Stage 3: AI Review│ 2-5m    CodeRabbit (PR only)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Stage 4: Testing │  2-4m    pytest + coverage
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Stage 5: Build   │  2-5m    Docker + artifacts
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ✅ CI Success  │  All checks passed!
└─────────────────┘
```

## 🔍 Common Commands

### Run Locally Before Push
```bash
# Full quality check
uv run ruff check . && uv run ruff format --check .

# Auto-fix formatting
uv run ruff format .

# Security scan
uv run bandit -r app/ -ll --skip B101,B601

# Unit tests only
uv run pytest tests/ -m "not integration"

# All tests with coverage
uv run pytest tests/ --cov=app --cov-fail-under=80

# Build Docker image
docker build -t payment-api:local .
```

### Check CI Status
```bash
# Via GitHub CLI
gh run list --workflow=ci.yml

# View latest run
gh run view --web
```

## ⚡ Quick Fixes

### ❌ Ruff Failed
```bash
# Auto-fix
uv run ruff check . --fix
uv run ruff format .
```

### ❌ Tests Failed
```bash
# Run with verbose output
uv run pytest tests/ -vv --tb=long

# Run specific test
uv run pytest tests/unit/test_services.py -k test_name
```

### ❌ Coverage Too Low
```bash
# See what's not covered
uv run pytest tests/ --cov=app --cov-report=term-missing

# Generate HTML report
uv run pytest tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

### ❌ Security Issues Found
```bash
# View detailed report
uv run bandit -r app/ -f json -o report.json
cat report.json | python -m json.tool
```

## 📦 Artifacts Available

After CI completes, download from GitHub Actions:

1. **bandit-security-report** (30 days)
   - JSON format security scan results

2. **payment-api-docker-image** (7 days)
   - Compressed Docker image tar.gz

3. **Coverage Report** (on Codecov)
   - View at: codecov.io/gh/[org]/[repo]

## 🎯 Success Criteria

CI will pass when:
- ✅ No lint/format errors
- ✅ No security vulnerabilities
- ✅ All tests pass
- ✅ Coverage ≥ 80%
- ✅ Docker builds successfully

## 💡 Pro Tips

1. **Run locally first** - Saves CI minutes
2. **Use cache** - ~3-5x faster builds
3. **Fix ruff first** - Cheapest to fix
4. **Watch coverage** - Keep it above 80%
5. **Review AI suggestions** - They're usually helpful

## 🆘 Need Help?

1. Check [README.md](.github/README.md) for full docs
2. View workflow logs in GitHub Actions
3. Run locally to debug
4. Contact DevOps team

## 🔗 Quick Links

- [Full Documentation](README.md)
- [CI Strategy Doc](/docs/github-actions-ci-strategy.md)
- [Payment API CLAUDE.md](../CLAUDE.md)
- [GitHub Actions Dashboard](../../actions)

---

**Last Updated**: 2025-10-15
