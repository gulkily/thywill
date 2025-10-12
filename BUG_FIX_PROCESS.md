# Bug Fix Process

## Overview
4-step workflow for diagnosing, patching, and validating defects while preserving repo history and documentation fidelity.

## The Process

### Step 0: Bug Intake (Required)
**Goal**: Capture each bug concisely before any code changes.

**Format**: Markdown entry in `docs/bug/` (follow numbering)
**Filename**: `bug_{next_bug_number}_{short_slug}.txt`
- Define `bug_slug = bug_{next_bug_number}_{short_slug}` and reuse this prefix for all related docs (e.g., `bug_8_offline_feed_navigation_step1_diagnosis_plan.md`).
- Summary (1–2 sentences)
- Steps to reproduce
- Expected vs actual behavior
- Impact assessment (user/system)
- Initial technical notes or suspected cause (optional)

**Avoid**: Fixing without a log, vague repro steps, missing expected outcome.

---

### Step 1: Diagnosis Plan
**When Needed**: For any bug beyond trivial typos or copy changes

**Content**: Focused plan in `docs/plans/` describing investigation strategy
**Filename**: `{bug_slug}_step1_diagnosis_plan.md`
- Problem statement
- Known context/logs
- Hypotheses (1–3) with quick validation ideas
- Impacted areas/modules
- Success criteria for diagnosis completion

**Avoid**: Diving into implementation, speculative essays, missing success criteria.

---

### Step 2: Remediation Plan
**Content**: Concrete patch outline with tests and rollout checks

**Format**: `docs/plans/{bug_slug}_step2_remediation_plan.md`
- Root cause summary (once confirmed)
- Proposed fix approach (bullet points)
- Code/infra touchpoints with owners (if applicable)
- Testing matrix (unit/integration/manual) with owners
- Risk assessment + rollback plan

**Avoid**: Huge multi-step rewrites, skipping testing commitments, ignoring dependencies.

---

### Step 3: Implementation & Validation
**Process**: Create bugfix branch (e.g., `bugfix/{bug_slug}`), implement scoped changes, run committed tests

**Requirements**:
- Implement plan in atomic commits (<65 char imperative subject)
- Update docs/config flags impacted by the bug
- Record verification evidence (screens, logs, test output)
- Prepare Step 4 summary document

**Avoid**: Mixing unrelated fixes, skipping tests, committing unresolved TODOs.

---

### Step 4: Resolution Summary
**Content**: Concise wrap-up document in `docs/plans/{bug_slug}_step3_resolution_summary.md`
- Fix overview (what/why)
- Tests run (with results)
- Follow-up tasks or monitoring notes

**Avoid**: Restating git diff, omitting test results, introducing new commitments.

## Key Rules

**Codex Agent**:
- Always log the bug before touching code
- Request approval between steps when collaborating with humans
- Stay within bug scope; flag feature creep immediately
- Keep fixes minimal but complete; prefer guardrails over silent failures

**Repo Maintainer**:
- Review and approve step outputs sequentially
- Provide additional logs or reproduction context early
- Confirm downstream integrations before deployment

## Warning Signs
- Skipping diagnosis plan for non-trivial issues
- Fix plan >1 page or lacking testing strategy
- Implementation without corresponding documentation/test updates

## Workflows

**Simple Bug**: Step 0 → Step 3 (diagnosis/remediation combined) → Step 4

**Complex Bug**: Step 0 → Step 1 → Step 2 → Step 3 → Step 4
