---
name: sf-datacloud-prepare
description: >
  Salesforce Data Cloud Prepare phase.
  TRIGGER when: user creates or manages Data Cloud data streams, DLOs, transforms,
  or Document AI configurations, or asks about ingestion into Data Cloud.
  DO NOT TRIGGER when: the task is connection setup only (use sf-datacloud-connect),
  DMOs and identity resolution (use sf-datacloud-harmonize), or query/search work (use sf-datacloud-retrieve).
license: MIT
compatibility: "Requires an external community sf data360 CLI plugin and a Data Cloud-enabled org"
metadata:
  version: "1.0.0"
  author: "Gnanasekaran Thoppae"
  phase: "Prepare"
---

# sf-datacloud-prepare: Data Cloud Prepare Phase

Use this skill when the user needs **ingestion and lake preparation work**: data streams, Data Lake Objects, transforms, or DocAI-based extraction.

## When This Skill Owns the Task

Use `sf-datacloud-prepare` when the work involves:
- `sf data360 data-stream *`
- `sf data360 dlo *`
- `sf data360 transform *`
- `sf data360 docai *`
- choosing how data should enter Data Cloud

Delegate elsewhere when the user is:
- still creating/testing source connections → [sf-datacloud-connect](../sf-datacloud-connect/SKILL.md)
- mapping to DMOs or designing IR/data graphs → [sf-datacloud-harmonize](../sf-datacloud-harmonize/SKILL.md)
- querying ingested data → [sf-datacloud-retrieve](../sf-datacloud-retrieve/SKILL.md)

---

## Required Context to Gather First

Ask for or infer:
- target org alias
- source connection name
- source object / dataset
- desired stream type
- DLO naming expectations
- whether the user is creating, updating, running, or deleting a stream

---

## Core Operating Rules

- Verify the external plugin runtime before running Data Cloud commands.
- Run the shared readiness classifier before mutating ingestion assets: `node ~/.claude/skills/sf-datacloud/scripts/diagnose-org.mjs -o <org> --phase prepare --json`.
- Prefer inspecting existing streams and DLOs before creating new ingestion assets.
- Suppress linked-plugin warning noise with `2>/dev/null` for normal usage.
- Treat DLO naming and field naming as Data Cloud-specific, not CRM-native.
- Confirm whether each dataset should be treated as `Profile`, `Engagement`, or `Other` before creating the stream.
- Hand off to Harmonize only after ingestion assets are clearly healthy.

---

## Recommended Workflow

### 1. Classify readiness for prepare work
```bash
node ~/.claude/skills/sf-datacloud/scripts/diagnose-org.mjs -o <org> --phase prepare --json
```

### 2. Inspect existing ingestion assets
```bash
sf data360 data-stream list -o <org> 2>/dev/null
sf data360 dlo list -o <org> 2>/dev/null
```

### 3. Confirm the stream category before creation
Use these rules when suggesting categories:

| Category | Use for | Typical requirement |
|---|---|---|
| `Profile` | person/entity records | primary key |
| `Engagement` | time-based events or interactions | primary key + event time field |
| `Other` | reference/configuration/supporting datasets | primary key |

When the source is ambiguous, ask the user explicitly whether the dataset should be treated as `Profile`, `Engagement`, or `Other`.

### 4. Create or inspect streams intentionally
```bash
sf data360 data-stream get -o <org> --name <stream> 2>/dev/null
sf data360 data-stream create-from-object -o <org> --object Contact --connection SalesforceDotCom_Home 2>/dev/null
sf data360 data-stream create -o <org> -f stream.json 2>/dev/null
```

### 5. Check DLO shape
```bash
sf data360 dlo get -o <org> --name Contact_Home__dll 2>/dev/null
```

### 6. Only then move into harmonization
Once the stream and DLO are healthy, hand off to [sf-datacloud-harmonize](../sf-datacloud-harmonize/SKILL.md).

---

## High-Signal Gotchas

- CRM-backed stream behavior is not the same as fully custom connector-framework ingestion.
- Some external database connectors can be created via API while stream creation still requires UI flow or org-specific browser automation. Do not promise a pure CLI stream-creation path for every connector type.
- Stream deletion can also delete the associated DLO unless the delete mode says otherwise.
- DLO field naming differs from CRM field naming.
- Query DLO record counts with Data Cloud SQL instead of assuming list output is sufficient.
- `CdpDataStreams` means the stream module is gated for the current org/user; guide the user to provisioning/permissions review instead of retrying blindly.

---

## Output Format

```text
Prepare task: <stream / dlo / transform / docai>
Source: <connection + object>
Target org: <alias>
Artifacts: <stream names / dlo names / json definitions>
Verification: <passed / partial / blocked>
Next step: <harmonize or retrieve>
```

---

## References

- [README.md](README.md)
- [../sf-datacloud/assets/definitions/data-stream.template.json](../sf-datacloud/assets/definitions/data-stream.template.json)
- [../sf-datacloud/references/plugin-setup.md](../sf-datacloud/references/plugin-setup.md)
- [../sf-datacloud/references/feature-readiness.md](../sf-datacloud/references/feature-readiness.md)
