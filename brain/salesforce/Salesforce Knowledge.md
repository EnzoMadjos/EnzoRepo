# Salesforce Knowledge

tags: [salesforce, index, knowledge]

## Loaded knowledge domains (Memory MCP graph)

All Salesforce knowledge is also loaded in the Memory MCP knowledge graph (`Salesforce-Knowledge-Base`). Use `mcp_memory_search_nodes` to query specific topics.

## Topics

- [[fflib Architecture]] — Service/Domain/Selector/UoW layers
- [[Trigger Framework]] — One trigger per object, handler dispatch
- [[Governor Limits]] — Bulkification, limits reference
- [[Apex Testing Standards]] — 90%+ coverage, mocking, test data factory
- [[Apex Security Patterns]] — CRUD/FLS, with sharing, SOQL injection prevention
- [[SOQL Best Practices]] — Selectors only, no SOQL in loops
- [[NebulaLogger]] — Structured logging for Apex/Flow/LWC
- [[LWC Patterns]] — Component architecture, wire service, events
- [[Salesforce Flow Patterns]] — Flow types, invocable Apex, bulkification
- [[Salesforce DevOps Patterns]] — sfdx-hardis, CI/CD, scratch orgs
- [[Salesforce Integration Patterns]] — REST/SOAP/Platform Events/CDC/Salesforce Functions
- [[Salesforce Well-Architected]] — 5 pillars: Security, Reliability, Performance, Scalability, Sustainability

## Key repos reference

| Repo | Purpose |
|---|---|
| apex-enterprise-patterns/fflib-apex-common | Gold standard architecture |
| kevinohara80/sfdc-trigger-framework | Trigger handler pattern |
| mitchspano/trigger-actions-framework | Advanced trigger actions |
| trailheadapps/lwc-recipes | LWC patterns reference |
| trailheadapps/apex-recipes | Apex patterns reference |
| apex-enterprise-patterns/fflib-apex-mocks | Mocking framework |
| amoss/NebulaLogger | Structured logging |
| sfdx-hardis | DevOps + CI/CD Swiss knife |

## Related

- [[SF QA Agent]]
- [[Projects Index]]
