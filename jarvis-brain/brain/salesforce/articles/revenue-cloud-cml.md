# Revenue Cloud Advanced (RCA/RLM) + CML — Salesforce Knowledge Base
> Sources: Salesforce Help (API v67.0, Summer '26), Avinava sf-documentation-knowledge, bgaldino/rlm-base-dev, starch-uk/agent-docs CML v1.0.0, forceweaver-web blog
> Last updated: 2026-05-13

---

## 1. Overview

**Salesforce Revenue Cloud Advanced** (also called **Revenue Lifecycle Management — RLM**) is a separate product suite on top of core Salesforce. It provides end-to-end quote-to-cash:

- **PCM** — Product Catalog Management (product definitions, bundles, attributes)
- **Configurator** — Advanced product configuration with CML-based constraint engine
- **Pricing** — Price books, adjustments, tiers, price rules
- **Rates** — Recurring/usage-based rate structures
- **Transactions** — Quotes, orders, contracts (CLM)
- **DRO** — Dynamic Revenue Orchestration (fulfillment workflow)
- **Usage** — Metered usage policies and grants
- **Billing** — Billing schedules, invoices, collections
- **Approvals** — Multi-step approval orchestration

**NOT available in**: Government Cloud, EU Operating Zone.

---

## 2. Data Model — 263 Objects Across 9 Domains

### Domain Summary
| Domain | Abbreviation | Key Objects |
|---|---|---|
| Product Catalog Management | PCM | Product2, ProductCatalog, ProductCategory, ProductAttribute, ProductClassification, ProductComponentGroup |
| Pricing | Pricing | Pricebook2, PricebookEntry (PBE), PriceAdjustmentSchedule (PAS), PriceAdjustmentTier (PAT), PriceBook, ProductSellingModel (PSM), ProductSellingModelOption (PSMO) |
| Rates | Rates | ProductRateCard, RateAdjustmentByTier (RABT), UsageType |
| Configurator | Configurator | ProductConfigurationConstraint, ConfigurationModel, CML source (product-level) |
| Transactions | Transactions / CLM | Quote, QuoteLineItem, Order, OrderItem, Contract, ContractLineItem, Asset |
| DRO | Dynamic Revenue Orchestration | FulfillmentOrder, FulfillmentOrderLineItem, OrchestrationPlan, OrchestrationStep |
| Usage | Usage | ProductUsageResource (PUR), ProductUsageResourcePolicy (PURP), ProductUsageGrant (PUG) |
| Billing | Billing | BillingScheduleGroup (BSG), BillingSchedule, Invoice, InvoiceLineItem, Payment |
| Approvals | Approvals | ApprovalRequest, ApprovalStep |

### Key Object Relationships
```
ProductCatalog
  └── ProductCategory
        └── Product2
              ├── ProductAttribute (defines configurable fields)
              ├── ProductClassification (groups products by category)
              ├── ProductSellingModel (PSM) — one-time / recurring / evergreen
              │     └── ProductSellingModelOption (PSMO)
              ├── PricebookEntry (PBE) → Pricebook2
              ├── PriceAdjustmentSchedule (PAS)
              │     └── PriceAdjustmentTier (PAT)
              └── ProductComponentGroup (for bundle structure)
                    └── Product2 (child components)
```

### SOQL Examples
```apex
// Get all active products with pricing
List<Product2> products = [
    SELECT Id, Name, ProductCode, IsActive,
           (SELECT Id, UnitPrice, Pricebook2.Name FROM PricebookEntries WHERE IsActive = true)
    FROM Product2
    WHERE IsActive = true
    ORDER BY Name
];

// Get price adjustments for a product
List<PriceAdjustmentSchedule> pas = [
    SELECT Id, Name, AdjustmentType, AdjustmentAmount,
           (SELECT FromValue, ToValue, AdjustmentAmount FROM PriceAdjustmentTiers ORDER BY FromValue)
    FROM PriceAdjustmentSchedule
    WHERE Product2Id = :productId
];

// Get bundle structure
List<ProductComponentGroup> components = [
    SELECT Id, Name, MinQuantity, MaxQuantity, Sequence,
           ParentProductId, ChildProductId
    FROM ProductComponentGroup
    WHERE ParentProductId = :bundleProductId
];
```

---

## 3. CML — Constraint Modeling Language

CML is a **DSL built natively into RCA** for writing product configuration rules. It compiles to a Constraint Model → Constraint Engine → validated configuration output at runtime. No custom Apex needed.

**Permission required**: `Product Configuration Constraints Designer`

### 3.1 Core Concepts

| Building Block | In CML | Maps To in RCA |
|---|---|---|
| `define` / `property` | Global constants/properties | Header-level fixed values |
| `type` | Entity definition | Product, Bundle, Component, ProductClass |
| Variable | Typed field on a type | ProductAttribute, product field, context tag |
| `relation` | How types link | Bundle structure (parent–component) |
| `constraint` | Logical restriction | Configuration rule |

### 3.2 Full Syntax Reference

```cml
// ─── GLOBAL DECLARATIONS ───────────────────────────────────────────────────
define MAX_SEATS 100                        // Fixed constant
define COLORS ["Red", "Blue", "Green"]      // List constant
property maxDiscount = 0.25;                // Configurable (can change per org)
extern int minOrder = 5;                    // External variable with default

// ─── TYPES ────────────────────────────────────────────────────────────────
type Product {
    string name;
    int quantity = [1..MAX_SEATS];
    decimal(2) price = [0..99999.99];
}

type Laptop : Product {                     // Inherits from Product
    int RAM = [8, 16, 32, 64];
    string processor = ["i5", "i7", "i9"];
    boolean warrantyIncluded = false;
}

type WarrantyPlan : Product {
    int years = [1..3];
}

// ─── VARIABLES ────────────────────────────────────────────────────────────
int quantity = [1..10];                     // Integer range
string color = COLORS;                      // List reference
decimal(2) price = [0..1000.00];            // Decimal range
boolean addWarranty = false;
string tier = ["Silver", "Gold", "Platinum"];
int[] selectedItems;                        // Array variable

// ─── RELATIONSHIPS ────────────────────────────────────────────────────────
relation laptops : Laptop[1..5];            // 1 to 5 Laptops required
relation warranty : WarrantyPlan[0..1];     // Optional warranty
relation accessories : Accessory[0..*];    // Zero to unlimited
relation orderedItems : Item[1..3] order (TypeA, TypeB, TypeC);  // Ordered

// ─── CONSTRAINTS ──────────────────────────────────────────────────────────
// Basic
constraint(quantity > 0);
constraint(price <= 9999.99);

// Implication with message
constraint(addWarranty -> warranty[0].years >= 1, "Warranty requires at least 1 year");

// Type filter
constraint(laptops[Laptop] > 0);            // At least 1 Laptop type in relation

// ─── RULES ────────────────────────────────────────────────────────────────
// Require: if A selected, auto-add B
require(laptop.quantity > 0, warranty.years > 0);

// Exclude: prevent two products from co-existing
exclude(productA.quantity > 0, productB.quantity > 0);

// Validate: fail with message if condition false
validate(quantity >= 1 && quantity <= 100, "Quantity must be between 1 and 100");

// Recommend: soft constraint (suggestion, not enforcement)
recommend(processor == "i7", "i7 recommended for best performance");

// Message: display info/warning/error
message(RAM < 16, "Performance may be limited with less than 16GB RAM", "Warning");

// ─── AGGREGATION FUNCTIONS ────────────────────────────────────────────────
constraint(sum(laptops.price) <= 50000);    // Sum of all related item prices
constraint(count(accessories) <= 3);        // Count of related items
constraint(min(laptops.RAM) >= 16);         // Min value across relation
constraint(max(laptops.price) <= 5000);     // Max value
constraint(avg(laptops.RAM) >= 24);         // Average
constraint(parent().tier == "Gold");        // Access parent product in bundle

// ─── PREFERENCE / HIDE / ACTION ───────────────────────────────────────────
preference(processor == "i7");              // Soft preference (default suggestion)
hide(quantity > 10, bulkOption);            // Hide element when condition true
action(quantity > 10, applyBulkDiscount()); // Trigger custom action
```

### 3.3 Visual Builder ↔ CML Editor

- **Bidirectional sync**: Visual Builder (point-and-click) compiles to CML; CML Editor saves back to visual view
- Advanced logic (complex `constraint` expressions, custom aggregations) only available in CML Editor
- Visual Builder covers: basic require/exclude, simple variable domains, relationship cardinality

### 3.4 Where CML Lives in the Data Model

```apex
// CML is stored on ProductConfigurationConstraint records
List<ProductConfigurationConstraint> cmlModels = [
    SELECT Id, Name, CMLSource__c, Status, Product2Id
    FROM ProductConfigurationConstraint
    WHERE Product2Id = :productId
];
// CMLSource__c is the raw CML text (multi-line)
```

---

## 4. CML Debugging

### Enable Debug Logging
1. Setup → **Debug Logs** → New
2. Set user (or Automated Process for API calls)
3. **Apex Code**: FINE (required — lower levels miss constraint engine events)
4. **Workflow**: FINER (for rule firing events)
5. Expiry: set 1–7 days for testing

### Reading CML Debug Logs
Key event markers in debug log:
```
CONSTRAINT_ENGINE_DECISION — shows which constraints were evaluated
CONSTRAINT_RULE_FIRED — shows which require/exclude/validate triggered
CONSTRAINT_MODEL_COMPILED — shows compilation success/errors
CML_PARSE_ERROR — syntax errors in CML source
```

### Common CML Errors
| Error | Cause | Fix |
|---|---|---|
| `CML_PARSE_ERROR: Unexpected token` | Syntax error | Check parentheses, commas, string quotes |
| `Undefined type: X` | Type not declared | Declare type before use |
| `Cardinality violation` | min > max in relation | Fix `[min..max]` values |
| `Circular dependency` | A requires B requires A | Break cycle with intermediate variable |
| `Compilation timeout` | Model too complex | Reduce constraint depth, split models |

---

## 5. CML Anti-Patterns

### ⚠ The Product Classification Trap
**Problem**: Using a shared `ProductClassification` + `exclude` rules causes the Configurator UI to lock — preventing unrelated products from being selected.

**How it happens**:
```cml
// Shared classification: "SoftwareProduct"
// ProductA and ProductB both have ProductClassification = "SoftwareProduct"
// CML rule:
exclude(ProductA.quantity > 0, ProductB.quantity > 0);
// BUT: Configurator resolves this at the CLASSIFICATION level, not product level
// Result: selecting ANY SoftwareProduct locks out ALL SoftwareProducts
```

**Fix**: Use **per-product** classifications (or product-level types in CML) instead of shared parent classifications for exclude rules:
```cml
// ✅ Safe — product-specific types
type ProductA_Type : Product {}
type ProductB_Type : Product {}
exclude(productA_items[ProductA_Type] > 0, productB_items[ProductB_Type] > 0);
```

---

## 6. Revenue Cloud Business APIs (v66.0 REST)

**Base URL**: `/services/apexrest/commerce/` or `/services/data/v66.0/commerce/`

### Key API Groups
| Domain | Endpoint Pattern | Purpose |
|---|---|---|
| PCM | `/product-catalog/...` | CRUD product catalog items |
| Product Discovery | `/product-discovery/search` | Search/filter product catalog |
| Configurator | `/configurator/...` | Launch configuration sessions, validate configs |
| Pricing | `/pricing/calculate` | Get calculated prices for a configuration |
| Rate Management | `/rate-management/...` | Manage rate cards, usage rates |
| Transaction Mgmt | `/transaction/...` | Create/manage quotes and orders |
| Usage Management | `/usage/...` | Record and query usage events |
| Billing | `/billing/...` | Generate invoices, manage billing schedules |
| Context Service | `/context/...` | Get/set context for pricing/config rules |

### Configurator API: Start a Configuration Session
```apex
HttpRequest req = new HttpRequest();
req.setEndpoint('/services/data/v66.0/commerce/configurator/sessions');
req.setMethod('POST');
req.setHeader('Authorization', 'Bearer ' + UserInfo.getSessionId());
req.setHeader('Content-Type', 'application/json');
req.setBody(JSON.serialize(new Map<String, Object>{
    'productId' => 'product2Id_here',
    'pricebookId' => 'pricebook2Id_here',
    'contextId' => 'contextId_here'
}));
HttpResponse res = new Http().send(req);
// Returns sessionId for subsequent configuration calls
```

### Pricing API: Calculate Price
```apex
// POST /services/data/v66.0/commerce/pricing/calculate
Map<String, Object> requestBody = new Map<String, Object>{
    'products' => new List<Map<String, Object>>{
        new Map<String, Object>{
            'productId' => productId,
            'quantity' => 1,
            'pricebookId' => pricebookId
        }
    },
    'contextId' => contextId
};
```

---

## 7. RLM Implementation Notes

### Don't-Do List
- ❌ Don't write Apex triggers on PCM objects (Product2, PricebookEntry) for pricing logic — use Price Rules
- ❌ Don't bypass the Configurator API for order creation — it skips constraint validation
- ❌ Don't put CML in workflow/process — it's only runtime via Configurator
- ❌ Don't use shared ProductClassification with broad exclude rules (Classification Trap)
- ❌ Don't write ad-hoc SOQL for pricing — use Pricing API (caching, rules, adjustments won't apply)

