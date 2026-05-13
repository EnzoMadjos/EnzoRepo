# Salesforce Knowledge Base — Master Reference
> Compiled: 2026-05-13 | API v67.0 Summer '26
> Sources: Salesforce Help, Avinava/sf-documentation-knowledge, bgaldino/rlm-base-dev, starch-uk/agent-docs, trailheadapps, forceweaver-web
>
> This file is the single authoritative Salesforce reference for this workspace.
> Auto-loaded by GitHub Copilot via `.github/copilot-instructions.md`.
> Individual topic files: `brain/salesforce/articles/`

---

## Quick Reference Index
- [1. Apex Development](#apex-development)
- [2. Lightning Web Components (LWC)](#lwc)
- [3. Salesforce Flow](#flow)
- [4. Revenue Cloud Advanced + CML](#revenue-cloud-cml)
- [5. DevOps (SFDX + CI/CD)](#devops)
- [6. Integration Patterns](#integration)
- [7. Salesforce Security Checklist](#security)
- [8. Governor Limits Quick Reference](#limits)

---

## <a name="apex-development"></a>1. Apex Development

### Golden Trigger Rules
- One trigger per object, no logic in trigger body — delegate to handler class
- Always bulkify: collect IDs → one SOQL → process collection → one DML
- Never query or DML in a loop

```apex
// Trigger pattern
trigger AccountTrigger on Account (before insert, before update, after insert, after update) {
    AccountTriggerHandler handler = new AccountTriggerHandler();
    switch on Trigger.operationType {
        when BEFORE_INSERT  { handler.beforeInsert(Trigger.new); }
        when BEFORE_UPDATE  { handler.beforeUpdate(Trigger.new, Trigger.oldMap); }
        when AFTER_INSERT   { handler.afterInsert(Trigger.new); }
        when AFTER_UPDATE   { handler.afterUpdate(Trigger.new, Trigger.oldMap); }
    }
}
```

### Order of Execution (on save)
1. System validation → 2. Before triggers → 3. Validation rules → 4. Record saved to DB → 5. After triggers → 6. Workflow/Assignment/Auto-response rules → 7. Workflow field updates (re-fires triggers once) → 8. Flow/Process → 9. Roll-up summaries → 10. Commit → 11. Post-commit (emails, async)

### Context Variables
| Variable | Available In |
|---|---|
| `Trigger.new` | insert, update, undelete |
| `Trigger.old` | update, delete |
| `Trigger.newMap` | before update, after insert/update/undelete |
| `Trigger.oldMap` | update, delete |

### Enterprise Architecture (fflib Layers)
| Layer | Class | Responsibility |
|---|---|---|
| Service | `AccountsService` | Business logic, orchestrates others |
| Domain | `Accounts extends fflib_SObjectDomain` | Record-level logic, trigger delegation |
| Selector | `AccountsSelector extends fflib_SObjectSelector` | All SOQL queries |
| Unit of Work | `fflib_SObjectUnitOfWork` | Batches all DML, single commit |

### Security: FLS + CRUD + Sharing
```apex
// with sharing = enforce user record visibility
// without sharing = system-level (admin bypass)
// inherited sharing = use caller's context (default)

// Modern FLS check (API v48+)
SObjectAccessDecision decision = Security.stripInaccessible(
    AccessType.READABLE,
    [SELECT Id, Name, Rating FROM Account]
);
List<Account> safe = (List<Account>) decision.getRecords();

// SOQL injection prevention — use bind variables
String nameFilter = userInput;  // NEVER concatenate raw input
List<Account> accounts = [SELECT Id FROM Account WHERE Name = :nameFilter];
```

### Async Apex Decision Matrix
| Type | Use For | Limit |
|---|---|---|
| `@future(callout=true)` | Callouts from triggers | 50/tx |
| `Queueable` + `Database.AllowsCallouts` | Chaining, complex state | 50/tx |
| `Database.Batchable` | Large volume (>10K records) | 5 concurrent |
| `Schedulable` | Cron-based recurring | 100 scheduled |

### Testing Standards
- Minimum 75% org coverage; 90%+ recommended
- `@TestSetup` for shared test data — runs once per class
- Never `seeAllData = true`
- Use test data factories, never hardcode IDs
- Assert state changes, not just "no exception"
- Use fflib-apex-mocks to stub selectors (no actual SOQL in unit tests)

### Governor Limits (Sync Transaction)
| Resource | Limit |
|---|---|
| SOQL queries | 100 |
| SOQL rows returned | 50,000 |
| DML statements | 150 |
| DML rows | 10,000 |
| CPU time | 10,000 ms |
| Heap size | 6 MB |
| Callouts | 100 |
| Future calls | 50 |

*Async limits: SOQL 200, CPU 60,000 ms, Heap 12 MB*

### Key Repos
- [apex-enterprise-patterns/fflib-apex-common](https://github.com/apex-enterprise-patterns/fflib-apex-common)
- [apex-enterprise-patterns/fflib-apex-mocks](https://github.com/apex-enterprise-patterns/fflib-apex-mocks)
- [trailheadapps/apex-recipes](https://github.com/trailheadapps/apex-recipes)

---

## <a name="lwc"></a>2. Lightning Web Components (LWC)

### Component File Structure
```
myComponent/
  myComponent.html           # Template (required)
  myComponent.js             # Controller (required)
  myComponent.css            # Styles (optional)
  myComponent.js-meta.xml    # Metadata (required for deploy)
```

### Reactive Decorators
| Decorator | When to Use |
|---|---|
| (none) | Primitives — auto-reactive |
| `@track` | Objects/arrays — deep change detection |
| `@api` | Public property exposed to parent |
| `@wire` | Wire Apex method or data service |

### Lifecycle Hooks
| Hook | Use For |
|---|---|
| `constructor()` | Init vars — DON'T touch DOM |
| `connectedCallback()` | Subscribe to events, setup |
| `disconnectedCallback()` | Unsubscribe, cleanup |
| `renderedCallback()` | 3rd-party lib init (guard with isRendered flag) |
| `errorCallback(error, stack)` | Error boundaries for children |

### Communication Patterns
```js
// Parent → Child: @api property
// Child → Parent: CustomEvent + dispatchEvent
// Cross-component: Lightning Message Service (LMS)

// Child fires event
const event = new CustomEvent('save', { detail: { data: this.formData } });
this.dispatchEvent(event);

// Parent listens in template
<c-child onsave={handleChildSave}></c-child>
```

### Wire Service
```js
// @wire auto-calls when reactive params change ($ prefix)
@wire(getAccount, { accountId: '$recordId' })
wiredAccount({ error, data }) {
    if (data) this.account = data;
    else if (error) console.error(error);
}
```

### Lightning Data Service (no Apex needed)
```html
<!-- Read-only form -->
<lightning-record-view-form record-id={recordId} object-api-name="Account">
    <lightning-output-field field-name="Name"></lightning-output-field>
</lightning-record-view-form>

<!-- Edit form -->
<lightning-record-edit-form record-id={recordId} object-api-name="Account" onsuccess={handleSuccess}>
    <lightning-input-field field-name="Name"></lightning-input-field>
    <lightning-button type="submit" label="Save"></lightning-button>
</lightning-record-edit-form>
```

### Performance Rules
- Use `@wire` over imperative Apex for reads (platform caching)
- Mark Apex `cacheable=true` when possible
- Never call Apex in `renderedCallback` without a render-guard flag
- Split large components for better rendering performance

### Key Repo
- [trailheadapps/lwc-recipes](https://github.com/trailheadapps/lwc-recipes) — 70+ component examples

---

## <a name="flow"></a>3. Salesforce Flow

### Flow Types
| Type | Trigger | Use For |
|---|---|---|
| Record-Triggered | DML event | Automation on record changes |
| Screen Flow | User-launched | Guided wizards, data entry |
| Scheduled | Time-based cron | Nightly jobs, reminders |
| Platform Event | Event received | Async event processing |
| Autolaunched | Called from Apex/REST | Reusable business logic |

### Before Save vs After Save
| | Before Save | After Save |
|---|---|---|
| Record ID available | ❌ | ✅ |
| Update triggering record | ✅ (no DML) | ❌ (extra DML) |
| Create/update related records | ❌ | ✅ |

### Bulkification Rules
- ✅ Collect records in loops → DML/Get Records OUTSIDE loop
- ❌ Never DML or Get Records inside a Loop element — hits limits with bulk data

### Flow vs Apex Decision Guide
| Use Flow | Use Apex |
|---|---|
| Simple field updates, related record updates | Complex SOQL / aggregates |
| Guided user input | HTTP callouts |
| Admin-maintainable automation | Bulk processing >50K records |
| Event-driven with Platform Events | Re-entrant / recursion logic |
| Time-based reminders | Packaged/ISV products |

### Invocable Apex from Flow
```apex
@InvocableMethod(label='Get Account Tier')
public static List<Result> getTier(List<Request> requests) {
    List<Result> results = new List<Result>();
    for (Request req : requests) {
        Result res = new Result();
        res.tier = req.annualRevenue > 1000000 ? 'Enterprise' : 'SMB';
        results.add(res);
    }
    return results;
}
// Input/output MUST be List<T> — never a single item
```

### Flow Limits
- Max elements processed per transaction: 2,000
- Loop iterations: 2,000
- Sub-flow nesting depth: 10
- Shared with Apex tx: SOQL 100, DML 150, DML rows 10,000

---

## <a name="revenue-cloud-cml"></a>4. Revenue Cloud Advanced (RCA/RLM) + CML

### Architecture Overview
**Salesforce Revenue Cloud Advanced = Revenue Lifecycle Management (RLM)**
9 domains: PCM → Configurator → Pricing → Rates → Transactions (CLM) → DRO → Usage → Billing → Approvals
263 objects total | API v67.0 | NOT available in Government Cloud or EU Operating Zone

### Data Model Key Objects
| Domain | Key Objects |
|---|---|
| PCM | Product2, ProductCatalog, ProductCategory, ProductAttribute, ProductClassification, ProductComponentGroup |
| Pricing | Pricebook2, PricebookEntry, PriceAdjustmentSchedule, PriceAdjustmentTier, ProductSellingModel (PSM), ProductSellingModelOption (PSMO) |
| Rates | ProductRateCard, RateAdjustmentByTier (RABT), UsageType |
| Configurator | ProductConfigurationConstraint (stores CML source), ConfigurationModel |
| Transactions | Quote, QuoteLineItem, Order, OrderItem, Contract, ContractLineItem, Asset |
| DRO | FulfillmentOrder, FulfillmentOrderLineItem, OrchestrationPlan, OrchestrationStep |
| Usage | ProductUsageResource (PUR), ProductUsageResourcePolicy (PURP), ProductUsageGrant (PUG) |
| Billing | BillingScheduleGroup (BSG), BillingSchedule, Invoice, InvoiceLineItem, Payment |

### CML — Constraint Modeling Language
CML is a DSL that compiles to a constraint model → Constraint Engine → compliant configurations at runtime.  
**Permission required**: `Product Configuration Constraints Designer`

#### 5 Building Blocks
| Block | Keyword | Maps To |
|---|---|---|
| Global declarations | `define`, `property`, `extern` | Fixed values, configurable properties |
| Types | `type Name [: Parent]` | Products, bundles, components, classes |
| Variables | `type field = [domain]` | ProductAttributes, product fields |
| Relationships | `relation name : Type[min..max]` | Bundle structure (parent–component) |
| Constraints | `constraint(expr)` / `require` / `exclude` / `validate` / `recommend` | Config rules |

#### CML Syntax Cheatsheet
```cml
// Global declarations
define MAX_SEATS 100
define COLORS ["Red", "Blue"]
property maxDiscount = 0.25;
extern int minOrder = 5;

// Types
type Laptop : Product {
    int RAM = [8, 16, 32, 64];
    string processor = ["i5", "i7", "i9"];
    boolean warrantyIncluded = false;
}

// Relationships (bundle structure)
relation laptops : Laptop[1..5];         // 1-5 required
relation warranty : WarrantyPlan[0..1];  // optional
relation accessories : Item[0..*];       // unlimited

// Constraints
constraint(RAM >= 16, "Min 16GB RAM required");
constraint(processor == "i9" -> RAM >= 32, "i9 requires 32GB RAM");

// Rules
require(laptop.quantity > 0, warranty.years > 0);    // auto-add warranty if laptop selected
exclude(productA.quantity > 0, productB.quantity > 0); // prevent A+B combo
validate(quantity >= 1 && quantity <= 100, "Quantity must be 1-100");
recommend(RAM >= 32, "32GB recommended for best performance");

// Aggregation
constraint(sum(laptops.price) <= 50000);
constraint(count(accessories) <= 3);
constraint(min(laptops.RAM) >= 16);
constraint(parent().tier == "Gold");     // access parent in bundle
```

#### Visual Builder ↔ CML Editor
Bidirectional sync. Advanced constraints only available in CML Editor.

#### Debugging CML
1. Setup → Debug Logs → New → **Apex Code: FINE**, Workflow: FINER
2. Key log markers: `CONSTRAINT_ENGINE_DECISION`, `CONSTRAINT_RULE_FIRED`, `CML_PARSE_ERROR`

#### CML Anti-Pattern: Product Classification Trap
**Problem**: Shared `ProductClassification` + `exclude` rules → Configurator UI locks out unrelated products.  
**Fix**: Use per-product type definitions in CML instead of shared classifications with broad exclude rules.

### Revenue Cloud Business APIs (v66.0)
| Domain | Endpoint | Purpose |
|---|---|---|
| PCM | `/services/data/v66.0/commerce/product-catalog/...` | Product CRUD |
| Configurator | `/services/data/v66.0/commerce/configurator/sessions` | Config sessions |
| Pricing | `/services/data/v66.0/commerce/pricing/calculate` | Price calculation |
| Transactions | `/services/data/v66.0/commerce/transaction/...` | Quotes + orders |
| Billing | `/services/data/v66.0/commerce/billing/...` | Invoices |

### Key Repos
- [bgaldino/rlm-base-dev](https://github.com/bgaldino/rlm-base-dev) — 263-object data model + skills
- [Avinava/sf-documentation-knowledge](https://github.com/Avinava/sf-documentation-knowledge) — 661 RC docs
- [starch-uk/agent-docs](https://github.com/starch-uk/agent-docs) — CML v1.0.0 full reference

---

## <a name="devops"></a>5. DevOps (SFDX + CI/CD)

### Core Workflow
```bash
# Auth to org
sf org login web --alias my-sandbox --instance-url https://test.salesforce.com

# Create scratch org
sf org create scratch --definition-file config/project-scratch-def.json --alias dev --duration-days 7

# Push/pull
sf project deploy start --target-org dev     # local → org
sf project retrieve start --target-org dev   # org → local

# Validate (check-only, no save)
sf project deploy validate --source-dir force-app --target-org prod

# Deploy with tests
sf project deploy start \
  --source-dir force-app \
  --target-org prod \
  --test-level RunSpecifiedTests \
  --tests AccountServiceTest,ContactServiceTest

# Run tests
sf apex run test --target-org my-sandbox --test-level RunLocalTests
```

### Test Levels
| Level | Use |
|---|---|
| `NoTestRun` | Sandbox/scratch only |
| `RunLocalTests` | All local tests — standard for staging |
| `RunAllTestsInOrg` | Production deploys |
| `RunSpecifiedTests` | Targeted test runs |

### JWT Auth for CI/CD
```bash
sf org login jwt \
  --client-id $SF_CLIENT_ID \
  --jwt-key-file server.key \
  --username $SF_USERNAME \
  --alias ci-org \
  --instance-url https://test.salesforce.com
```

### GitHub Actions — Validate + Deploy Pattern
```yaml
- name: Validate deployment
  run: sf project deploy validate --source-dir force-app --target-org target-org --test-level RunLocalTests

- name: Deploy (main branch only)
  if: github.ref == 'refs/heads/main'
  run: sf project deploy start --source-dir force-app --target-org prod --test-level RunLocalTests
```

### sfdx-hardis (Enhanced CI/CD)
```bash
npm install -g sfdx-hardis
sf hardis:project:deploy:smart     # auto test selection + enhanced error reporting
sf hardis:project:deploy:delta     # delta deploy — only changed metadata
```

### Common Deploy Errors
| Error | Fix |
|---|---|
| `Test coverage below 75%` | Fix tests or use RunLocalTests |
| `Missing field reference` | Remove field reference in code before deleting field |
| `Component not found` | Deploy dependency first |
| `Entity of type X Cannot be Found` | Check API name case sensitivity |

---

## <a name="integration"></a>6. Integration Patterns

### Pattern Selection Matrix
| Pattern | Use When |
|---|---|
| REST API | External app reading/writing SF data |
| Bulk API 2.0 | 100K+ record data loads |
| Platform Events | Event-driven, decoupled async |
| CDC (Change Data Capture) | Subscribe to record changes in real-time |
| Apex Callouts | Salesforce calling external systems |
| External Services | Low-code callouts from Flow (OpenAPI) |
| Named Credentials | All callout endpoint + auth config |

### REST API Essentials
```bash
# OAuth client credentials
POST /services/oauth2/token
grant_type=client_credentials&client_id=KEY&client_secret=SECRET

# CRUD
GET    /services/data/v67.0/sobjects/Account/{id}
POST   /services/data/v67.0/sobjects/Account/
PATCH  /services/data/v67.0/sobjects/Account/{id}
DELETE /services/data/v67.0/sobjects/Account/{id}
PATCH  /services/data/v67.0/sobjects/Account/ExternalId__c/{extId}  # upsert
```

### Apex Callouts — Rules
```apex
// Use Named Credentials — never hardcode URLs/tokens
req.setEndpoint('callout:MyNamedCredential/v1/endpoint');

// Callouts from triggers MUST be async
@future(callout=true)
public static void callExternalSystem(Set<Id> ids) { ... }

// Mock in tests
Test.setMock(HttpCalloutMock.class, new MockHttpResponse());
```

### Platform Events
```apex
// Publish
EventBus.publish(new MyEvent__e(OrderId__c = id, Status__c = 'DONE'));

// Subscribe (trigger)
trigger MyEventTrigger on MyEvent__e (after insert) {
    for (MyEvent__e e : Trigger.new) { /* process */ }
}
```

Platform Events are NOT rolled back on Apex exceptions (unlike DML). Retained 72 hours.

### CDC (Change Data Capture)
```
Enable: Setup → Change Data Capture → select objects
Subscribe: CometD channel /data/AccountChangeEvent
Payload: ChangeEventHeader (entityName, changeType CREATE/UPDATE/DELETE/UNDELETE, changedFields)
```

### Integration Security Checklist
- [ ] OAuth 2.0 only — no Basic Auth in code
- [ ] Named Credentials for all endpoints
- [ ] IP restrictions on Connected Apps
- [ ] HTTPS only for callouts
- [ ] Validate inbound webhooks (HMAC signature)
- [ ] Minimum OAuth scopes

---

## <a name="security"></a>7. Security Quick Reference

### Apex Security Rules
| Check | Code |
|---|---|
| FLS (modern) | `Security.stripInaccessible(AccessType.READABLE, records)` |
| CRUD (read) | `Schema.sObjectType.Account.isAccessible()` |
| CRUD (create) | `Schema.sObjectType.Account.isCreateable()` |
| CRUD (update) | `Schema.sObjectType.Account.isUpdateable()` |
| Sharing (user records) | Declare `with sharing` on class |
| SOQL injection | Use bind variables `:userInput` — never string concat |

### Permission Architecture (Recommended)
```
Profile: Minimum (login, object access)
  + Permission Set: Feature-specific access
  + Permission Set Group: Bundle multiple PSets
```

### OWASP Top 10 — Salesforce Relevance
| OWASP | Salesforce Risk | Mitigation |
|---|---|---|
| Injection | SOQL Injection | Bind variables, `String.escapeSingleQuotes()` |
| Broken Access Control | Missing FLS/CRUD | `Security.stripInaccessible()`, `with sharing` |
| Cryptographic Failures | Storing secrets in plaintext | Named Credentials, Protected Custom Settings |
| Security Misconfiguration | Overly permissive profiles | Principle of least privilege |
| XSS | LWC rendering user input | LWC auto-escapes; avoid `innerHTML` in JS |

---

## <a name="limits"></a>8. Governor Limits Quick Reference

### Sync Transaction
| Resource | Limit |
|---|---|
| SOQL queries | 100 |
| SOQL rows | 50,000 |
| DML statements | 150 |
| DML rows | 10,000 |
| CPU time | 10,000 ms |
| Heap | 6 MB |
| Callouts | 100 |
| `@future` calls | 50 |
| Email invocations | 10 |

### Async Transaction (Batch, Future, Queueable)
| Resource | Limit |
|---|---|
| SOQL queries | 200 |
| CPU time | 60,000 ms |
| Heap | 12 MB |

### Limit API at Runtime
```apex
Limits.getQueries()        // used so far
Limits.getLimitQueries()   // max (100 sync, 200 async)
Limits.getDmlStatements()
Limits.getCpuTime()        // ms used
```

---

*Full topic files: `brain/salesforce/articles/` (apex.md, lwc.md, flow.md, revenue-cloud-cml.md, devops.md, integration.md)*
