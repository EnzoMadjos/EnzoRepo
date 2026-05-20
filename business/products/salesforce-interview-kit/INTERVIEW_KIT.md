# Salesforce Developer Interview Kit
## Apex · LWC · Agentforce · Revenue Cloud

**By Lorenzo Madjos | Platform App Manager @ Accenture**  
*Salesforce AI Associate · Platform App Builder · CSM*

---

> This guide is written from real interview experience — not recycled documentation.  
> Every question here has been asked in actual Salesforce developer interviews at consulting firms, ISVs, and enterprise orgs.

---

## How to Use This Guide

1. **Quick prep (2 hours):** Read the cheat sheet (Part 6) + skim bolded answers
2. **Standard prep (1 day):** Work through Part 1–3 fully, mark gaps
3. **Deep prep (3 days):** All parts + write your own answers before reading the provided ones
4. **The night before:** Cheat sheet + your personal story answers only

---

# PART 1 — Apex Fundamentals

---

## Governor Limits

### Q1. What are governor limits and why does Salesforce enforce them?

**Answer:**  
Governor limits are Salesforce's enforcement mechanism to ensure no single tenant consumes excessive shared resources on the multitenant platform. Because thousands of orgs run on the same infrastructure, Salesforce enforces per-transaction limits on DML operations, SOQL queries, CPU time, heap size, and more.

**Key limits to memorize:**

| Resource | Synchronous Limit | Asynchronous Limit |
|---|---|---|
| SOQL queries | 100 | 200 |
| DML statements | 150 | 150 |
| DML rows | 10,000 | 10,000 |
| CPU time | 10,000 ms | 60,000 ms |
| Heap size | 6 MB | 12 MB |
| Callouts | 100 | 100 |
| Future calls | 50 | — |
| Queueable jobs | 50 | — |

**Pro tip in interviews:** Mention that you always check `Limits.getDMLStatements()` during debugging and that bulkification is your first instinct when writing triggers.

---

### Q2. What is bulkification and why is it critical?

**Answer:**  
Bulkification means writing Apex code that handles 200 records (one trigger batch) as efficiently as one record. The most common mistake is querying or doing DML inside a loop.

**Bad (not bulkified):**
```apex
trigger ContactTrigger on Contact (before insert) {
    for (Contact c : Trigger.new) {
        Account acc = [SELECT Id FROM Account WHERE Id = :c.AccountId]; // SOQL in loop!
        c.Description = acc.Name;
    }
}
```

**Good (bulkified):**
```apex
trigger ContactTrigger on Contact (before insert) {
    Set<Id> accountIds = new Set<Id>();
    for (Contact c : Trigger.new) accountIds.add(c.AccountId);

    Map<Id, Account> accounts = new Map<Id, Account>(
        [SELECT Id, Name FROM Account WHERE Id IN :accountIds]
    );

    for (Contact c : Trigger.new) {
        c.Description = accounts.get(c.AccountId)?.Name;
    }
}
```

---

### Q3. What is the difference between `insert` and `upsert`?

**Answer:**  
- `insert` — creates new records only. Fails if a matching record exists.
- `upsert` — inserts if no match, updates if match found. Match is determined by record Id or an external Id field you specify.

```apex
upsert accounts Account.Fields.External_Id__c;
```

Use `upsert` for data integrations where you don't know if records already exist.

---

### Q4. What happens when a DML operation partially fails?

**Answer:**  
By default, if any record in a DML operation fails, the entire operation is rolled back. To handle partial success, use `Database.insert(records, false)` — the second parameter `allOrNothing = false` allows partial saves and returns a `Database.SaveResult[]` you can inspect for errors.

```apex
List<Database.SaveResult> results = Database.insert(contacts, false);
for (Database.SaveResult sr : results) {
    if (!sr.isSuccess()) {
        for (Database.Error err : sr.getErrors()) {
            System.debug('Error: ' + err.getMessage());
        }
    }
}
```

---

### Q5. What is a `@future` method? When would you use it?

**Answer:**  
A `@future` method runs asynchronously in a separate transaction. Use it when:
- You need to make a callout from a trigger (triggers cannot make synchronous callouts)
- You want to avoid mixed DML errors (e.g., modifying both setup and non-setup objects)
- You need to exceed synchronous CPU limits

```apex
@future(callout=true)
public static void syncToExternalSystem(Set<Id> recordIds) {
    List<Account> accounts = [SELECT Id, Name FROM Account WHERE Id IN :recordIds];
    // make HTTP callout here
}
```

**Limitation:** You cannot pass sObjects directly. Pass Ids and re-query inside.

---

## Trigger Patterns

### Q6. What is the One Trigger Per Object pattern?

**Answer:**  
Having multiple triggers on the same object creates unpredictable execution order. The best practice is one trigger per object that delegates to a handler class.

**Trigger (thin):**
```apex
trigger AccountTrigger on Account (before insert, before update, after insert, after update) {
    AccountTriggerHandler.handle(Trigger.operationType, Trigger.new, Trigger.oldMap);
}
```

