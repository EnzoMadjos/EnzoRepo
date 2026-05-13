# Salesforce Flow — Knowledge Base
> Source: Salesforce Automation (Summer '26), official docs, best practices
> Last updated: 2026-05-13

---

## 1. Flow Types

| Flow Type | Trigger | Runs As | Use For |
|---|---|---|---|
| **Record-Triggered Flow** | DML event (create/update/delete) | System (sharing = record context) | Automation on record changes |
| **Screen Flow** | User launches manually | User | Guided data entry, wizards |
| **Scheduled Flow** | Time-based cron | System | Nightly batch, reminder emails |
| **Platform Event Flow** | Platform Event received | System | Async event processing |
| **Autolaunched Flow** | Called from Apex / Process / REST | System | Reusable business logic |
| **Orchestration** | Salesforce Orchestrator | System | Multi-step cross-user workflows |

---

## 2. Record-Triggered Flow Decision Matrix

| Need | Recommended Tool |
|---|---|
| Field update on same record (simple) | Record-Triggered Flow (before save) |
| Update related records | Record-Triggered Flow (after save) |
| Complex branching, formula-heavy | Record-Triggered Flow |
| Cross-object update + DML | Record-Triggered Flow (after save) |
| Needs callout / HTTP | Apex (flows can't make callouts) |
| Needs complex bulk processing | Apex Trigger + Batch |
| Multiple triggers on same object | Flow beats multiple triggers |
| Advanced query/SOQL | Apex |

### Before vs After Save
| | Before Save | After Save |
|---|---|---|
| Access record ID | ❌ (not yet committed) | ✅ |
| Update triggering record | ✅ (no extra DML) | ❌ (requires DML element — causes recursive concern) |
| Create/update related records | ❌ | ✅ |
| Speed | Faster | Slightly slower |

---

## 3. Flow Bulkification

Flows are **automatically bulkified** — they process collections of records. Key rules:

✅ **Do use:**
- Get Records → loop → update records → Update Records (outside loop)
- Collections in loops, accumulate then DML once

❌ **Anti-patterns:**
- DML inside a loop element (creates DML for each record — hits 150 limit)
- Get Records inside a loop (SOQL inside loop — hits 100 limit)
- More than 3 levels of sub-flow nesting (performance hit)

```
Good pattern:
[Loop] → [Assignment to collection] → [end loop] → [Update Records]

Bad pattern:
[Loop] → [Update Records] → [end loop]   ← DML per iteration!
```

---

## 4. Invocable Apex from Flow

When Flow can't do something natively, delegate to Apex via `@InvocableMethod`.

```apex
public class GetAccountTier {
    @InvocableMethod(label='Get Account Tier' description='Returns tier based on revenue')
    public static List<Result> getTier(List<Request> requests) {
        List<Result> results = new List<Result>();
        for (Request req : requests) {
            Result res = new Result();
            res.tier = req.annualRevenue > 1000000 ? 'Enterprise' : 'SMB';
            results.add(res);
        }
        return results;
    }

    public class Request {
        @InvocableVariable(required=true) public Decimal annualRevenue;
    }
    public class Result {
        @InvocableVariable public String tier;
    }
}
```

**Rules for InvocableMethod:**
- Input/Output must be `List<T>` — receives a collection, returns a collection
- Supports primitives, sObjects, and custom Apex classes with `@InvocableVariable`
- Can be called from Flows, Processes, REST API via `/actions/custom/apex/`
- No `@future` inside invocable methods called from Flow (already async context risk)

---

## 5. Screen Flow Patterns

```
Pattern: Multi-Step Wizard
Screen 1 → Decision (has account?) → [Yes] → Screen 2 (confirm)
                                   → [No]  → Screen 2 (create account) → Screen 3
→ Create Records
→ Screen: Success

Best practices:
- Use formula resources for display logic (avoid redundant screens)
- Section components group fields visually
- Fault paths on every DML element
- "Navigate" component to redirect to record after success
```

### Screen Flow: Embedding in LWC
```html
<template>
    <lightning-flow flow-api-name="My_Screen_Flow"
                    flow-input-variables={inputVars}
                    onstatuschange={handleStatusChange}>
    </lightning-flow>
</template>
```
```js
inputVars = [{ name: 'recordId', type: 'String', value: this.recordId }];
handleStatusChange(event) {
    if (event.detail.status === 'FINISHED') {
        // flow finished
    }
}
```

---

## 6. Scheduled Flow

```
Trigger: Scheduled
- Frequency: Run once, Daily, Weekly
- Start date/time: configurable
- Object: choose starting record collection

Example: Every day at 6am, get all Cases open > 7 days, send email to owner

Decision: Don't build scheduled flows that query >50K records
Alternative: Use Scheduled Apex with Database.getQueryLocator for large volumes
```

---

## 7. Platform Event Flow

```
Trigger: Platform Event Received (e.g., OrderFulfilled__e)
- Subscribe to event channel
- Process event payload
- Create/update records based on event

Note: Platform Event Flows can't be paused/resumed — they run to completion
Resume After Wait element NOT available in Platform Event Flow
```

---

## 8. Flow vs Apex: Decision Guide

| Scenario | Use |
|---|---|
| Simple field updates on same/related objects | **Flow** |
| Guided user input with complex branching | **Screen Flow** |
| Time-based automation (reminders, SLA) | **Scheduled Flow** |
| Event-driven async processing | **Platform Event Flow** |
| Complex SOQL / aggregate queries | **Apex** |
| HTTP callouts | **Apex** |
| Bulk processing > 50K records | **Apex Batch** |
| Re-entrant logic / recursion control needed | **Apex** |
| Packaged / ISV product | **Apex** (flows harder to extend) |
| Admin maintenance needed (no-code) | **Flow** |

---

## 9. Flow Debugging Tips

1. **Debug mode**: Run flow in Debug → shows each element, variable values at each step
2. **Fault paths**: Always add fault connector from Get/Update/Create Records elements to display error
3. **After Save infinite loop**: Use formula condition `{!$Record.ProcessedByFlow__c} = false` or `ISCHANGED({!$Record.Field})` to prevent re-entry
4. **Flow Interview**: In Setup → Flows → Flow Interviews — see paused/waiting flows
5. **Debug log**: For invocable Apex called from flow — set debug level, check `FLOW_ELEMENT` events in log

---

## 10. Flow Limits (per transaction)
| Resource | Limit |
|---|---|
| Total elements processed | 2,000 |
| SOQL queries | 100 (shared with transaction) |
| DML rows | 10,000 (shared) |
| Max flow interviews (bulk) | 200 active at once |
| Sub-flow depth | 10 levels |
| Loop iterations | 2,000 |
