# Repo Knowledge — sfdc-truckin

> **Critical rule:** Before writing new utilities, helpers, or patterns — check this file first. Reuse what already exists. Do not reinvent logging, mocking, callouts, feature flags, or query building.

---

## Quick Lookup: "When you need X, use Y"

| When you need to... | Use this |
|---------------------|----------|
| Log errors or info | `Logr` class → `TruckinLog__c` |
| Log with SObject context | `TruckinLogFactory` → caller must `insert` the returned record |
| Auto-log + throw exception | `TruckinException.createAndLog()` |
| Check a feature flag | `FeatureManagerSelector` or `Feature_Manager__mdt.getInstance('Name').isActive__c` |
| Make an HTTP callout | `Webservice_Setting__mdt` + Named Credential pattern |
| Get Okta bearer token | `OktaInternalService.getInternalAccessToken()` |
| Track callout for retry | `REST_Callout_Job__c` + `RESTCalloutBatch` |
| Write a trigger | Extend `TriggerHandler`, call `new Handler().run()` in trigger |
| Disable a trigger at runtime | `TriggerHandler.bypass('HandlerName')` |
| Disable ALL triggers | Set `TriggerControl__c.IsEnabled__c = false` |
| Create a service class | Singleton with `ServiceFactory.get()` |
| Mock a service in tests | `DI.mock(MyService.class)` |
| Bypass sharing rules | `WithoutSharing.fetchOne(query)` / `WithoutSharing.doUpdate(records)` |
| Handle nulls safely | `Optional.of(value, default)` |
| Work with collections | `CollectionUtils.intersect()`, `.isEmpty()`, `.slice()` |
| Create test data | `TestUtilities.create{Type}(fieldMap, doInsert)` |
| Generate fake IDs in tests | `TestUtils.generateFakeId(SObjectType)` |
| Mock HTTP callouts | `PortalHttpMock(statusCode, body)` or `MultiRequestMock` |
| Chain batch jobs | Extend `ChainableBatch`, use `.chain().run()` |
| Async callout | `Queueable` + `Database.AllowsCallouts` + `SonosTransactionFinalizerUtility` |
| Lightning error handling | `AuraHandledExceptionBuilder.buildClientMessage(ex)` |
| Store integration config | `Webservice_Setting__mdt` (paths/timeouts) + Named Credentials (auth) |
| Store Slack channel IDs | `Slack_Channel__mdt` |
| Configure batch scope | `Batch_Class_Scope_Size__mdt` |

---

## 1. Logging

### Logr (Fluent Builder) — `Logr.cls`

All logging goes to `TruckinLog__c` (auto-numbered `TL-{0000}`).

```apex
// Exception logging
new Logr()
    .setSubject('MyClassName')
    .setCategory('Sonos Pro')
    .setTriggerInfo('AccountTrigger.after update')
    .setRecords(recordId)
    .addException(ex)
    .save();

// Informational logging
Logr logger = new Logr();
logger.add('Step 1: Fetched records')
      .add('Step 2: Processed 50 items')
      .setSubject('BatchProcessor')
      .save();

// Reuse with reset
logger.reset();
logger.add('Next batch started').save();
```

| Method | Returns | Purpose |
|--------|---------|---------|
| `add(Object)` | `Logr` | Append entry to log body |
| `setSubject(String)` | `Logr` | Source class/component name |
| `setCategory(String)` | `Logr` | Category picklist value |
| `setTriggerInfo(String)` | `Logr` | Context info (class.method) |
| `setRecords(String)` | `Logr` | Related record IDs (auto-truncates to 100 chars) |
| `addException(Exception)` | `Logr` | Sets IsException, StackTrace, formatted message |
| `save()` | `Logr` | Inserts `TruckinLog__c` record |
| `reset()` | `Logr` | Clears state for reuse |

**Category picklist values:** `Sonos Pro`, `Sonos Radio`, `Other`, `Partners`, `CloudCraze`, `Sonos B2B Store`, `User Persona`

### TruckinLogFactory (Structured Logs) — `TruckinLogFactory.cls`

Builds **unsaved** `TruckinLog__c` records with auto-generated headers. **Caller must `insert`.**