**Handler class:**
```apex
public class AccountTriggerHandler {
    public static void handle(System.TriggerOperation op, List<Account> newList, Map<Id, Account> oldMap) {
        switch on op {
            when BEFORE_INSERT { onBeforeInsert(newList); }
            when BEFORE_UPDATE { onBeforeUpdate(newList, oldMap); }
            when AFTER_INSERT  { onAfterInsert(newList); }
            when AFTER_UPDATE  { onAfterUpdate(newList, oldMap); }
        }
    }
    // individual methods below
}
```

---

### Q7. What is the difference between `Trigger.new` and `Trigger.newMap`?

**Answer:**  
- `Trigger.new` — `List<SObject>` of new record versions. Available on insert, update, undelete.
- `Trigger.newMap` — `Map<Id, SObject>` of new versions keyed by Id. Available on update, undelete (not insert, because records have no Id yet on before insert).
- `Trigger.old` / `Trigger.oldMap` — previous versions. Available on update, delete.

**Common pattern:** Use `Trigger.newMap` to check if a field actually changed:
```apex
for (Account acc : Trigger.new) {
    Account old = Trigger.oldMap.get(acc.Id);
    if (acc.Industry != old.Industry) {
        // field changed — do something
    }
}
```

---

### Q8. When would you use `before` vs `after` trigger context?

**Answer:**  
- **Before trigger** — use to validate or modify field values before they're saved to the database. No DML needed; assign directly to `Trigger.new` records.
- **After trigger** — use when you need the record's Id (only available after save) or when you need to update related records via DML.

Rule of thumb: If you're setting a field on the triggering record → before. If you're creating/updating other records → after.

---

### Q9. How do you prevent recursive trigger execution?

**Answer:**  
Use a static Boolean flag in a utility class:

```apex
public class TriggerContext {
    public static Boolean isFirstRun = true;
}
```

```apex
trigger AccountTrigger on Account (after update) {
    if (TriggerContext.isFirstRun) {
        TriggerContext.isFirstRun = false;
        AccountTriggerHandler.onAfterUpdate(Trigger.new, Trigger.oldMap);
    }
}
```

**Better pattern:** Use a `Set<Id>` to track already-processed record Ids instead of a blanket Boolean, so you only skip the exact records already processed — not all records.

---

## SOQL / SOSL

### Q10. What is the difference between SOQL and SOSL?

**Answer:**  
- **SOQL** (Salesforce Object Query Language) — queries a single object and its relationships. Returns sObject records.
- **SOSL** (Salesforce Object Search Language) — full-text search across multiple objects at once. Returns `List<List<SObject>>`.

Use SOSL when you don't know which object has the data (e.g., user searched a name — could be a Contact, Lead, or Account).

```apex
List<List<SObject>> results = [FIND 'Accenture' IN ALL FIELDS
    RETURNING Account(Name), Contact(FirstName, LastName)];
```

---

### Q11. What is a relationship query? What's the difference between parent-to-child and child-to-parent?

**Answer:**  
**Child-to-parent (dot notation):** Traverse up to the parent from a child record.
```apex
SELECT Id, Name, Account.Name FROM Contact WHERE Account.Industry = 'Technology'
```

**Parent-to-child (subquery):** Retrieve child records inline with the parent. Uses the child's relationship name (usually plural).
```apex
SELECT Id, Name, (SELECT Id, LastName FROM Contacts) FROM Account WHERE Name = 'Accenture'
```

Limit: You can go up to **5 levels** in a child-to-parent query. Subqueries count toward your 100 SOQL governor limit.

---

### Q12. What is SOQL injection and how do you prevent it?

**Answer:**  
SOQL injection is when user-supplied input is concatenated directly into a dynamic SOQL string, allowing manipulation of the query.

**Vulnerable:**
```apex
String name = ApexPages.currentPage().getParameters().get('name');
String query = 'SELECT Id FROM Account WHERE Name = \'' + name + '\'';
List<Account> accs = Database.query(query);
```

A user entering `' OR Name != '` breaks the query logic.

**Safe — use bind variables:**
```apex
String name = ApexPages.currentPage().getParameters().get('name');
List<Account> accs = [SELECT Id FROM Account WHERE Name = :name]; // bind, not concat
```

If you must use dynamic SOQL, escape user input with `String.escapeSingleQuotes()`.

---

## Async Apex

### Q13. What are the 4 types of async Apex? When do you use each?

**Answer:**

| Type | Use When |
|---|---|
| `@future` | Simple one-off async call, callout from trigger, mixed DML |
| `Queueable` | Need to chain jobs, pass sObjects, complex state |
| `Batch Apex` | Processing millions of records in chunks |
| `Scheduled Apex` | Run on a time-based schedule (cron-like) |

**Decision flow:**
- Need to process millions of records? → **Batch**
- Need to run on a schedule? → **Scheduled** (often calls Batch or Queueable)
- Need to chain multiple async operations? → **Queueable**
- Simple background task from trigger? → **@future**

---

### Q14. How does Batch Apex work? What are the 3 methods you must implement?

**Answer:**  
Batch Apex processes large data sets in chunks (default 200 records per batch, max 2,000).

