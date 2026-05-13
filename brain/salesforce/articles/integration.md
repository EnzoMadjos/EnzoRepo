# Salesforce Integration Patterns — Knowledge Base
> Source: Salesforce Integration Patterns, API v67.0, Summer '26, official docs
> Last updated: 2026-05-13

---

## 1. Integration Pattern Overview

| Pattern | Protocol | When to Use |
|---|---|---|
| REST API | HTTP/JSON | External app reads/writes SF data |
| SOAP API | HTTP/XML | Legacy enterprise systems, strong typing needed |
| Bulk API 2.0 | HTTP/JSON (async) | Large data volumes (100K+ records) |
| Streaming API | Bayeux/CometD | Real-time data changes to external app |
| Platform Events | Pub/Sub | Event-driven decoupled integrations |
| Change Data Capture (CDC) | Pub/Sub | Subscribe to record changes |
| Apex Callouts | HTTP/SOAP | SF calling external systems |
| External Services | OpenAPI | Low-code callouts from Flow/REST |
| Named Credentials | Auth config | Secure endpoint storage for callouts |
| Outbound Messages | SOAP push | Legacy: push SF data on workflow rule |

---

## 2. REST API (External → Salesforce)

### Authentication: OAuth 2.0 (JWT Bearer)
```
POST /services/oauth2/token
grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer
assertion=<signed JWT>
```

### Authentication: OAuth 2.0 (Client Credentials — for server-to-server)
```bash
curl -X POST https://login.salesforce.com/services/oauth2/token \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_CONSUMER_KEY" \
  -d "client_secret=YOUR_CONSUMER_SECRET"
# Returns: access_token, instance_url
```

### CRUD Operations
```bash
# Query
GET /services/data/v67.0/query?q=SELECT+Id,Name+FROM+Account+LIMIT+10
Authorization: Bearer <access_token>

# Get record
GET /services/data/v67.0/sobjects/Account/recordId

# Create record
POST /services/data/v67.0/sobjects/Account/
Content-Type: application/json
{"Name": "Acme Corp", "Industry": "Technology"}

# Update record (PATCH — partial update)
PATCH /services/data/v67.0/sobjects/Account/recordId
{"Industry": "Manufacturing"}

# Delete record
DELETE /services/data/v67.0/sobjects/Account/recordId

# Upsert by external ID
PATCH /services/data/v67.0/sobjects/Account/ExternalId__c/EXT-001
{"Name": "Acme Corp"}
```

### Composite API (batch multiple requests)
```json
POST /services/data/v67.0/composite/
{
  "allOrNone": true,
  "compositeRequest": [
    {
      "method": "POST",
      "url": "/services/data/v67.0/sobjects/Account/",
      "referenceId": "newAccount",
      "body": {"Name": "Test Account"}
    },
    {
      "method": "POST",
      "url": "/services/data/v67.0/sobjects/Contact/",
      "referenceId": "newContact",
      "body": {
        "LastName": "Smith",
        "AccountId": "@{newAccount.id}"
      }
    }
  ]
}
```

---

## 3. Bulk API 2.0

For inserting/updating/deleting large datasets (100K+ records).

```bash
# Step 1: Create job
POST /services/data/v67.0/jobs/ingest/
{"object": "Account", "operation": "insert", "contentType": "CSV"}
# Returns: jobId

# Step 2: Upload data
PUT /services/data/v67.0/jobs/ingest/{jobId}/batches
Content-Type: text/csv
Name,Industry
Acme Corp,Technology
Widget Inc,Manufacturing

# Step 3: Close job (trigger processing)
PATCH /services/data/v67.0/jobs/ingest/{jobId}
{"state": "UploadComplete"}

# Step 4: Poll status
GET /services/data/v67.0/jobs/ingest/{jobId}
# state: Open → UploadComplete → InProgress → JobComplete/Failed

# Step 5: Get results
GET /services/data/v67.0/jobs/ingest/{jobId}/successfulResults/
GET /services/data/v67.0/jobs/ingest/{jobId}/failedResults/
```

