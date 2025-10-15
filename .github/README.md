# GitHub Actions CI/CD for Payment API

This directory contains GitHub Actions workflows for the STAB Payment API service.

## Workflows

### 📋 CI Pipeline (`workflows/ci.yml`)

Complete continuous integration pipeline with 5 stages:

**Stage 1: Code Quality**
- Linting and formatting with `ruff`
- Fast syntax and style checks

**Stage 2: Security Scanning**
- Dependency vulnerability scan with `pip-audit`
- SAST (Static Application Security Testing) with `bandit`

**Stage 3: AI Code Review** (PR only)
- Automated code review using CodeRabbit
- Provides suggestions for improvements
- Non-blocking (warning only)

**Stage 4: Testing**
- Unit tests with `pytest`
- Integration tests with PostgreSQL service
- Coverage threshold: 80%
- Uploads coverage to Codecov

**Stage 5: Build & Artifacts**
- Docker image build validation
- Multi-stage build with `uv`
- Cache optimization with GitHub Actions cache
- Uploads Docker image as artifact (7 days retention)

## Trigger Conditions

### Push Events
```yaml
branches: [main, develop, feature/*]
paths:
  - stab-payment-api/**
  - .github/workflows/ci.yml
```

### Pull Request Events
```yaml
branches: [main, develop]
paths:
  - stab-payment-api/**
  - .github/workflows/ci.yml
```

## Environment Variables

### Required in GitHub Secrets
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
- `CODECOV_TOKEN` - (Optional) For coverage upload to Codecov

### Optional Secrets (for AI Review)
- `CODERABBIT_TOKEN` - For CodeRabbit AI review integration

## Job Dependencies

```
quality (Stage 1)
    ↓
security (Stage 2)
    ↓
ai-review (Stage 3) ← Only on Pull Requests
    ↓
test (Stage 4)
    ↓
build (Stage 5)
    ↓
ci-success (Gate)
```

## Caching Strategy

### Python Dependencies
```yaml
Key: ${{ runner.os }}-uv-py311-${{ hashFiles('uv.lock') }}
Paths:
  - ~/.cache/uv
  - .venv
```

### Docker Build
```yaml
Type: GitHub Actions cache (gha)
Mode: max (aggressive caching)
```

## Artifacts

### Bandit Security Report
- **Name**: `bandit-security-report`
- **Path**: `bandit-report.json`
- **Retention**: 30 days
- **Format**: JSON

### Docker Image
- **Name**: `payment-api-docker-image`
- **Path**: `payment-api-image.tar.gz`
- **Retention**: 7 days
- **Format**: Compressed tar

### Coverage Report
- **Uploaded to**: Codecov
- **Format**: XML (coverage.xml)
- **Flag**: `payment-api`

## Success Criteria

CI passes when ALL of the following succeed:
- ✅ Code quality checks pass
- ✅ No security vulnerabilities found
- ✅ All tests pass with ≥80% coverage
- ✅ Docker image builds successfully

AI Review is **non-blocking** and only runs on PRs.

## Local Testing

### Run Quality Checks
```bash
cd stab-payment-api
uv sync
uv run ruff check .
uv run ruff format --check .
```

### Run Security Scans
```bash
# Dependency scan
uv pip compile pyproject.toml -o requirements.txt
pip-audit -r requirements.txt

# SAST scan
uv run bandit -r app/ -ll
```

### Run Tests
```bash
# Unit tests only
uv run pytest tests/ -m "not integration"

# All tests with coverage
uv run pytest tests/ --cov=app --cov-fail-under=80
```

### Build Docker Image
```bash
docker build -t stab-payment-api:local .
```

## Troubleshooting

### ❌ Ruff Formatting Fails
```bash
# Auto-fix formatting issues
uv run ruff format .
```

### ❌ Tests Fail Locally
```bash
# Ensure PostgreSQL is running
docker run -d -p 5432:5432 \
  -e POSTGRES_USER=stab_test \
  -e POSTGRES_PASSWORD=test_password \
  -e POSTGRES_DB=stabdb_test \
  postgres:15-alpine

# Run tests with verbose output
uv run pytest tests/ -vv
```

### ❌ Cache Issues
- Delete `.github/workflows/ci.yml` cache in GitHub Actions settings
- Update cache key version in workflow file

### ❌ Bandit False Positives
Edit `pyproject.toml`:
```toml
[tool.bandit]
exclude_dirs = ["tests/", "alembic/"]
skips = ["B101", "B601"]  # Add test IDs to skip
```

## Performance Metrics

| Stage | Expected Time | Cache Hit |
|-------|--------------|-----------|
| Quality | 30s - 1m | 90%+ |
| Security | 1m - 2m | N/A |
| AI Review | 2m - 5m | N/A |
| Testing | 2m - 4m | 85%+ |
| Build | 2m - 5m | 80%+ |
| **Total** | **8m - 17m** | - |

## Best Practices

1. **Always run locally first** before pushing
2. **Keep uv.lock updated** for consistent dependencies
3. **Write tests** for new features (maintain 80% coverage)
4. **Fix security issues immediately** - CI will block merges
5. **Review AI suggestions** - they often catch subtle bugs

## Reference Documentation

- [GitHub Actions CI Strategy](/docs/github-actions-ci-strategy.md)
- [Payment API CLAUDE.md](../CLAUDE.md)
- [Testing Guide](../tests/README.md)

## Support

For issues with CI:
1. Check workflow logs in GitHub Actions tab
2. Review this README for troubleshooting steps
3. Contact DevOps team if persistent issues

---

**Last Updated**: 2025-10-15
**Maintainer**: STAB DevOps Team