```apex
public class AccountBatch implements Database.Batchable<SObject> {

    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator('SELECT Id, Name FROM Account WHERE Industry = \'Technology\'');
    }

    public void execute(Database.BatchableContext bc, List<Account> scope) {
        // process each chunk of records
        for (Account acc : scope) {
            acc.Description = 'Processed by batch';
        }
        update scope;
    }

    public void finish(Database.BatchableContext bc) {
        // called once after all chunks complete — send notification, chain next job, etc.
        Messaging.SingleEmailMessage mail = new Messaging.SingleEmailMessage();
        // ...
    }
}
```

Execute: `Database.executeBatch(new AccountBatch(), 200);`

---

### Q15. What is Queueable Apex? How is it better than `@future`?

**Answer:**  
Queueable implements the `Queueable` interface and improves on `@future` in 3 ways:
1. **Can pass sObjects** — `@future` only accepts primitives
2. **Chainable** — call `System.enqueueJob()` from inside execute() to chain next job
3. **Job Id returned** — you can monitor via `AsyncApexJob`

```apex
public class SyncQueueable implements Queueable, Database.AllowsCallouts {
    private List<Id> recordIds;

    public SyncQueueable(List<Id> ids) { this.recordIds = ids; }

    public void execute(QueueableContext ctx) {
        List<Account> accounts = [SELECT Id, Name FROM Account WHERE Id IN :recordIds];
        // do work
        // chain next job if needed:
        System.enqueueJob(new NextQueueable(accounts));
    }
}
```

---

## Test Classes

### Q16. What are the minimum requirements for a valid Apex test class?

**Answer:**
- Class must have `@isTest` annotation
- Test methods must have `@isTest` annotation (or `testMethod` keyword — deprecated)
- Must use `Test.startTest()` / `Test.stopTest()` to reset governor limits during the test
- Must use `System.assert()`, `System.assertEquals()`, or `System.assertNotEquals()` — a test with no assertion is worthless
- Must achieve **75% code coverage** org-wide for production deployment

```apex
@isTest
private class AccountServiceTest {
    @TestSetup
    static void setup() {
        Account acc = new Account(Name = 'Test Account');
        insert acc;
    }

    @isTest
    static void testAccountNaming() {
        Account acc = [SELECT Id, Name FROM Account LIMIT 1];
        Test.startTest();
        AccountService.rename(acc.Id, 'New Name');
        Test.stopTest();
        Account updated = [SELECT Name FROM Account WHERE Id = :acc.Id];
        System.assertEquals('New Name', updated.Name, 'Name should be updated');
    }
}
```

---

### Q17. What is `@TestSetup` and why should you use it?

**Answer:**  
`@TestSetup` runs once before all test methods in the class and creates test data that each method gets a fresh copy of. Without it, each test method creates its own data — slower and more DML operations.

Using `@TestSetup` reduces total test DML calls from `N × setup_cost` to `1 × setup_cost`.

---

### Q18. How do you test callouts in Apex?

**Answer:**  
You cannot make real HTTP callouts in tests. Use `HttpCalloutMock`:

```apex
@isTest
global class MockHttpResponse implements HttpCalloutMock {
    global HTTPResponse respond(HTTPRequest req) {
        HttpResponse res = new HttpResponse();
        res.setBody('{"status":"ok"}');
        res.setStatusCode(200);
        return res;
    }
}
```

In your test:
```apex
@isTest
static void testCallout() {
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse());
    Test.startTest();
    MyCalloutService.run();
    Test.stopTest();
    // assert results
}
```

---

# PART 2 — Advanced Apex

---

### Q19. What is the Selector Layer pattern?

**Answer:**  
The Selector Layer (from Apex Enterprise Patterns) centralizes all SOQL queries into dedicated classes. Benefits:
- One place to add fields to a query
- Easy to mock in tests
- Enforces consistent WITH SECURITY_ENFORCED usage

```apex
public class AccountsSelector {
    public List<Account> selectById(Set<Id> ids) {
        return [SELECT Id, Name, Industry, OwnerId
                FROM Account
                WHERE Id IN :ids
                WITH SECURITY_ENFORCED];
    }
}
```

---

### Q20. What is a Platform Event? How does it differ from a trigger?

**Answer:**  
Platform Events are Salesforce's publish-subscribe messaging system. Unlike triggers (which fire synchronously within the same transaction), Platform Events:
- Decouple publisher and subscriber — they run in separate transactions
- Survive errors in the subscriber — publisher transaction isn't rolled back if subscriber fails
- Support external systems subscribing via CometD/Streaming API

```apex
// Publish
Order_Event__e event = new Order_Event__e(Order_Id__c = orderId, Status__c = 'Shipped');
EventBus.publish(event);

// Subscribe (trigger on the platform event object)
trigger OrderEventTrigger on Order_Event__e (after insert) {
    for (Order_Event__e e : Trigger.new) {
        // handle event
    }
}
```

---

### Q21. What is Change Data Capture (CDC)?