```apex
// Exception with SObject context
TruckinLogFactory factory = new TruckinLogFactory('PaymentProcessor');
TruckinLog__c log = factory.create(paymentRecord, 'processRefund', ex);
insert log;

// Database.Error handling
TruckinLog__c log = factory.create(record, 'upsertAccounts', saveResult.getErrors());
insert log;

// Static helper (no factory instance needed)
TruckinLog__c log = TruckinLogFactory.create('MyClass', 'Error message', recordId, true, 'MyClass.myMethod');
insert log;
```

Auto-header SObject support: `SalesAccount__c`, `Payment`, `SonosInvoicePayment__c`, `ServiceContract`, `SonosInvoice__c`, `CardPaymentMethod`, `Event`. Extend `LOG_FIELDS_PER_SOBJECT_TYPE` map to add new types.

### Log Cleanup

`TruckinLogCleanUpBatch` — deletes logs older than configurable days (default: 100).

---

## 2. Feature Flags

### Feature_Manager__mdt

| Field | Type | Purpose |
|-------|------|---------|
| `isActive__c` | Checkbox (default: `false`) | Feature on/off toggle |

```apex
// Preferred: via selector
FeatureManagerSelector selector = new FeatureManagerSelector();
Boolean isEnabled = selector.getFeatureByDeveloperName('SplitOrder');

// Alternative: direct getInstance
Feature_Manager__mdt feature = Feature_Manager__mdt.getInstance('ChatAvailability');
Boolean isActive = feature != null && feature.isActive__c;

// Alternative: via ApexUtilities
Boolean isActive = ApexUtilities.getFeatureStatus('NirvanaDiagnostics');
```

### Portal Feature Toggles

| Metadata Type | Accessor |
|---------------|----------|
| `Dealer_Portal_Feature_Toggle__mdt` | `PortalCustomMetadataSelector.getDealerPortalFeatureToggle(type)` |
| `DevPortalFeatureToggle__mdt` | `PortalCustomMetadataSelector.getFeatureToggle(type)` |
| `DevPortalControlToggle__mdt` | `PortalCustomMetadataSelector.getControlFeatureToggle()` |

---

## 3. Integration & Callouts

### Standard Pattern: Webservice_Setting__mdt + Named Credentials

All integrations use `Webservice_Setting__mdt` (119 records) for config + Named Credentials for auth.

| Field | Purpose |
|-------|---------|
| `Named_Credential__c` | Named Credential for authentication |
| `Service_Path__c` | Relative service path (e.g., `/ws/rest/test`) |
| `Timeout__c` | Timeout in ms (default: 10000) |
| `Token_Endpoint__c` | OAuth token endpoint (optional) |
| `Client_Id__c` | OAuth client ID (optional) |
| `Client_Secret__c` | OAuth client secret (optional) |
| `Enable_Debug__c` | Enable debug mode (optional) |

```apex
// Standard callout
Webservice_Setting__mdt service = Webservice_Setting__mdt.getInstance('My_Integration_Name');

HttpRequest req = new HttpRequest();
req.setEndpoint('callout:' + service.Named_Credential__c + service.Service_Path__c);
req.setTimeout((Integer) service.Timeout__c);
req.setMethod('POST');
req.setHeader('Content-Type', 'application/json');
req.setBody(JSON.serialize(payload));

HttpResponse res = new Http().send(req);
```

### Bearer Token Pattern (Okta)

```apex
String token = OktaInternalService.getInternalAccessToken();
req.setHeader('Authorization', 'Bearer ' + token);
```

Uses `AuthProvider` for Okta credentials. Caches tokens in `Cache.Org.getPartition('local.Default')`.

### Callout Tracking & Retry

`REST_Callout_Job__c` tracks HTTP results for audit and retry. `RESTCalloutBatch` retries failed records (scheduled via `RESTCalloutBatchScheduler`).

### Flow-Callable Callouts

```apex
// Generic sync callout for Flows
SynCalloutUtility — @InvocableMethod(label='Send Callout')

// Jira-specific
JiraCalloutService — @InvocableMethod(label='Jira Callout')
```

### Major Integration Groups

| Group | Named Credential | Purpose |
|-------|-----------------|---------|
| Solace (43 records) | `Solace` | Event-driven messaging (OMS, orders, subscriptions) |
| SAP (6 records) | `SAP` | Price/availability, order modifications, documents |
| OMS (7 records) | Various | Order Management System |
| Marketing Cloud (3 records) | Various | SFMC journeys and transactional API |
| Extend (5 records) | `AccountServices` | Extended warranty |
| Jira (2 records) | `Jira` | Issue management |