---

## 4. Apex Callouts (Salesforce → External)

### Named Credentials (recommended — no secrets in code)
```apex
// Named Credential: "ExternalPaymentAPI" (setup in Setup → Named Credentials)
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:ExternalPaymentAPI/payments/charge');
req.setMethod('POST');
req.setHeader('Content-Type', 'application/json');
req.setBody(JSON.serialize(payload));
req.setTimeout(10000);  // 10 seconds max (120s absolute max)

Http http = new Http();
HttpResponse res = http.send(req);
if (res.getStatusCode() == 200) {
    Map<String, Object> result = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
}
```

### Callout from Trigger (must be async)
```apex
// Triggers CANNOT make callouts synchronously
// ✅ Use @future(callout=true)
@future(callout=true)
public static void notifyExternalSystem(Set<Id> accountIds) {
    List<Account> accounts = [SELECT Id, Name FROM Account WHERE Id IN :accountIds];
    // make callout
}

// Or use Queueable with Database.AllowsCallouts
public class ExternalSyncJob implements Queueable, Database.AllowsCallouts {
    private Set<Id> ids;
    public ExternalSyncJob(Set<Id> ids) { this.ids = ids; }
    public void execute(QueueableContext ctx) {
        // make callout here
    }
}
```

### SOAP Callout (via WSDL2Apex)
```apex
// Generated stub from WSDL
SoapApiStub.SoapPort stub = new SoapApiStub.SoapPort();
stub.timeout_x = 30000;
// Use Named Credential endpoint
stub.endpoint_x = 'callout:MySoapService';
SoapApiStub.ResponseType response = stub.processOrder(orderId);
```

### Mock Callouts in Tests
```apex
// Implement HttpCalloutMock
@IsTest
global class MockHttpResponse implements HttpCalloutMock {
    global HTTPResponse respond(HTTPRequest req) {
        HttpResponse res = new HttpResponse();
        res.setStatusCode(200);
        res.setBody('{"status": "success", "id": "12345"}');
        return res;
    }
}

// Use in test
@IsTest
static void testCallout() {
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse());
    Test.startTest();
    ExternalSyncJob job = new ExternalSyncJob(testIds);
    System.enqueueJob(job);
    Test.stopTest();
}
```

---

## 5. Platform Events

Platform Events enable **event-driven, decoupled** integrations.

### Publish from Apex
```apex
// Define: Setup → Platform Events → New (MyEvent__e with fields)
// Publish
MyEvent__e event = new MyEvent__e(
    OrderId__c = orderId,
    Status__c = 'PROCESSED',
    Timestamp__c = DateTime.now()
);
Database.SaveResult result = EventBus.publish(event);
if (!result.isSuccess()) {
    for (Database.Error err : result.getErrors()) {
        Logger.error('Event publish failed: ' + err.getMessage());
    }
}
```

### Bulk Publish
```apex
List<MyEvent__e> events = new List<MyEvent__e>();
for (Order o : processedOrders) {
    events.add(new MyEvent__e(OrderId__c = o.Id, Status__c = 'DONE'));
}
List<Database.SaveResult> results = EventBus.publish(events);
```

### Subscribe from Apex (Trigger on Platform Event)
```apex
// Trigger: fires when event received
trigger MyEventTrigger on MyEvent__e (after insert) {
    for (MyEvent__e event : Trigger.new) {
        // process event payload
        // Note: EventUuid and ReplayId available
        String replayId = (String) event.get('ReplayId');
    }
}
```

### Subscribe from External System (Streaming API)
```bash
# CometD subscription
POST /cometd/67.0/
{
  "channel": "/event/MyEvent__e",
  "replayId": -1   // -1 = all new events; -2 = all retained events (72hrs)
}
```

