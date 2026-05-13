# Salesforce Knowledge

tags: [salesforce, index, knowledge]

## Primary Knowledge Base

- **Master file**: `brain/salesforce/SALESFORCE_KB.md` — compiled reference (auto-loaded by Copilot)
- **Topic articles**: `brain/salesforce/articles/`
  - [apex.md](articles/apex.md) — Triggers, governor limits, security, fflib, async, testing, SOQL
  - [lwc.md](articles/lwc.md) — Component structure, lifecycle, wire, LDS, communication, testing
  - [flow.md](articles/flow.md) — Flow types, bulkification, invocable Apex, decision guide, limits
  - [revenue-cloud-cml.md](articles/revenue-cloud-cml.md) — RCA/RLM data model, CML syntax, Business APIs
  - [devops.md](articles/devops.md) — SFDX commands, scratch orgs, CI/CD, GitHub Actions, sfdx-hardis
  - [integration.md](articles/integration.md) — REST API, Bulk API, Platform Events, CDC, callouts, Named Credentials

## Topics (Index)

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
- [[Salesforce Integration Patterns]] — REST/SOAP/Platform Events/CDC
- [[Revenue Cloud Advanced]] — RLM data model, CML constraint language, Business APIs
- [[Salesforce Well-Architected]] — 5 pillars: Security, Reliability, Performance, Scalability, Sustainability

## Key Repos Reference

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
| bgaldino/rlm-base-dev | Revenue Cloud data model + skills |
| Avinava/sf-documentation-knowledge | Scraped SF Help docs API v67.0 |
| starch-uk/agent-docs | CML v1.0.0 full reference |

## Related

- [[SF QA Agent]]
- [[Projects Index]]