---

## 4. Trigger Framework

### All triggers MUST extend `TriggerHandler` — `TriggerHandler.cls`

```apex
// Trigger (minimal)
trigger MyObjectTrigger on MyObject__c (before insert, before update, after insert, after update) {
    new MyObjectTriggerHandler().run();
}
```

```apex
// Handler
public with sharing class MyObjectTriggerHandler extends TriggerHandler {

    protected override void runQueries() {
        // bulk-query related data before dispatch
    }

    protected override void beforeInsert() { }
    protected override void afterUpdate() { }
}
```

**Override methods:** `beforeInsert()`, `beforeUpdate()`, `beforeDelete()`, `afterInsert()`, `afterUpdate()`, `afterDelete()`, `afterUndelete()`, `runQueries()`

### TriggerHandler API

| Method | Type | Purpose |
|--------|------|---------|
| `run()` | Instance | Main entry — validates, detects context, dispatches |
| `setMaxLoopCount(Integer)` | Instance | Limit recursion (default: 5 if set) |
| `clearMaxLoopCount()` | Instance | Remove loop limit |
| `bypass(String)` | Static | Skip a handler at runtime |
| `clearBypass(String)` | Static | Re-enable a bypassed handler |
| `isBypassed(String)` | Static | Check bypass status |
| `clearAllBypasses()` | Static | Clear all bypasses |

### Global Trigger Control

`TriggerControl__c` (Hierarchy Custom Setting) — `IsEnabled__c` checkbox. When `false`, ALL triggers are disabled. `TriggerHandler.validateRun()` checks this automatically.

### Bypassing in Async Code

```apex
TriggerHandler.bypass('ContactTriggerHandler_v2');
update contacts;
TriggerHandler.clearBypass('ContactTriggerHandler_v2');
```

---

## 5. Service Layer & Dependency Injection

### ServiceFactory + DI — `ServiceFactory.cls`, `DI.cls`

```apex
// Singleton service pattern
public with sharing class MyService {
    private static MyService instance;

    public static MyService getInstance() {
        if (instance == null) {
            instance = (MyService) ServiceFactory.get(MyService.class);
        }
        return instance;
    }

    public virtual MyResult doSomething(Id recordId) {
        // business logic — methods must be virtual for DI mocking
    }
}
```

**How DI works:**
- `ServiceFactory.get(Type)` returns a cached singleton
- `DI.inject(Type, instance)` returns real instance in production, mock in tests
- `DI.mock(MyService.class)` creates a `StubProvider`-based mock

### Mocking in Tests

```apex
@IsTest
static void testMyService() {
    DI.Mock mock = DI.mock(MyService.class);
    mock.startStubbing();
    mock.when(((MyService) mock.stub).doSomething(null))
        .thenReturn(expectedResult);
    mock.stopStubbing();

    MyService service = MyService.getInstance(); // returns mock
}
```

### Sharing Bypass

`WithoutSharing.cls` — use when a `with sharing` service needs one elevated operation:

```apex
SObject result = WithoutSharing.fetchOne(myQuery);
WithoutSharing.doUpdate(records);
```

---


## 8. Error Handling

### TruckinException (Auto-Logging) — `TruckinException.cls`

Extends `Exception`. Logs automatically **once per API request** to `TruckinLog__c`.

```apex
throw TruckinException.createAndLog(
    'Payment processing failed',           // message
    'PaymentId: ' + paymentId,             // context
    'PaymentService',                       // subject
    'PaymentService.processRefund',         // triggerInfo
    'Sonos Pro'                             // category
);
```

