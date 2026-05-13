# Salesforce DevOps — Knowledge Base
> Source: Salesforce DX, sfdx-hardis, CI/CD best practices, Summer '26
> Last updated: 2026-05-13

---

## 1. Salesforce DX (SFDX) Core Workflow

### Project Structure
```
force-app/
  main/
    default/
      classes/           # Apex classes (.cls + .cls-meta.xml)
      triggers/          # Apex triggers
      lwc/               # Lightning Web Components
      flows/             # Flows
      objects/           # Custom objects + fields
        Account/
          fields/
            CustomField__c.field-meta.xml
      permissionsets/
      profiles/
      layouts/
      staticresources/
      aura/              # Legacy Aura components
.forceignore             # Like .gitignore for SF metadata
sfdx-project.json        # Project config, API version, package directories
```

### `sfdx-project.json`
```json
{
  "packageDirectories": [
    { "path": "force-app", "default": true }
  ],
  "namespace": "",
  "sfdcLoginUrl": "https://login.salesforce.com",
  "sourceApiVersion": "67.0"
}
```

---

## 2. Org Authentication

```bash
# Authenticate to org (opens browser)
sf org login web --alias my-sandbox --instance-url https://test.salesforce.com

# Login to production
sf org login web --alias prod --instance-url https://login.salesforce.com

# List authenticated orgs
sf org list

# Set default org
sf config set target-org my-sandbox

# Login with JWT (for CI/CD — no browser)
sf org login jwt \
  --client-id $SF_CLIENT_ID \
  --jwt-key-file server.key \
  --username $SF_USERNAME \
  --alias ci-org \
  --instance-url https://test.salesforce.com
```

---

## 3. Scratch Orgs

Scratch orgs are disposable, configurable environments — use for development and testing.

```bash
# Create scratch org (uses config/project-scratch-def.json)
sf org create scratch \
  --definition-file config/project-scratch-def.json \
  --alias my-scratch \
  --duration-days 7

# Push local source to scratch org
sf project deploy start --target-org my-scratch

# Pull changes from scratch org back to local
sf project retrieve start --target-org my-scratch

# Open scratch org in browser
sf org open --target-org my-scratch

# Delete scratch org
sf org delete scratch --target-org my-scratch --no-prompt
```

### Scratch Org Definition (`config/project-scratch-def.json`)
```json
{
  "edition": "Developer",
  "features": ["EnableSetPasswordInApi", "Communities", "ServiceCloud"],
  "settings": {
    "lightningExperienceSettings": { "enableS1DesktopEnabled": true },
    "mobileSettings": { "enableS1EncryptedStoragePref2": false }
  },
  "orgName": "MyProject Dev Org"
}
```

---

## 4. Deploy / Retrieve Commands

```bash
# Deploy entire force-app to org
sf project deploy start --target-org my-sandbox

# Deploy specific directory
sf project deploy start --source-dir force-app/main/default/classes --target-org my-sandbox

# Deploy specific metadata
sf project deploy start \
  --metadata ApexClass:AccountService,ApexClass:AccountServiceTest \
  --target-org my-sandbox

# Check-only deploy (validate without saving)
sf project deploy validate --source-dir force-app --target-org prod

# Retrieve specific metadata
sf project retrieve start --metadata ApexClass:AccountService --target-org my-sandbox

# Retrieve all from org
sf project retrieve start --target-org my-sandbox

# Deploy with test level
sf project deploy start \
  --source-dir force-app \
  --target-org prod \
  --test-level RunSpecifiedTests \
  --tests AccountServiceTest,ContactServiceTest
```

### Test Levels
| Level | When to Use |
|---|---|
| `NoTestRun` | Sandbox/scratch (no coverage check) |
| `RunLocalTests` | Run all local (non-namespaced) tests |
| `RunAllTestsInOrg` | Run every test — for production |
| `RunSpecifiedTests` | Run only named test classes |

---

## 5. CI/CD with GitHub Actions

### Basic Pipeline
```yaml
# .github/workflows/ci.yml
name: Salesforce CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Salesforce CLI
        run: npm install -g @salesforce/cli

      - name: Write JWT key
        run: echo "${{ secrets.SF_JWT_KEY }}" > server.key

      - name: Authenticate to org
        run: |
          sf org login jwt \
            --client-id ${{ secrets.SF_CLIENT_ID }} \
            --jwt-key-file server.key \
            --username ${{ secrets.SF_USERNAME }} \
            --alias target-org \
            --instance-url https://test.salesforce.com

      - name: Validate deployment (check-only)
        run: |
          sf project deploy validate \
            --source-dir force-app \
            --target-org target-org \
            --test-level RunLocalTests

  deploy-to-staging:
    needs: validate
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      # ... (same auth steps)
      - name: Deploy to staging
        run: |
          sf project deploy start \
            --source-dir force-app \
            --target-org staging-org \
            --test-level RunLocalTests
```

