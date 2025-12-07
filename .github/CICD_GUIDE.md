# CI/CD Branch Protection Configuration

This document describes the CI/CD workflows implemented for the repository.

## Automated Workflows

### 1. CI/CD Pipeline (`.github/workflows/ci.yml`)
- **Triggers**: On push and pull request to any branch
- **Steps**:
  1. Checkout code
  2. Set up Python 3.11
  3. Install dependencies (`pip install -r requirements.txt`)
  4. Run `./run install` - Install project dependencies
  5. Run `./run test` - Execute test suite
  6. Upload test results and logs

### 2. Branch Protection Check (`.github/workflows/require-review.yml`)
- **Triggers**: On pull request to `main` branch
- **Purpose**: Enforces at least 1 approving review before merge
- **Behavior**: Fails if no approval present

## Testing the CI/CD

### Automatic Testing
```bash
# Any push triggers the workflow
git push origin Sai
```

### Manual Testing
```bash
# Install dependencies
./run install

# Run tests locally
./run test
```

## Setting Up Full Branch Protection

For complete protection on the `main` branch:

1. Go to: Settings → Branches
2. Add rule for `main`
3. Enable:
   - ☑️ Require pull request with 1 approval
   - ☑️ Require status checks (select `test` from CI/CD)
   - ☑️ Require conversation resolution

## Viewing Workflow Results

Check workflow runs at:
https://github.com/hbtasdem/ECE30861_Team4_P2/actions
