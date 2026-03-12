# Validator Test Matrix

> Snapshot generated against the current repository assets using `hooks/scripts/agentscript-syntax-validator.py` after the rule-catalog expansion.
>
> Goal: distinguish **clean examples**, **warning-only templates**, and **intentionally partial snippets** that are expected to fail a full-agent validator.

## Command Used

```bash
python3 - <<'PY'
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path
spec=spec_from_file_location('v','skills/sf-ai-agentscript/hooks/scripts/agentscript-syntax-validator.py')
mod=module_from_spec(spec)
spec.loader.exec_module(mod)
for path in sorted(Path('skills/sf-ai-agentscript/assets').rglob('*.agent')):
    res=mod.AgentScriptValidator(path.read_text(), str(path)).validate()
    print(path, len(res['errors']), len(res['warnings']))
PY
```

## Summary

| Outcome | Count | Notes |
|---|---:|---|
| Clean (`0 blocking / 0 warnings`) | 1 | Fully self-contained example |
| Warning-only (`0 blocking / 1+ warnings`) | 16 | Usually complete templates with demo placeholders, portability notes, or style suggestions |
| Blocking (`1+ blocking`) | 13 | Mostly partial snippets by design; a small number are org-dependent or pattern examples that still need hardening |

## Clean

| File | Notes |
|---|---|
| `assets/agents/hello-world-employee.agent` | Clean pass in current repo/context. |

## Warning-Only Examples / Templates

| File | Dominant rules | Interpretation |
|---|---|---|
| `assets/agents/hello-world.agent` | `ASV-CFG-007` | Complete example; uses demo `default_agent_user`. |
| `assets/agents/multi-topic.agent` | `ASV-CFG-007`, `ASV-RUN-018` | Complete template; placeholders intentionally unresolved. |
| `assets/agents/production-faq.agent` | `ASV-CFG-007`, `ASV-QLT-001` | Valid example with demo user + transition naming suggestions. |
| `assets/agents/simple-qa.agent` | `ASV-CFG-007`, `ASV-QLT-001` | Complete template with unresolved placeholders. |
| `assets/components/escalation-setup.agent` | `ASV-CFG-007`, `ASV-QLT-001` | Complete escalation template; placeholders remain unresolved. |
| `assets/deterministic-routing.agent` | `ASV-CFG-004`, `ASV-CFG-007`, `ASV-QLT-001` | Complete example; nested-`if` issue fixed during validator audit. |
| `assets/flow-action-lookup.agent` | `ASV-CFG-004`, `ASV-CFG-007`, `ASV-QLT-001` | Complete example with demo user/comment and naming suggestions. |
| `assets/hub-and-spoke.agent` | `ASV-CFG-004`, `ASV-CFG-007`, `ASV-QLT-001` | Complete example with demo user/comment and naming suggestions. |
| `assets/minimal-starter.agent` | `ASV-CFG-004`, `ASV-CFG-007`, `ASV-QLT-001` | Minimal starter is structurally valid; warnings are expected template reminders. |
| `assets/patterns/critical-input-collection.agent` | `ASV-RUN-012`, `ASV-RUN-007` | Complete pattern demonstrating planner-hint caveats; warnings are instructional. |
| `assets/patterns/multi-step-workflow.agent` | `ASV-QLT-005` | Complete pattern; warnings reflect post-action check placement suggestions. |
| `assets/patterns/procedural-instructions.agent` | `ASV-RUN-007`, `ASV-QLT-001` | Complete pattern with advisory warnings only. |
| `assets/patterns/prompt-template-action.agent` | `ASV-RUN-005`, `ASV-RUN-007` | Complete pattern intentionally demonstrates risky prompt output displayability / planner hints. |
| `assets/patterns/system-instruction-overrides.agent` | `ASV-RUN-010`, `ASV-CFG-007`, `ASV-QLT-001` | Complete pattern; lifecycle `run` warnings are expected portability cautions. |
| `assets/prompt-rag-search.agent` | `ASV-CFG-004`, `ASV-CFG-007`, `ASV-QLT-001` | Complete example with demo user/comment and naming suggestions. |
| `assets/verification-gate.agent` | `ASV-CFG-004`, `ASV-CFG-007`, `ASV-RUN-018` | Complete pattern; undefined `refund_amount` bug was fixed during validator audit. |

## Blocking Files

### A. Intentionally Partial Snippets

These are not complete agents and are expected to fail a full-agent validator because they are meant to be embedded into a larger file.

| File | Dominant blockers |
|---|---|
| `assets/components/apex-action.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/components/error-handling.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/components/flow-action.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/components/n-ary-conditions.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/components/topic-with-actions.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/patterns/action-callbacks.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/patterns/advanced-input-bindings.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/patterns/delegation-routing.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/patterns/lifecycle-events.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/patterns/llm-controlled-actions.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-004` |
| `assets/patterns/open-gate-routing.agent` | `ASV-STR-003`, `ASV-CFG-001` |
| `assets/patterns/bidirectional-routing.agent` | `ASV-STR-003`, `ASV-CFG-001`, `ASV-STR-011` |

### B. Context / Org-Dependent Blocking Cases

| File | Dominant blockers | Interpretation |
|---|---|---|
| `assets/escalation-pattern.agent` | `ASV-ORG-007` | Structurally valid, but the referenced outbound route Flows do not exist in the currently resolved org, so the org-aware validator correctly blocks publish readiness. |

## Notes from This Audit

- The validator expansion surfaced **real sample issues** that were worth fixing:
  - `assets/deterministic-routing.agent` was flattened to remove unsupported nested `if` blocks.
  - `assets/verification-gate.agent` now declares `refund_amount` before it is referenced.
  - `assets/components/escalation-setup.agent` no longer uses invalid `set @variables.x = ...` syntax.
- The new `ASV-CFG-007` rule reduces noise on **template/demo values** by reporting them as unresolved placeholders/demo credentials instead of hard org failures.
- The remaining blocking cohort is largely expected because many `assets/components/*` and `assets/patterns/*` files are **partial building blocks**, not standalone publishable agents.

## Recommended Next Step

If you want the entire `assets/` tree to pass as a test suite, split it into two lanes:

1. **standalone agents/templates** — must validate with `0 blocking`
2. **partial snippets** — validate with a snippet-aware harness or a looser parser profile

That separation would let CI enforce publishability for complete examples without falsely failing the reference snippets.