### Do-Do List
- ✅ Use ProductSellingModel (PSM) to define billing terms (one-time, evergreen, termed)
- ✅ Use Context Service for dynamic pricing based on customer/account attributes
- ✅ Separate Configurator sessions from order creation — configure first, then submit
- ✅ Use Price Rules for conditional adjustments (instead of Apex)
- ✅ Test CML in a scratch org / sandbox before deploying (hard to roll back)

---

## 8. Key Repos & References
| Source | URL |
|---|---|
| bgaldino/rlm-base-dev | [github.com/bgaldino/rlm-base-dev](https://github.com/bgaldino/rlm-base-dev) — RLM 263-object data model, skills |
| Avinava/sf-documentation-knowledge | [github.com/Avinava/sf-documentation-knowledge](https://github.com/Avinava/sf-documentation-knowledge) — Scraped docs API v67 |
| starch-uk/agent-docs | [github.com/starch-uk/agent-docs](https://github.com/starch-uk/agent-docs) — CML v1.0.0 full reference |
| Salesforce Help — CML | `atlas.en-us.revenue_lifecycle_management_dev_guide.meta/revenue_lifecycle_management_dev_guide/` |
| Salesforce Help — RLM Dev Guide | Search: "Revenue Lifecycle Management Developer Guide" |