- Captures `RestContext.request` details if in REST context
- Fails silently on logging errors (won't break calling code)

### AuraHandledExceptionBuilder — `AuraHandledExceptionBuilder.cls`

For Lightning/Aura components:

```apex
try {
    // operation
} catch (Exception ex) {
    String clientMessage = AuraHandledExceptionBuilder.buildClientMessage(ex);
    throw new AuraHandledException(clientMessage);
}
```

### Domain-Specific Exceptions

Follow naming `{Integration}Exception extends Exception`:
- `SapCalloutException`
- `JiraCalloutServiceException`
- `VoiceCalloutException`
- `ExtendCalloutServiceException`

---

## 9. Test Utilities

### TestUtilities (Primary Factory) — `TestUtilities.cls`

Pattern: `create{Type}(Map<String, Object> fields, Boolean doInsert)`

```apex
Account acc = (Account) TestUtilities.createAccount(
    new Map<String, Object>{ 'Name' => 'Test Corp', 'Industry' => 'Technology' },
    true  // insert
);

Contact con = (Contact) TestUtilities.createContact(
    new Map<String, Object>{ 'AccountId' => acc.Id, 'Email' => 'test@test.com' },
    false  // don't insert
);
```

**Available methods:** `createUser`, `createAccount`, `createContact`, `createOrder`, `createProduct`, `createPricebookEntry`, `createPriceBookEntriesBulk`, `createCase`, `createShipment`, `createAsset`, `createSocialPost`, `createVoiceCall`, `createBillingAccount`, `createSubscription`

### trac_TestUtils (Default-Based Factory) — `trac_TestUtils.cls`

```apex
Account acc = (Account) trac_TestUtils.createSObject(new Account(), true);
List<Contact> contacts = trac_TestUtils.createSObjectList(new Contact(), 10, true);
Id fakeId = trac_TestUtils.newId(Account.SObjectType);
```

### TestUtils (Fake ID Generator) — `TestUtils.cls`

```apex
Id fakeAccountId = TestUtils.generateFakeId(Account.SObjectType);
TestUtils.generateFakeId(listOfRecords); // assigns fake IDs to a list
```

### HTTP Callout Mocks

```apex
// Simple mock
Test.setMock(HttpCalloutMock.class, new PortalHttpMock(200, '{"status":"ok"}'));

// Multi-endpoint mock
Map<String, HttpCalloutMock> mocks = new Map<String, HttpCalloutMock>{
    'callout:Solace/events' => new PortalHttpMock(200, '{}'),
    'callout:SAP/orders' => new PortalHttpMock(200, '{"orders":[]}')
};
Test.setMock(HttpCalloutMock.class, new MultiRequestMock(mocks));
```

---

## 10. Async Patterns

### ChainableBatch — `ChainableBatch.cls`

Extend instead of `Database.Batchable` when chaining batches:

```apex
public class MyBatch extends ChainableBatch {
    public Database.QueryLocator start(Database.BatchableContext ctx) { ... }
    public void execute(Database.BatchableContext ctx, List<SObject> scope) { ... }
    // finish() auto-chains to next batch
}

ChainableBatch.create(new FirstBatch(), 200)
    .chain(new SecondBatch(), 100)
    .chain(new ThirdBatch())
    .run();
```

### Queueable + Finalizer

```apex
public class MyCalloutQueueable implements Queueable, Database.AllowsCallouts {
    public void execute(QueueableContext context) {
        // perform callout
        System.attachFinalizer(new SonosTransactionFinalizerUtility());
    }
}
```

`SonosTransactionFinalizerUtility` logs unhandled exceptions from Queueable jobs.

### Batch Scope Config

`Batch_Class_Scope_Size__mdt` — configure batch scope sizes per class via custom metadata.

---

## 11. Utility Classes

| Class | Purpose | Key Methods |
|-------|---------|-------------|
| `Optional` | Null-safe defaults | `Optional.of(value, default)` for String, Date, Datetime, Decimal, Integer, Boolean |
| `CollectionUtils` | Collection operations | `intersect()`, `remove()`, `slice()`, `splice()`, `isEmpty()`, `notEmpty()`, `convertToIds()`, `joinTrimmed()` |
| `ApexUtilities` | General utilities | `getPickValues()`, `getFeatureStatus()`, `PostToOperationalManagersChatterGroup()` |
| `WithoutSharing` | Elevated DML/queries | `fetchOne(Query)`, `doUpdate(List<SObject>)` |
| `AppConstants` | Global constants | `MDT_SUFFIX`, `REBATE_PRODUCT_TYPE`, `ERROR_UNAUTHORIZED_ENDPOINT` |

### Domain-Specific Constants

| Class | Purpose |
|-------|---------|
| `SNSPRO_Lead_Constants` | Sonos Pro lead constants |
| `SNSPRO_Opportunity_Constants` | Sonos Pro opportunity constants |
| `SNS_IN_Constants` | Sonos India constants |
| `trac_Constants` | General Traction constants |

---

## 12. Custom Metadata & Settings Reference

### Configuration Metadata

| Type | Purpose | Access |
|------|---------|--------|
| `Feature_Manager__mdt` | Feature flags | `FeatureManagerSelector` or `getInstance()` |
| `Webservice_Setting__mdt` | Integration endpoint config (119 records) | `getInstance('DeveloperName')` |
| `SAP_Configuration__mdt` | SAP-specific settings | `SapCalloutService.fetchConfig()` |
| `Batch_Class_Scope_Size__mdt` | Batch scope sizes | `getInstance()` |
| `Slack_Channel__mdt` | Slack channel IDs | `getInstance()` |
| `Mock_API_Partners__mdt` | Mock API responses | Used by `SapCalloutService` |
| `Region_Setting__mdt` | Region-specific settings | `getInstance()` |
| `SFMC_BusinessUnit__mdt` | Marketing Cloud BU MIDs | `getInstance()` |

### Custom Settings

| Setting | Type | Purpose |
|---------|------|---------|
| `TriggerControl__c` | Hierarchy | Global trigger on/off (`IsEnabled__c`) |
| `NirvanaSettings__c` | — | Nirvana feature config (`MaxLoggerSize__c`) |

### Named Credentials (Major)

| Named Credential | Auth Type | Purpose |
|-----------------|-----------|---------|
| `Solace` | Password | Event messaging |
| `SAP` | Password | SAP ERP |
| `Boomi_Sonos_Inc` | Password | Boomi platform |
| `AccountServices` | External Credential (Okta) | Account/subscription services |
| `Jira` | External Credential (Bearer) | Jira issues |
| `SMAPI` | External Credential | Sonos API |
| `GoogleNamedCred` | OAuth 2.0 | Google Calendar |
| `Zuora` | Custom OAuth | Zuora billing |
| `BrazeCommercial` / `BrazeConsumer` | Token | Braze messaging |
| `LoqateAPI` | API Key | Address validation |
| `Global_E` | — | Returns/refunds |

**Pattern:** Base credentials (URL, username, password) in Named Credentials. Relative paths and runtime config in `Webservice_Setting__mdt`.

---

## 13. Repo Naming Conventions

### File Naming

| Type | Convention | Example |
|------|-----------|---------|
| Trigger | `{SObjectName}Trigger` | `AccountTrigger.trigger` |
| Trigger Handler | `{SObjectName}TriggerHandler` | `AccountTriggerHandler.cls` |
| Service | `{Domain}Service` | `AccountService.cls`, `B2B_OrderService.cls` |
| Selector | `{Domain}Selector` | `FeatureManagerSelector.cls` |
| Callout Service | `{Integration}CalloutService` | `SapCalloutService.cls` |
| Queueable | `{Purpose}Queueable` | `SolaceCalloutQueueable.cls` |
| Batch | `{Purpose}Batch` | `RESTCalloutBatch.cls` |
| Test Class | `{ClassName}_Test` or `{ClassName}Test` | `Logr_Test.cls` |
| HTTP Mock | `{Purpose}Mock` | `PortalHttpMock.cls` |
| Constants | `{Domain}_Constants` or `AppConstants` | `SNSPRO_Lead_Constants.cls` |
| Exception | `{Domain}Exception` | `TruckinException.cls` |

### Domain Prefixes

| Prefix | Domain |
|--------|--------|
| `B2B_` | B2B Commerce |
| `CC_` | CloudCraze / Commerce |
| `SNSPRO_` | Sonos Pro |
| `SNS_IN_` | Sonos India |
| `NF_` | New Feature (Voice/telephony) |
| `trac_` | Traction (CRM framework utilities) |
| `OMS_` | Order Management System |

### Class Header Convention

```apex
/**
 * Copyright (c) {year} Sonos, Inc. All Rights Reserved.
 * Subject to Sonos, Inc. licensing.
 *
 * @author {name}/Sonos
 * @version 1.0
 * @description
 *
 * PURPOSE
 *
 *    {description}
 *
 * TEST CLASS
 *
 *    {TestClassName}
 *
 * CHANGE LOG
 *
 *    [Version; Date; Author; Description]
 *    v1.0; {date}; {author}; Initial Build
 *
 **/
```
