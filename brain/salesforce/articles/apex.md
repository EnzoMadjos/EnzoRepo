# Apex Development — Salesforce Knowledge Base
> Source: Salesforce Help (API v67.0, Summer '26), apex-guide, trailheadapps/apex-recipes
> Last updated: 2026-05-13

---

## 1. Trigger Architecture

### Golden Rules
- **One trigger per object** — never multiple triggers on same object
- **No logic in trigger** — delegate everything to a handler class
- **Always bulkify** — every trigger must handle `List<SObject>` and `Map<Id, SObject>`
- **Never query or DML in a loop**

### Recommended Pattern (Trigger Handler)
```apex
// AccountTrigger.trigger
trigger AccountTrigger on Account (before insert, before update, after insert, after update) {
    AccountTriggerHandler handler = new AccountTriggerHandler();
    switch on Trigger.operationType {
        when BEFORE_INSERT  { handler.beforeInsert(Trigger.new); }
        when BEFORE_UPDATE  { handler.beforeUpdate(Trigger.new, Trigger.oldMap); }
        when AFTER_INSERT   { handler.afterInsert(Trigger.new); }
        when AFTER_UPDATE   { handler.afterUpdate(Trigger.new, Trigger.oldMap); }
    }
}

// AccountTriggerHandler.cls
public with sharing class AccountTriggerHandler {
    public void beforeInsert(List<Account> newAccounts) { /* logic */ }
    public void beforeUpdate(List<Account> newAccounts, Map<Id, Account> oldMap) { /* logic */ }
    public void afterInsert(List<Account> newAccounts) { /* logic */ }
    public void afterUpdate(List<Account> newAccounts, Map<Id, Account> oldMap) { /* logic */ }
}
```

### Context Variables
| Variable | Type | Available In |
|---|---|---|
| `Trigger.new` | List\<SObject\> | insert, update, undelete |
| `Trigger.old` | List\<SObject\> | update, delete |
| `Trigger.newMap` | Map\<Id,SObject\> | before update, after insert/update/undelete |
| `Trigger.oldMap` | Map\<Id,SObject\> | update, delete |
| `Trigger.isBefore` | Boolean | all |
| `Trigger.isAfter` | Boolean | all |
| `Trigger.isInsert/Update/Delete/Undelete` | Boolean | all |
| `Trigger.size` | Integer | count of records |

### Order of Execution (on Save)
1. System validation (required fields, field formats, max length)
2. **Before triggers**
3. System & custom validation rules
4. Record saved to DB (before commit)
5. **After triggers**
6. Assignment rules, auto-response rules, workflow rules
7. Workflow field updates → re-fires before/after update triggers (once only)
8. Processes (Flow), Escalation rules
9. Roll-up summary field recalculation
10. Criteria-based sharing rules
11. Commit to DB
12. Post-commit: sending emails, async jobs enqueued

### Trigger Best Practices
```apex
// ✅ Bulk-safe — collect IDs, query once, process all
public void afterInsert(List<Account> accounts) {
    Set<Id> accountIds = new Map<Id, Account>(accounts).keySet();
    List<Contact> contacts = [SELECT Id, AccountId FROM Contact WHERE AccountId IN :accountIds];
    // process contacts...
}

// ❌ Anti-pattern — SOQL in loop
public void afterInsert(List<Account> accounts) {
    for (Account a : accounts) {
        List<Contact> c = [SELECT Id FROM Contact WHERE AccountId = :a.Id]; // HITS LIMIT
    }
}
```

---

## 2. Governor Limits (API v67.0)

### Per-Transaction Sync Limits
| Resource | Limit |
|---|---|
| SOQL queries | 100 |
| SOQL rows returned | 50,000 |
| DML statements | 150 |
| DML rows | 10,000 |
| CPU time | 10,000 ms |
| Heap size | 6 MB |
| Callouts (HTTP/SOAP) | 100 |
| Future method calls | 50 |
| Queueable jobs added | 50 |
| Email invocations | 10 |

### Per-Transaction Async Limits (Batch, Future, Queueable)
| Resource | Limit |
|---|---|
| SOQL queries | 200 |
| SOQL rows returned | 50,000 |
| DML statements | 150 |
| CPU time | 60,000 ms |
| Heap size | 12 MB |

### Limit Checking at Runtime
```apex
Integer soqlUsed = Limits.getQueries();       // queries so far this tx
Integer soqlLimit = Limits.getLimitQueries();  // 100 (sync) or 200 (async)
Integer dmlUsed = Limits.getDmlStatements();
Integer cpuUsed = Limits.getCpuTime();         // ms
```

### Avoiding Limits
```apex
// ✅ SOQL outside loop
List<Account> accounts = [SELECT Id, Name FROM Account WHERE Industry = 'Tech'];

// ✅ Map lookup instead of repeated SOQL
Map<Id, Account> accMap = new Map<Id, Account>([SELECT Id, Name FROM Account]);

// ✅ Database.executeBatch for large data volume (200 records/chunk default)
Database.executeBatch(new MyBatchClass(), 200);

// ✅ @future for callouts from triggers
@future(callout=true)
public static void makeCallout(Set<Id> ids) { /* ... */ }
```

---

## 3. Security & Sharing

### Sharing Keywords
| Keyword | Behavior |
|---|---|
| `with sharing` | Enforces sharing rules — use for user-context classes |
| `without sharing` | Ignores sharing rules — use for system/admin operations |
| `inherited sharing` | Inherits caller's sharing context (default for classes without keyword) |

### FLS (Field-Level Security) Enforcement
```apex
// Manual FLS check
SObjectType accountType = Schema.getGlobalDescribe().get('Account');
Map<String, Schema.SObjectField> fields = accountType.getDescribe().fields.getMap();
if (fields.get('Name').getDescribe().isAccessible()) {
    // safe to read
}
if (fields.get('Name').getDescribe().isUpdateable()) {
    // safe to update
}

// Modern: Security.stripInaccessible (API v48+)
SObjectAccessDecision decision = Security.stripInaccessible(
    AccessType.READABLE,
    [SELECT Id, Name, Rating FROM Account]
);
List<Account> safeAccounts = (List<Account>) decision.getRecords();
```

### CRUD Enforcement
```apex
if (!Schema.sObjectType.Account.isAccessible()) throw new NoAccessException('No read access');
if (!Schema.sObjectType.Account.isCreateable()) throw new NoAccessException('No create access');
if (!Schema.sObjectType.Account.isUpdateable()) throw new NoAccessException('No update access');
if (!Schema.sObjectType.Account.isDeletable()) throw new NoAccessException('No delete access');
```

### SOQL Injection Prevention
```apex
// ❌ Vulnerable
String query = 'SELECT Id FROM Account WHERE Name = \'' + userInput + '\'';
List<Account> accounts = Database.query(query);

// ✅ Bind variable (safe)
String nameFilter = userInput;
List<Account> accounts = [SELECT Id FROM Account WHERE Name = :nameFilter];

// ✅ String.escapeSingleQuotes if dynamic SOQL is needed
String safe = String.escapeSingleQuotes(userInput);
String query = 'SELECT Id FROM Account WHERE Name = \'' + safe + '\'';
```

---

## 4. Enterprise Architecture (fflib)

### Layers
| Layer | Class Type | Responsibility |
|---|---|---|
| **Service** | `AccountsService` | Business logic, orchestrates domain + selector |
| **Domain** | `Accounts extends fflib_SObjectDomain` | Record-level logic, trigger handling |
| **Selector** | `AccountsSelector extends fflib_SObjectSelector` | All SOQL, returns typed Lists |
| **Unit of Work** | `fflib_SObjectUnitOfWork` | Batches all DML, single commit |

### Service Layer Example
```apex
public class AccountsService {
    public static void updateAccountRatings(Set<Id> accountIds) {
        fflib_ISObjectUnitOfWork uow = Application.UnitOfWork.newInstance();
        List<Account> accounts = AccountsSelector.newInstance().selectById(accountIds);
        Accounts domain = Accounts.newInstance(accounts);
        domain.updateRatings(uow);
        uow.commitWork();
    }
}
```

### Selector Layer Example
```apex
public class AccountsSelector extends fflib_SObjectSelector {
    public List<Schema.SObjectField> getSObjectFieldList() {
        return new List<Schema.SObjectField>{ Account.Id, Account.Name, Account.Rating };
    }
    public Schema.SObjectType getSObjectType() { return Account.SObjectType; }
    public List<Account> selectById(Set<Id> ids) {
        return (List<Account>) selectSObjectsById(ids);
    }
    public List<Account> selectByIndustry(String industry) {
        return (List<Account>) Database.query(
            newQueryFactory().setCondition('Industry = :industry').toSOQL()
        );
    }
}
```

---

## 5. Async Apex

### Types Comparison
| Type | When to Use | Limit |
|---|---|---|
| `@future` | Fire-and-forget, callouts from triggers | 50/tx |
| `Queueable` | Chaining, complex state, callouts | 50 enqueued/tx |
| `Batchable` | Large data volume (>10K records) | 5 concurrent |
| `Schedulable` | Cron-based recurring jobs | 100 scheduled |

### Queueable Example
```apex
public class AccountSyncJob implements Queueable, Database.AllowsCallouts {
    private Set<Id> accountIds;
    public AccountSyncJob(Set<Id> ids) { this.accountIds = ids; }

    public void execute(QueueableContext ctx) {
        List<Account> accounts = [SELECT Id, Name FROM Account WHERE Id IN :accountIds];
        // do work, make callouts...
        if (/* more to process */) {
            System.enqueueJob(new AccountSyncJob(nextBatch));
        }
    }
}
// Enqueue
System.enqueueJob(new AccountSyncJob(accountIds));
```

### Batch Apex Example
```apex
public class AccountBatchJob implements Database.Batchable<SObject> {
    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator('SELECT Id, Name FROM Account WHERE IsActive__c = true');
    }
    public void execute(Database.BatchableContext bc, List<Account> scope) {
        // process scope (default: 200 records per chunk)
        update scope;
    }
    public void finish(Database.BatchableContext bc) {
        // notify, chain next batch
    }
}
Database.executeBatch(new AccountBatchJob(), 200);
```

---

## 6. Apex Testing Standards

### Rules
- **Minimum 75% org coverage** to deploy, **90%+ recommended**
- Use `@TestSetup` for shared test data (runs once per class)
- Never use `seeAllData = true` (except for legacy KB articles edge cases)
- Use test data factories — never hardcode IDs
- Assert the state change, not just "no exception"

### Test Class Pattern
```apex
@IsTest
private class AccountsServiceTest {
    @TestSetup
    static void setup() {
        Account a = TestDataFactory.createAccount('Test Corp', 'Technology');
        insert a;
    }

    @IsTest
    static void updateAccountRatings_setsRating() {
        Account a = [SELECT Id FROM Account LIMIT 1];
        Test.startTest();
        AccountsService.updateAccountRatings(new Set<Id>{ a.Id });
        Test.stopTest();

        Account updated = [SELECT Rating FROM Account WHERE Id = :a.Id];
        System.assertEquals('Hot', updated.Rating, 'Rating should be Hot after update');
    }
}
```

### Mocking (fflib-apex-mocks)
```apex
// Mock the selector — no actual SOQL
fflib_ApexMocks mocks = new fflib_ApexMocks();
IAccountsSelector selectorMock = (IAccountsSelector) mocks.mock(IAccountsSelector.class);
mocks.startStubbing();
mocks.when(selectorMock.selectById(new Set<Id>{ testId }))
     .thenReturn(new List<Account>{ testAccount });
mocks.stopStubbing();
Application.Selector.setMock(selectorMock);
```

---

## 7. SOQL Best Practices
```apex
// ✅ Selective queries — use indexed fields in WHERE
[SELECT Id FROM Account WHERE Id IN :ids]
[SELECT Id FROM Account WHERE ExternalId__c = :extId]  // custom indexed field

// ✅ Limit fields — only what you need
[SELECT Id, Name, Rating FROM Account WHERE Industry = 'Tech']

// ❌ Never SELECT * or SELECT Id, * patterns
// ❌ Never SOQL inside loops

// ✅ For large result sets use QueryLocator in Batch
Database.getQueryLocator('SELECT Id FROM Account')

// ✅ Relationship queries (2-level max)
[SELECT Id, Name, (SELECT Id, LastName FROM Contacts) FROM Account WHERE Id IN :ids]

// ✅ Aggregate queries
List<AggregateResult> results = [SELECT AccountId, COUNT(Id) cnt FROM Contact GROUP BY AccountId];

// ✅ Dynamic SOQL with bind variables
String whereClause = 'Industry = :industry';
List<Account> accounts = Database.query('SELECT Id FROM Account WHERE ' + whereClause);
// Note: bind variables referenced by name are resolved at runtime
```

---

## 8. NebulaLogger (Structured Logging)
```apex
// Log at different levels
Logger.debug('Processing account', record);
Logger.info('Account processed successfully', record);
Logger.warn('Account missing required field', record);
Logger.error('Account processing failed', record, ex);

// Save log entries (triggers DML — do at end of transaction)
Logger.saveLog();

// In tests
Logger.getUserSettings().LoggingLevel__c = 'FINEST';
```

---

## Key Repos
| Repo | Purpose |
|---|---|
| [apex-enterprise-patterns/fflib-apex-common](https://github.com/apex-enterprise-patterns/fflib-apex-common) | Service/Domain/Selector/UoW layers |
| [apex-enterprise-patterns/fflib-apex-mocks](https://github.com/apex-enterprise-patterns/fflib-apex-mocks) | Mocking framework for Apex |
| [trailheadapps/apex-recipes](https://github.com/trailheadapps/apex-recipes) | Official pattern examples |
| [mitchspano/trigger-actions-framework](https://github.com/mitchspano/trigger-actions-framework) | Advanced trigger framework |
| [amoss/NebulaLogger](https://github.com/amoss/NebulaLogger) | Structured logging |