**Answer:**  
CDC lets you subscribe to change notifications for Salesforce records — create, update, delete, undelete events — delivered via Streaming API. Unlike triggers, CDC subscribers can be external systems (Node.js, Java, etc.) listening via CometD.

Use case: Sync Salesforce data to an external data warehouse in near-real-time without polling.

---

### Q22. What is the difference between `with sharing` and `without sharing`?

**Answer:**

| Keyword | Behavior |
|---|---|
| `with sharing` | Enforces the running user's record sharing rules. User sees only records they have access to. |
| `without sharing` | Ignores sharing rules. Code runs with full access regardless of user permissions. |
| (no keyword) | Inherits the sharing context of the calling class. |

**Best practice:** Default to `with sharing` for all classes. Only use `without sharing` when you have an explicit business reason (e.g., a system process that must access all records), and document why.

---

### Q23. What is a Named Credential and why should you use it?

**Answer:**  
A Named Credential stores an external endpoint URL + authentication credentials in Salesforce-managed secure storage. Benefits:
- No credentials in Apex code or Custom Settings
- Works with OAuth — Salesforce handles token refresh automatically
- Passes security review for AppExchange

```apex
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:MyExternalAPI/endpoint');  // Named Credential name
req.setMethod('GET');
```

---

### Q24. How do you handle bulkified trigger logic for complex business rules?

**Answer:**  
The Service Layer pattern. Move business logic out of the trigger handler into a service class that accepts collections:

```apex
public class OpportunityService {
    public static void calculateCommission(List<Opportunity> opps, Map<Id, Opportunity> oldMap) {
        // Collect all needed Ids first
        Set<Id> ownerIds = new Set<Id>();
        for (Opportunity opp : opps) ownerIds.add(opp.OwnerId);

        // One query
        Map<Id, User> users = new Map<Id, User>([SELECT Id, Commission_Rate__c FROM User WHERE Id IN :ownerIds]);

        // Process all records
        for (Opportunity opp : opps) {
            User owner = users.get(opp.OwnerId);
            opp.Commission__c = opp.Amount * owner.Commission_Rate__c;
        }
    }
}
```

---

### Q25. What is a Mixed DML error and how do you fix it?

**Answer:**  
A Mixed DML error occurs when you try to perform DML on both setup objects (User, Profile, PermissionSet, etc.) and non-setup objects (Account, Contact, etc.) in the same transaction.

**Fix:** Use `@future` or `System.runAs()` in tests to separate the transactions.

```apex
// In test: use System.runAs() to avoid mixed DML
@isTest
static void testUserCreation() {
    User adminUser = [SELECT Id FROM User WHERE Profile.Name = 'System Administrator' LIMIT 1];
    System.runAs(adminUser) {
        // create setup objects here
    }
    // create non-setup objects outside the runAs block
}
```

---

# PART 3 — Lightning Web Components (LWC)

---

## Core Concepts

### Q26. What is the LWC component lifecycle? List the hooks in order.

**Answer:**

| Hook | When It Fires |
|---|---|
| `constructor()` | Component instance created. Cannot access child elements yet. |
| `connectedCallback()` | Component inserted into the DOM. Use for initialization, event listeners. |
| `renderedCallback()` | Component rendered/re-rendered. Can access DOM elements. Fires after every render. |
| `disconnectedCallback()` | Component removed from DOM. Use to clean up event listeners, timers. |
| `errorCallback(error, stack)` | An error occurs in a child component. Use for error boundaries. |

**Important:** Do NOT call `this.template.querySelector()` in `constructor()` — the DOM isn't ready yet. Use `connectedCallback()` or `renderedCallback()`.

---

### Q27. What is the difference between `@api`, `@track`, and regular properties?

**Answer:**

| Decorator | Purpose |
|---|---|
| `@api` | Exposes a public property or method to the parent component. Reactive — parent changes re-render child. |
| `@track` | (Legacy) Made nested object/array mutations reactive. In API v39+, all properties are reactive to reassignment. `@track` is still needed for nested mutations in older components. |
| (none) | Private property. Reactive to reassignment but not accessible from parent. |

**Current best practice:** Use `@api` for public, nothing for private. Only use `@track` if you're mutating a property's inner fields (e.g., `this.obj.name = 'new'`) and need the UI to react.

---

### Q28. How do child-to-parent and parent-to-child communication work in LWC?

**Answer:**

**Parent-to-child:** Pass data via `@api` properties or call `@api` methods.
```html
<!-- Parent -->
<c-child record-id={selectedId}></c-child>
```
```js
// Child
@api recordId;
```

**Child-to-parent:** Dispatch a `CustomEvent`.
```js
// Child
const event = new CustomEvent('select', { detail: { id: this.recordId } });
this.dispatchEvent(event);
```
```html
<!-- Parent -->
<c-child onselect={handleSelect}></c-child>
```

**Sibling communication:** Use a shared parent as intermediary, or a pub-sub pattern via a message channel (`@salesforce/messageChannel`).

---

### Q29. What is the Wire Service? How does it differ from an imperative Apex call?

**Answer:**  
The `@wire` service reactively provisions data — it automatically re-fetches when its parameters change. It's declarative and integrated with the Lightning Data Service cache.

