---
name: sf-flow
description: >
  Creates and validates Salesforce Flows with 110-point scoring.
  TRIGGER when: user builds or edits record-triggered, screen, autolaunched, or
  scheduled flows, or touches .flow-meta.xml files.
  DO NOT TRIGGER when: Apex automation (use sf-apex), process builder migration
  questions only, or non-Flow declarative config (use sf-metadata).
license: MIT
metadata:
  version: "2.1.0"
  author: "Jag Valaiyapathy"
  scoring: "110 points across 6 categories"
---

# sf-flow: Salesforce Flow Creation and Validation

Expert Salesforce Flow Builder with deep knowledge of best practices, bulkification, and Spring '26 (API 66.0) metadata. Create production-ready, performant, secure, and maintainable flows.

## Quick Reference: Validation Script

```bash
python3 ~/.claude/plugins/marketplaces/sf-skills/sf-flow/hooks/scripts/validate_flow.py <flow-file.xml>
```

**Scoring**: 110 points across 6 categories. Minimum 88 (80%) for deployment.

---

## Core Responsibilities

1. **Flow Generation**: Create well-structured Flow metadata XML from requirements
2. **Strict Validation**: Enforce best practices with comprehensive checks and scoring
3. **Safe Deployment**: Integrate with sf-deploy skill for two-step validation and deployment
4. **Testing Guidance**: Provide type-specific testing checklists and verification steps

---

## CRITICAL: Orchestration Order

**sf-metadata → sf-flow → sf-deploy → sf-data** (you are here: sf-flow)

Flow references custom object/fields? Create with sf-metadata FIRST. Deploy objects BEFORE flows. See `references/orchestration.md` for extended patterns including Agentforce.

---

## Key Insights

| Insight | Details |
|---------|---------|
| **Before vs After Save** | Before-Save updates avoid a second DML — changes are committed in memory with the triggering record. This is the most performant pattern for same-record updates. After-Save: related records, emails, callouts |
| **Test with 251** | Batch boundary at 200. Test 251+ records for governor limits, N+1 patterns, bulk safety |
| **$Record context** | Single-record, NOT a collection. Platform handles batching. Never loop over $Record |
| **Transform vs Loop** | Transform: data mapping/shaping (30-50% faster). Loop: per-record decisions, counters, varying logic. See `references/transform-vs-loop-guide.md` |

**Automation Density**: For Low density objects (0-2 automations), Flow is the official recommendation. Use **Flow Trigger Explorer** (Setup → Process Automation) to audit existing automations before adding new ones. See [sf-apex/references/automation-density-guide.md](../sf-apex/references/automation-density-guide.md) for the full framework.

---

## Form Building

| Need | Tool | Notes |
|------|------|-------|
| Simple record field visibility | **Dynamic Forms** | No code, Lightning App Builder config |
| Guided wizard / multi-step | **Screen Flow** | Declarative, admin-buildable |
| Complex custom UI in Flow | **Screen Flow + LWC** | Hybrid — Flow orchestrates, LWC renders |

> ⚠️ **Screens break transactions**: Each screen element commits prior DML. Collect all input first, then perform DML after the final screen. Use the Roll Back Records element for multi-step forms.

**Scheduled Flow > Apex Schedulable** for most scheduling needs. Scheduled Flows are deployable metadata, packageable, and don't count against the 100 Apex scheduled job limit.

**See**: [references/form-building-guide.md](references/form-building-guide.md) for the 5-tool comparison, decision tree, security warnings, and OmniStudio considerations

---

## Workflow Design (5-Phase Pattern)

### Phase 1: Requirements Gathering

**Before building, evaluate alternatives**: See `references/flow-best-practices.md` Section 1 — sometimes a Formula Field, Validation Rule, or Roll-Up Summary is the better choice.

**Ask the user** to gather: flow type, primary purpose, trigger object/conditions, target org alias.

**Then**: Check existing flows (`Glob: **/*.flow-meta.xml`), offer reusable subflows from `references/subflow-library.md`, reference `references/governance-checklist.md` for complex automation.

### Phase 2: Flow Design & Template Selection

| Flow Type | Template File | Naming Prefix |
|-----------|---------------|---------------|
| Screen | `screen-flow-template.xml` | `Screen_` |
| Record-Triggered (After) | `record-triggered-*.xml` | `Auto_` |
| Record-Triggered (Before) | `record-triggered-*.xml` | `Before_` |
| Scheduled | `scheduled-flow-template.xml` | `Sched_` |
| Platform Event | `platform-event-flow-template.xml` | `Event_` |
| Autolaunched | `autolaunched-flow-template.xml` | `Sub_` or `Util_` |

**Element Pattern Templates** in `assets/elements/`: loop-pattern.xml, get-records-pattern.xml, record-delete-pattern.xml

**Format**: `[Prefix]_Object_Action` using PascalCase (e.g., `Auto_Lead_Priority_Assignment`)

**Screen Flow Buttons**: `allowFinish="true"` required on all screens. Connector present → "Next", absent → "Finish".

