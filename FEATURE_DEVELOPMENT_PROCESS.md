# Feature Development Process

## Overview
3-step process for feature development with optional solution assessment.

## The Process

### Step 0: Solution Assessment (Optional)
**When Needed**: Multiple viable approaches, complex trade-offs, or unclear direction

**Format**: Ultra-concise comparison document (≤1 page) in `docs/plans/`
**Filename**: `{feature_name}_solution_assessment.md`
- Problem statement (1 sentence)
- 2-4 solution options with key pros/cons (bullet points only)
- Clear recommendation with brief reasoning

**Avoid**: Long explanations, implementation details, >4 options, verbose prose

---

### Step 1: Feature Description
**Content**: Problem statement, 3-5 user stories, core requirements, user flow, success criteria

**Format**: Concise document (≤1 page) in `docs/plans/`
**Filename**: `{feature_name}_feature_description.md`
- Problem (1-2 sentences)
- User stories (bullet points: "As [role], I want [goal] so that [benefit]")
- Core requirements (3-5 bullet points)
- Simple user flow (numbered steps)
- Success criteria (measurable outcomes)

**Avoid**: Implementation details, code, database schema, UI mockups, verbose descriptions

---

### Step 2: Development Plan
**Content**: Atomic stages (<2 hours each), dependencies, testing strategy, risk assessment

**Format**: Numbered stages in `docs/plans/` (≤1 page)
**Filename**: `{feature_name}_development_plan.md`
- Each stage: goal, dependencies, changes, testing, risks (bullet points)
- Database changes (conceptual, no SQL)
- Function signatures (no implementation)

**Avoid**: Full code, HTML templates, detailed SQL, verbose explanations

---

### Step 3: Implementation
**Process**: Create feature branch, implement stages in order, test each stage, commit with descriptive messages

**Critical Requirements**:
- **MUST create feature branch first** (e.g., `feature/admin-rights-management`)
- Complete stages atomically (<2 hours each)
- Complete each completed stage to the branch
- Test before proceeding to next stage
- Track progress with TodoWrite

**Completion Criteria**:
- All stages implemented and tested
- Feature accessible through normal UI (not just direct URLs)
- System dependencies resolved (roles, migrations, etc.)
- Documentation updated

## File Naming Convention
Each step MUST be a separate file in `docs/plans/`:
- **Step 0**: `{feature_name}_solution_assessment.md`
- **Step 1**: `{feature_name}_feature_description.md`
- **Step 2**: `{feature_name}_development_plan.md`

## Key Rules

**Claude Code**:
- Suggest Step 0 for complex/multi-solution features  
- Stay in current step, don't jump ahead
- Wait for explicit approval between steps
- ALWAYS create separate files for each step
- ALWAYS create feature branch before Step 3
- Flag scope creep, return to appropriate step

**User**:
- Review and approve explicitly at each step
- Flag issues early (easier to change)
- Resist adding features mid-implementation

## Warning Signs
- **Step 0**: >1 page, >4 options, verbose explanations
- **Step 1**: >1 page, code examples, UI/database details  
- **Step 2**: >1 page, >2 hour stages, complex dependencies
- **Step 3**: No feature branch, skipping stages, changing requirements

## Workflows

**Simple**: Step 1 → Step 2 → Step 3 (feature branch → implement stages → test/commit → complete)

**Complex**: Step 0 (solution assessment) → Step 1 → Step 2 → Step 3