```js
import { LightningElement, wire } from 'lwc';
import getContacts from '@salesforce/apex/ContactController.getContacts';

export default class ContactList extends LightningElement {
    @wire(getContacts, { accountId: '$recordId' })
    contacts;  // { data, error }
}
```

**Imperative call** — you control when it fires (e.g., on button click, after validation):
```js
import getContacts from '@salesforce/apex/ContactController.getContacts';

async handleSearch() {
    try {
        this.contacts = await getContacts({ accountId: this.recordId });
    } catch (error) {
        this.error = error;
    }
}
```

**Rule of thumb:** Wire for initial data load that depends on record context. Imperative for user-triggered actions.

---

### Q30. How do you access DOM elements in LWC?

**Answer:**  
Use `this.template.querySelector()` (one element) or `this.template.querySelectorAll()` (all matching).

```js
connectedCallback() {
    const input = this.template.querySelector('lightning-input');
    input.focus();
}
```

**Never** use `document.querySelector()` in LWC — it breaks component encapsulation and will not work in Lightning Locker/Shadow DOM.

---

### Q31. What is the Lightning Message Service (LMS)?

**Answer:**  
LMS enables communication between unrelated components (not in a parent-child relationship) — including Aura components, LWC, and Visualforce — using message channels.

```js
// Publisher
import { publish, MessageContext } from 'lightning/messageService';
import MY_CHANNEL from '@salesforce/messageChannel/MyChannel__c';

@wire(MessageContext) messageContext;

handleClick() {
    publish(this.messageContext, MY_CHANNEL, { recordId: this.recordId });
}
```

```js
// Subscriber
import { subscribe, MessageContext } from 'lightning/messageService';
import MY_CHANNEL from '@salesforce/messageChannel/MyChannel__c';

@wire(MessageContext) messageContext;
subscription = null;

connectedCallback() {
    this.subscription = subscribe(this.messageContext, MY_CHANNEL, (msg) => {
        this.handleMessage(msg);
    });
}
```

---

### Q32. What is Shadow DOM and how does it affect LWC styling?

**Answer:**  
LWC uses Shadow DOM to encapsulate component styles — CSS in one component does NOT leak into child components or the page.

**Implications:**
- You cannot style child component internals from a parent's CSS
- Use CSS custom properties (variables) to pass style values across shadow boundaries
- SLDS utility classes work because they're applied to elements you own

```css
/* Parent can pass a variable */
c-child {
    --brand-color: #0070d2;
}
```
```css
/* Child uses the variable */
.my-element {
    color: var(--brand-color);
}
```

---

### Q33. How do you navigate to a record page from an LWC component?

**Answer:**  
Use the `NavigationMixin`:

```js
import { LightningElement } from 'lwc';
import { NavigationMixin } from 'lightning/navigation';

export default class MyComponent extends NavigationMixin(LightningElement) {
    navigateToRecord(recordId) {
        this[NavigationMixin.Navigate]({
            type: 'standard__recordPage',
            attributes: {
                recordId: recordId,
                actionName: 'view'
            }
        });
    }
}
```

---

### Q34. What is the difference between `connectedCallback` and `renderedCallback`?

**Answer:**  
- `connectedCallback` fires once when the component is added to the DOM. Use for initialization, subscriptions, initial data setup.
- `renderedCallback` fires after every render (initial + every re-render triggered by reactive property changes). 

**Warning:** Do not do DML, callouts, or data fetching in `renderedCallback` without a guard — it can cause infinite re-render loops.

```js
renderedCallback() {
    if (this.hasRendered) return;
    this.hasRendered = true;
    // one-time DOM manipulation
}
```

---

### Q35. How do you handle errors gracefully in LWC?

**Answer:**  
Use `errorCallback()` as an error boundary for child component errors, and `try/catch` for imperative Apex calls. For wire errors, check the `error` property.

```js
// Wire error handling
@wire(getContacts) 
wiredContacts({ data, error }) {
    if (data) {
        this.contacts = data;
        this.error = undefined;
    } else if (error) {
        this.error = error.body.message;
        this.contacts = undefined;
    }
}
```

Display errors using `lightning-card` with an alert, or a dedicated `c-error-panel` component.

---

### Q36. What is a Base Lightning Component? Give 3 examples.

**Answer:**  
Base Lightning Components are Salesforce-provided pre-built components that follow SLDS standards automatically.

| Component | Use Case |
|---|---|
| `lightning-record-form` | Display/edit a record with automatic FLS enforcement |
| `lightning-datatable` | Sortable, selectable data table |
| `lightning-input` | Form input with built-in validation |
| `lightning-combobox` | Dropdown select |
| `lightning-button` | Styled button |
| `lightning-card` | Container with header, footer slots |
| `lightning-toast` (new) | Show toast notifications in LWC |

---

### Q37. How do you test LWC components?

**Answer:**  
LWC uses **Jest** for unit tests. Tests live in `__tests__/` next to the component.