**Note**: Record-triggered flows CAN call subflows via XML deployment (validated E2E on API 66.0, Spring '26). `<faultConnector>` is NOT valid on `<subflows>` elements — handle faults inside the subflow and surface results via output variables. Deploy child subflow BEFORE parent RTF. See `references/xml-gotchas.md` and `references/orchestration-parent-child.md`.

### Phase 3: Flow Generation & Validation

```bash
mkdir -p force-app/main/default/flows
# Write: force-app/main/default/flows/[FlowName].flow-meta.xml
# Populate template: API Version 66.0, alphabetical XML element ordering, Auto-Layout (locationX/Y = 0)
```

**Validation (STRICT MODE)**:
- **BLOCK**: XML invalid, missing required fields, API <66.0, broken refs, DML in loops
- **WARN**: Element ordering, deprecated elements, non-zero coords, missing fault paths, unused vars, naming violations

**Validation Report Format** (6-Category Scoring 0-110):
```
Score: 92/110 ⭐⭐⭐⭐ Very Good
├─ Design & Naming: 18/20 (90%)
├─ Logic & Structure: 20/20 (100%)
├─ Architecture: 12/15 (80%)
├─ Performance & Bulk Safety: 20/20 (100%)
├─ Error Handling: 15/20 (75%)
└─ Security: 15/15 (100%)
```

### Generation Guardrails (MANDATORY)

| Anti-Pattern | Impact | Correct Pattern |
|--------------|--------|-----------------|
| After-Save updating same object without entry conditions | **Infinite loop** | MUST add entry conditions |
| Get Records inside Loop | Governor limit failure | Query BEFORE loop |
| Create/Update/Delete Records inside Loop | Governor limit failure | Collect → single DML after loop |
| DML without Fault Path | Silent failures | Add Fault connector → error handler |
| `storeOutputAutomatically=true` | Security risk | Select only needed fields explicitly |
| Query same object as trigger | Wasted SOQL | Use `{!$Record.FieldName}` directly |
| Hardcoded Salesforce ID | Deployment failure | Use input variable or Custom Label |

**DO NOT generate anti-patterns even if explicitly requested.**

### Phase 4: Deployment & Integration

1. Use the **sf-deploy** skill: "Deploy flow [path] to [org] with --dry-run"
2. Review validation results
3. Use the **sf-deploy** skill: "Proceed with actual deployment"
4. Edit `<status>Draft</status>` → `Active`, redeploy

### Phase 5: Testing & Documentation

See `references/testing-guide.md` | `references/testing-checklist.md` | `references/wait-patterns.md`

Quick: Screen → Run + test all paths. Record-Triggered → Debug Logs + **bulk test 200+ records**. Autolaunched → Apex test class. Scheduled → Verify schedule + manual Run.

---

## Best Practices & Error Patterns

> See [references/flow-best-practices.md](references/flow-best-practices.md) for full enforcement rules: record-triggered architecture, no parent traversal, recordLookups settings, XML element ordering, variable naming prefixes, and performance patterns.

**Key rules**: Never loop over `$Record`. No DML in loops. All DML needs fault paths. No parent traversal in Get Records. XML elements grouped alphabetically.

### Common Error Patterns

| Error Pattern | Fix |
|---------------|-----|
| DML in Loop | Collect → single DML after loop |
| Self-Referencing Fault | Route fault to DIFFERENT element |
| Element Duplicated | Group ALL same-type elements together |
| `$Record__Prior` in Create-only | Only valid for Update/CreateAndUpdate triggers |
| "Parent.Field doesn't exist" | Use TWO Get Records (child then parent) |

See `references/xml-gotchas.md` for XML-specific issues.

---

## Integration Patterns

> See [references/integration-patterns.md](references/integration-patterns.md) for LWC-in-Flow XML patterns, Apex @InvocableMethod integration, and documentation links.

> See [references/agentforce-flow-integration.md](references/agentforce-flow-integration.md) for Agentforce variable name matching, output variable naming, formula limitations, and **Action Definition registration** (required for `flow://` targets in Agent Script).

---

## Cross-Skill Integration

| From Skill | To sf-flow | When |
|------------|------------|------|
| sf-ai-agentscript | → sf-flow | "Create Autolaunched Flow for agent action" |
| sf-apex | → sf-flow | "Create Flow wrapper for Apex logic" |
| sf-integration | → sf-flow | "Create HTTP Callout Flow" |

| From sf-flow | To Skill | When |
|--------------|----------|------|
| sf-flow | → sf-metadata | "Describe Invoice__c" (verify fields before flow) |
| sf-flow | → sf-deploy | "Deploy flow with --dry-run" |
| sf-flow | → sf-data | "Create 200 test Accounts" (after deploy) |

## Flow Testing (CLI)

```bash
sf flow run test --tests FlowTest1,FlowTest2 --target-org my-sandbox
sf flow run test --test-level RunAllFlowTests --target-org my-sandbox
sf flow get test --test-run-id <id> --target-org my-sandbox
```

> GA since v2.86.9. For Apex tests, see `/sf-testing`. For unified runner (Beta): `sf logic run test`.

---

## Edge Cases

| Scenario | Solution |
|----------|----------|
| >200 records | Warn limits, suggest scheduled flow |
| >5 branches | Use subflows |
| Cross-object | Check circular deps, test recursion |
| Production | Deploy Draft, activate explicitly |

**Debug**: Flow not visible → deploy report + permissions | Tests fail → Debug Logs + bulk test | Sandbox→Prod fails → FLS + dependencies

---

## Notes

**Dependencies** (optional): sf-deploy, sf-metadata, sf-data | **API**: 66.0 | **Mode**: Strict (warnings block) | Python validators recommended