### Platform Events vs Standard Objects
| | Platform Events | Standard Objects |
|---|---|---|
| Trigger fires | After publish | After DML |
| Rollback | NOT rolled back on Apex error | Rolled back |
| Retry | EventBus handles delivery | None |
| Order guaranteed | Within publisher | None |
| Retention | 72 hours | Until deleted |

---

## 6. Change Data Capture (CDC)

CDC publishes change events for **any enabled standard or custom object**.

```bash
# Enable CDC: Setup → Change Data Capture → select objects

# Subscribe (same as Platform Events)
Channel: /data/AccountChangeEvent
ReplayId: -1 (new events) or -2 (last 72hrs)

# Event payload example
{
  "ChangeEventHeader": {
    "entityName": "Account",
    "changeType": "UPDATE",    // CREATE, UPDATE, DELETE, UNDELETE
    "changedFields": ["Name", "Industry"],
    "recordIds": ["001xx000003GYn1AAG"]
  },
  "Name": "New Name",
  "Industry": "Technology"
  // Only changed fields are included
}
```

### CDC in Flow (Platform Event Triggered Flow)
1. Trigger: Platform Event Received → `AccountChangeEvent`
2. Check `ChangeEventHeader.changeType` = 'UPDATE'
3. Get record → process changes

---

## 7. External Services (Low-Code Callouts)

Register an OpenAPI 3.0 spec → Salesforce generates invocable actions → use from Flow.

```
Setup → External Services → Add External Service
→ Name: PaymentGateway
→ URL: https://api.payment.com/openapi.json (must be reachable)
→ Named Credential: PaymentGatewayNC

→ Actions generated: PaymentGateway.createCharge, PaymentGateway.getCharge, etc.
→ Use in Flow: Action element → External Services → PaymentGateway.createCharge
```

---

## 8. Named Credentials

Centralize endpoint + auth config — never hardcode URLs or secrets in Apex.

```
Setup → Named Credentials → New (Legacy) or New (2022+)

Type: Named Credential (holds URL + auth)
Name: ExternalPaymentAPI
URL: https://api.payment.com
Identity Type: Named Principal (org-wide) or Per User
Auth Protocol: OAuth 2.0 / Basic / JWT / No Auth

Type: External Credential (holds auth scheme)
→ Link to Named Credential
→ Grant permission via Principal
```

```apex
// Usage (no URL or token in code)
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:ExternalPaymentAPI/v1/charge');
// Auth header injected automatically
```

---

## 9. Integration Anti-Patterns

| Anti-Pattern | Problem | Fix |
|---|---|---|
| Hardcoded endpoints/tokens in Apex | Security risk, hard to maintain | Use Named Credentials |
| Callout inside trigger (sync) | Runtime exception | Use `@future(callout=true)` or Queueable |
| No retry logic for external callouts | Silent failures | Implement retry with exponential backoff |
| Processing all records in one `@future` | 150 `@future` per tx limit | Use Queueable with chunked processing |
| Platform Event without fault handling | Lost events on error | Check `EventBus.publish` results, log failures |
| Point-to-point integrations everywhere | Tight coupling, hard to change | Use Platform Events as event bus |
| Using Workflow Outbound Messages | SOAP-only, deprecated path | Migrate to Platform Events or Apex callouts |

---

## 10. Security Checklist for Integrations

- [ ] OAuth 2.0 only — no Basic Auth with username/password in code
- [ ] Named Credentials for all endpoints — no hardcoded URLs
- [ ] IP restrictions on Connected Apps (Trusted IPs setting)
- [ ] Minimum scopes on OAuth — only what's needed (api, refresh_token)
- [ ] Callouts over HTTPS only — validate certificates
- [ ] Validate inbound webhook payloads (HMAC signature or shared secret)
- [ ] Rate limiting on inbound REST API (via Salesforce quotas + custom logic)
- [ ] Log all integration events for audit trail