```js
// contactList/__tests__/contactList.test.js
import { createElement } from 'lwc';
import ContactList from 'c/contactList';
import getContacts from '@salesforce/apex/ContactController.getContacts';

jest.mock('@salesforce/apex/ContactController.getContacts', () => ({
    default: jest.fn()
}), { virtual: true });

describe('c-contact-list', () => {
    afterEach(() => { while (document.body.firstChild) document.body.removeChild(document.body.firstChild); });

    it('renders contacts', async () => {
        getContacts.mockResolvedValue([{ Id: '001', Name: 'Test' }]);
        const element = createElement('c-contact-list', { is: ContactList });
        document.body.appendChild(element);
        await Promise.resolve();
        const items = element.shadowRoot.querySelectorAll('li');
        expect(items.length).toBe(1);
    });
});
```

---

### Q38. What is `lightning-record-edit-form` vs `lightning-record-form`?

**Answer:**

| Component | Control Level |
|---|---|
| `lightning-record-form` | Simple. Auto-generates layout. Less customization. |
| `lightning-record-edit-form` | Full control over field layout, custom validation, custom submit handling. |

Use `lightning-record-form` for standard CRUD UIs. Use `lightning-record-edit-form` when you need custom field placement, conditional fields, or custom submit logic.

---

### Q39. What is a Slot in LWC?

**Answer:**  
Slots allow a parent to inject HTML content into a child component's template.

```html
<!-- child: c-card -->
<template>
    <div class="card">
        <slot name="header"></slot>
        <slot></slot>  <!-- default slot -->
    </div>
</template>
```

```html
<!-- parent -->
<c-card>
    <span slot="header">My Title</span>
    <p>Body content goes in the default slot</p>
</c-card>
```

---

### Q40. What is `@salesforce/resourceUrl` used for?

**Answer:**  
To reference static resources (images, CSS, JS libraries) stored in Salesforce Static Resources.

```js
import MY_IMAGE from '@salesforce/resourceUrl/myImage';
```

```html
<img src={myImageUrl} />
```

---

# PART 4 — Agentforce & AI

---

### Q41. What is Agentforce? How does it differ from Einstein Copilot?

**Answer:**  
Agentforce is Salesforce's autonomous AI agent platform — agents that can reason, plan, and take actions across Salesforce without step-by-step human instruction. Einstein Copilot (rebranded as Agentforce as of 2024) was the earlier embedded AI assistant in the Salesforce UI.

The key distinction: Agentforce agents can run multi-step workflows autonomously, handle async tasks, and integrate with external systems — not just answer questions.

---

### Q42. What are the 5 core components of an Agentforce Agent?

**Answer:**

| Component | Purpose |
|---|---|
| **Agent** | The top-level container — defines the agent's identity and scope |
| **Topic** | A domain or category of tasks the agent handles (e.g., "Order Management") |
| **Instructions** | Natural language rules that guide the agent's behavior within a topic |
| **Action** | What the agent can DO — Apex, Flow, Prompt Template, or MuleSoft API |
| **Guardrails** | Rules that restrict what the agent should NOT do |

---

### Q43. What types of Actions can an Agentforce agent perform?

**Answer:**

| Action Type | Description |
|---|---|
| **Apex Action** | Calls an `@InvocableMethod` Apex class |
| **Flow Action** | Runs an Autolaunched Flow |
| **Prompt Template** | Sends a prompt to an LLM and returns the response |
| **MuleSoft API Action** | Calls an external API via MuleSoft |
| **Knowledge Search** | Retrieves articles from Salesforce Knowledge |

---

### Q44. What is a Prompt Template in Salesforce? How do you create one?

**Answer:**  
Prompt Templates are reusable LLM prompts built in Prompt Builder. They can reference merge fields from Salesforce records, use Flow for data enrichment, and be called from Agentforce actions, Flows, or Apex.

**Types:**
- **Record Summary** — Summarize a record
- **Field Generation** — Generate a value for a specific field
- **Sales Email** — Draft emails with record context
- **Flex Template** — Free-form, custom use cases

You create them in **Setup → Prompt Builder**. They support Flex merge fields with dot notation: `{!$Input:Account.Name}`.

---

### Q45. How do you invoke a Prompt Template from Apex?

**Answer:**

```apex
ConnectApi.EinsteinPromptTemplateGenerationsInput promptInput = 
    new ConnectApi.EinsteinPromptTemplateGenerationsInput();
promptInput.isPreview = false;

Map<String, ConnectApi.WrappedValue> inputParams = new Map<String, ConnectApi.WrappedValue>();
ConnectApi.WrappedValue wrappedId = new ConnectApi.WrappedValue();
wrappedId.value = recordId;
inputParams.put('Input:Account', wrappedId);
promptInput.inputParams = inputParams;

ConnectApi.EinsteinPromptTemplateGenerationsRepresentation result = 
    ConnectApi.EinsteinLLM.generateMessagesForPromptTemplate('My_Template_Name', promptInput);

String generatedText = result.generations[0].text;
```

---

### Q46. What is the `@InvocableMethod` annotation? How does it relate to Agentforce?

**Answer:**  
`@InvocableMethod` exposes an Apex method to Flow, Process Builder, and Agentforce Actions. Agentforce can invoke these methods as actions when an agent decides the task requires it.