### Required GitHub Secrets
| Secret | Value |
|---|---|
| `SF_CLIENT_ID` | Connected App Consumer Key |
| `SF_JWT_KEY` | Private key for Connected App JWT auth |
| `SF_USERNAME` | Salesforce username for CI user |

### Connected App Setup (for JWT)
1. Setup → App Manager → New Connected App
2. Enable OAuth, check "Use Digital Signatures"
3. Upload certificate (from `openssl` generated key pair)
4. Grant full access + api + refresh_token scopes
5. Pre-authorize in permission set or profile

---

## 6. sfdx-hardis (Enhanced DevOps)

sfdx-hardis adds hardened deploy workflows, delta deploys, automatic test selection, and Slack notifications.

```bash
# Install
npm install -g sfdx-hardis

# Hardened deploy (auto-selects tests, handles scratch orgs)
sf hardis:project:deploy:smart --target-org my-sandbox

# Delta deploy (only changed metadata since last deploy)
sf hardis:project:deploy:delta --target-org my-sandbox

# Generate org diff report
sf hardis:org:diagnose:unusedmetadata --target-org my-sandbox

# Auto-approve PR when all checks pass
sf hardis:work:save --target-org my-sandbox
```

---

## 7. Source Control Strategies

### Branching Model
```
main (production)
  └── staging
        └── feature/TICKET-123-account-trigger
        └── feature/TICKET-456-lwc-contact-form
        └── hotfix/PROD-789-pricing-error
```

### .forceignore (what not to track)
```
# Standard generated files
**/*.dup
**/profiles          # Profiles are messy — use Permission Sets instead
**/*.sanitizedHtml
**/package.xml

# Managed package objects (don't track external packages)
**/*__mdt            # Custom metadata — manage separately if not versioned
```

### Package.xml Pattern
```xml
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>*</members>
        <name>LightningComponentBundle</name>
    </types>
    <types>
        <members>*</members>
        <name>CustomObject</name>
    </types>
    <version>67.0</version>
</Package>
```

---

## 8. Running Tests

```bash
# Run all tests in org
sf apex run test --target-org my-sandbox --test-level RunLocalTests --result-format human

# Run specific test class
sf apex run test \
  --class-names AccountServiceTest \
  --target-org my-sandbox \
  --result-format tap \
  --output-dir test-results

# Run tests synchronously (wait for results)
sf apex run test --target-org my-sandbox --synchronous

# Check code coverage
sf apex run test \
  --target-org my-sandbox \
  --code-coverage \
  --result-format json \
  --output-dir test-results
```

---

## 9. Common Deployment Errors

| Error | Cause | Fix |
|---|---|---|
| `Test coverage below 75%` | Org doesn't have enough test coverage | Fix tests in org OR add --test-level RunLocalTests |
| `Missing field reference` | Field deleted but still referenced in Apex | Remove/update code first, then remove field |
| `Component not found: MyComponent` | LWC dependency missing | Deploy dependency first |
| `UNKNOWN_EXCEPTION: null` | Generic Salesforce error | Check debug logs, usually a DML error |
| `Dependent class failed` | Test class references a class with error | Fix the referenced class first |
| `Entity of type X named Y Cannot be Found` | Metadata reference mismatch | Check API names, case-sensitivity |

---

## 10. Key Tools & Repos
| Tool | URL |
|---|---|
| Salesforce CLI | [developer.salesforce.com/tools/salesforcecli](https://developer.salesforce.com/tools/salesforcecli) |
| sfdx-hardis | [github.com/hardisgroupcom/sfdx-hardis](https://github.com/hardisgroupcom/sfdx-hardis) |
| SF GitHub Actions | [github.com/forcedotcom/salesforcedx-actions](https://github.com/forcedotcom/salesforcedx-actions) |
| SFDMU (Data migration) | [github.com/forcedotcom/SFDX-Data-Move-Utility](https://github.com/forcedotcom/SFDX-Data-Move-Utility) |
| Prettier Apex | [github.com/dangmai/prettier-plugin-apex](https://github.com/dangmai/prettier-plugin-apex) |