```apex
public class GetAccountSummaryAction {
    @InvocableMethod(
        label='Get Account Summary'
        description='Returns a summary of an account given its ID. Use when the user asks about account details.'
    )
    public static List<String> getSummary(List<Id> accountIds) {
        List<String> summaries = new List<String>();
        for (Account acc : [SELECT Name, Industry, AnnualRevenue FROM Account WHERE Id IN :accountIds]) {
            summaries.add(acc.Name + ' | ' + acc.Industry + ' | $' + acc.AnnualRevenue);
        }
        return summaries;
    }
}
```

**The `description` matters** — the LLM reads it to decide which action to call. Be specific and natural-language clear.

---

### Q47. What are Guardrails in Agentforce?

**Answer:**  
Guardrails are natural language rules that tell the agent what it must NOT do. They enforce business rules, compliance requirements, and safety constraints.

Examples:
- "Never share a customer's payment information"
- "Do not create Opportunities without manager approval"
- "Always escalate cases rated Priority 1 to a human agent"

Guardrails are configured at the Topic level in the Agentforce builder.

---

### Q48. What is Einstein for Developers (formerly CodeGen)?

**Answer:**  
Einstein for Developers is Salesforce's AI coding assistant integrated into VS Code via the Salesforce Extension Pack. Capabilities:
- Inline Apex code generation from comments
- Auto-complete for SOQL, Apex, LWC
- Test class generation
- Code explanation in plain English

Triggered by writing a comment describing what you want, then using the generate shortcut.

---

### Q49. What is the difference between Agentforce for Service and Agentforce for Sales?

**Answer:**

| | Agentforce for Service | Agentforce for Sales |
|---|---|---|
| **Use case** | Customer support, case deflection, self-service | SDR prospecting, meeting prep, follow-up |
| **Channels** | Chat, Email, Messaging, Voice | Email, CRM activity |
| **Key actions** | Deflect cases, update records, escalate to human | Research prospects, draft emails, update pipeline |
| **Key metric** | Case deflection rate | Meetings booked, pipeline influenced |

---

### Q50. What is Data Cloud and how does it relate to Agentforce?

**Answer:**  
Data Cloud is Salesforce's real-time customer data platform that unifies data from multiple sources into a single customer profile. Agentforce uses Data Cloud as its data layer — agents can query unified customer profiles, trigger automations based on real-time signals, and ground LLM responses in actual customer data instead of hallucinating.

Key integration: **Retrieval Augmented Generation (RAG)** — Agentforce agents use Data Cloud vectors to retrieve relevant customer context before generating a response.

---

# PART 5 — Revenue Cloud / CPQ

---

### Q51. What is Salesforce CPQ? What problem does it solve?

**Answer:**  
CPQ (Configure, Price, Quote) automates the quoting process for complex products. It solves:
- Products with many variants and options (configuration rules)
- Pricing logic that's too complex for standard Price Books (discount schedules, price rules, block pricing)
- Consistent, legally-compliant quotes generated in minutes instead of hours

---

### Q52. What is a Price Rule in CPQ?

**Answer:**  
Price Rules automate field updates on Quote Lines, Quotes, or other objects when certain conditions are met. They fire during the pricing calculation step.

**Components:**
1. **Conditions** — When does this rule fire? (e.g., Product Family = 'Hardware')
2. **Actions** — What gets updated? (e.g., set Quote Line's List Price to a calculated value)

Price Rules replace complex Apex triggers for pricing logic.

---

### Q53. What is the difference between a Product Rule and a Price Rule?

**Answer:**

| | Product Rule | Price Rule |
|---|---|---|
| **Purpose** | Control what products can be selected together | Calculate and set pricing fields |
| **Types** | Alert, Validation, Selection, Filter | — |
| **When it fires** | Configuration step (when user picks products) | Pricing step (when calculating prices) |
| **Example** | "Cannot add GPU without Workstation base product" | "Apply 10% discount when quantity > 100" |

---

### Q54. What is a Subscription product in CPQ? What is a Renewal?

**Answer:**  
A Subscription product has a defined term (e.g., 12 months, annual). CPQ tracks:
- Start Date / End Date
- Subscription Term
- Pricing Method (e.g., per month, per year)

A **Renewal** is a new Quote automatically generated before the subscription expires — CPQ creates it from the existing contracted products. The Renewal Opportunity is linked to the original.

---

### Q55. What is Revenue Cloud (formerly Billing)?

**Answer:**  
Revenue Cloud extends CPQ into the post-sale revenue lifecycle:
- **Order Management** — Converts Quotes to Orders
- **Billing** — Generates invoices, manages billing schedules, handles proration
- **Revenue Recognition** — Compliant revenue scheduling (ASC 606 / IFRS 15)
- **Collections** — Payment tracking, dunning

The full Quote-to-Cash process lives in Revenue Cloud: CPQ (configure/price/quote) → Orders → Billing → Revenue Recognition → Collections.

---

### Q56. What is an Amendment in CPQ?

**Answer:**  
An Amendment modifies an active subscription mid-term. Use cases:
- Upgrade from 10 seats to 20 seats
- Add a new product to an existing contract
- Remove a product before renewal

CPQ creates an Amendment Quote from the active Contract. It automatically handles proration — adjusting prices based on remaining subscription days.

---

# PART 6 — Cheat Sheet

---

## Governor Limits (Memorize These)

| Limit | Sync | Async |
|---|---|---|
| SOQL queries | 100 | 200 |
| SOQL rows returned | 50,000 | 50,000 |
| DML statements | 150 | 150 |
| DML rows | 10,000 | 10,000 |
| CPU time | 10,000 ms | 60,000 ms |
| Heap size | 6 MB | 12 MB |
| Callouts | 100 | 100 |
| @future calls per tx | 50 | — |
| Batch jobs queued | 5 | — |
| Push topics | 50 | — |

---

## Trigger Context Variables

| Variable | Type | Available |
|---|---|---|
| `Trigger.new` | List<SObject> | insert, update, undelete |
| `Trigger.old` | List<SObject> | update, delete |
| `Trigger.newMap` | Map<Id,SObject> | update, undelete |
| `Trigger.oldMap` | Map<Id,SObject> | update, delete |
| `Trigger.isBefore` | Boolean | all |
| `Trigger.isAfter` | Boolean | all |
| `Trigger.isInsert` | Boolean | all |
| `Trigger.isUpdate` | Boolean | all |
| `Trigger.isDelete` | Boolean | all |
| `Trigger.operationType` | System.TriggerOperation | all |

---

## LWC Lifecycle Hooks (In Order)

```
constructor()        → instance created, no DOM access
connectedCallback()  → added to DOM, initialize here
render()             → returns template (optional override)
renderedCallback()   → DOM ready, guard against infinite loops
disconnectedCallback() → cleanup, remove listeners
errorCallback()      → child error boundary
```

---

## Async Apex Decision Tree

```
Need to process millions of records?
  YES → Batch Apex (Database.executeBatch)
  NO  ↓
Need to run on schedule?
  YES → Scheduled Apex (System.schedule)
  NO  ↓
Need to chain jobs or pass sObjects?
  YES → Queueable (System.enqueueJob)
  NO  ↓
Simple background task / callout from trigger?
  YES → @future
```

---

## Common Interview Red Flags (What NOT to Say)

| ❌ Don't Say | ✅ Say Instead |
|---|---|
| "I put the SOQL inside the loop for simplicity" | "I always query outside loops and use Maps" |
| "We don't need test classes for this" | "I aim for 85%+ coverage with meaningful assertions" |
| "I use `without sharing` by default" | "I default to `with sharing` and justify exceptions" |
| "I just used `eval()` for dynamic logic" | "I use safe patterns like `Database.query()` with bind variables" |
| "I didn't document why we used `without sharing`" | "I always comment security-sensitive code choices" |

---

## SOQL Performance Tips

1. **Use selective filters** — filter on indexed fields (Id, Name, ExternalId, Owner, CreatedDate, custom indexed fields)
2. **Avoid `LIKE '%text'`** — leading wildcard kills index usage
3. **Limit fields** — only SELECT fields you need
4. **Use LIMIT** — especially in loops and exploratory queries
5. **Parent field filtering is faster** — `WHERE Account.Industry = 'Tech'` uses Account index
6. **Check query plan** — use the Developer Console Query Plan tool

---

## Key Relationships to Know

| Child Object | Parent | Relationship Field |
|---|---|---|
| Contact | Account | AccountId |
| Opportunity | Account | AccountId |
| Case | Account | AccountId |
| Case | Contact | ContactId |
| OpportunityLineItem | Opportunity | OpportunityId |
| OpportunityLineItem | PricebookEntry | PricebookEntryId |
| Quote | Opportunity | OpportunityId |
| Task/Event | Any | WhoId (person), WhatId (non-person) |

---

## LWC vs Aura — When Interviewers Ask

| | LWC | Aura |
|---|---|---|
| Standard | Web Components standard | Proprietary |
| Performance | Faster (native browser) | Slower |
| Testing | Jest | — (limited) |
| Shadow DOM | Native | Synthetic |
| Status | Current (use this) | Legacy (migrate away) |
| Interop | LWC inside Aura ✅ | Aura inside LWC ❌ |

---

## Your Personal Story Answers

Prepare a 2-3 sentence story for each:

- **"Tell me about a complex trigger you built"** → Mention bulkification, one-trigger pattern, handler class, test coverage
- **"Describe a time you hit governor limits"** → Explain what you diagnosed, how you refactored to bulk patterns
- **"How do you approach a new LWC component?"** → Requirements, wire vs imperative, SLDS first, Jest tests
- **"Agentforce experience?"** → Mention Topics, Actions, @InvocableMethod, Prompt Builder
- **"What's your approach to code reviews?"** → Bulkification, with sharing, SOQL injection, test assertions

---

*MadjosBuilds — Built by Lorenzo Madjos, Platform App Manager @ Accenture*  
*Salesforce AI Associate · Platform App Builder · Certified Scrum Master*
