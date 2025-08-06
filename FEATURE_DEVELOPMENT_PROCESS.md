# Feature Development Process

## Overview
3-step process for feature development with optional solution assessment.

## The Process

### Step 0: Solution Assessment (Optional)
**When Needed**: Multiple viable approaches, complex trade-offs, or unclear direction

**Format**: Brief comparison document (2-3 pages max)
- Problem context (2-3 sentences)  
- 2-4 solution options with pros/cons
- Comparison on: complexity, maintainability, performance, UX, risk
- Recommended approach with reasoning

**Avoid**: Implementation details, >4 options, minor variations

---

### Step 1: Feature Description
**Content**: Problem statement, 3-5 user stories, core requirements, user flow, success criteria

**Format**: 1-2 pages in `docs/plans/`
- Problem (2-3 sentences)
- User stories ("As a [role], I want [goal] so that [benefit]")  
- Core requirements (3-7 bullet points)
- Simple user flow description
- Measurable success criteria

**Avoid**: Implementation details, code, database schema, UI mockups

---

### Step 2: Development Plan
**Content**: Atomic stages (<2 hours each), dependencies, testing strategy, risk assessment

**Format**: Numbered stages in `docs/plans/`
- Each stage: goal, dependencies, high-level changes, testing, risks
- Database changes (no SQL)
- Function signatures (no implementation)

**Avoid**: Full code, HTML templates, detailed SQL, extensive examples

---

### Step 3: Implementation
**Process**: Create feature branch, implement stages in order, test each stage, commit with descriptive messages

**Critical Requirements**:
- **MUST create feature branch first** (e.g., `feature/admin-rights-management`)
- Complete stages atomically (<2 hours each)
- Test before proceeding to next stage
- Track progress with TodoWrite

**Completion Criteria**:
- All stages implemented and tested
- Feature accessible through normal UI (not just direct URLs)
- System dependencies resolved (roles, migrations, etc.)
- Documentation updated

## Key Rules

**Claude Code**:
- Suggest Step 0 for complex/multi-solution features  
- Stay in current step, don't jump ahead
- Wait for explicit approval between steps
- ALWAYS create feature branch before Step 3
- Flag scope creep, return to appropriate step

**User**:
- Review and approve explicitly at each step
- Flag issues early (easier to change)
- Resist adding features mid-implementation

## Warning Signs
- **Step 0**: >4 options, implementation details, analysis paralysis
- **Step 1**: >3 pages, code examples, UI/database details  
- **Step 2**: >2 hour stages, complex dependencies, missing tests/risks
- **Step 3**: No feature branch, skipping stages, changing requirements

## Workflows

**Simple**: Step 1 → Step 2 → Step 3 (feature branch → implement stages → test/commit → complete)

**Complex**: Step 0 (solution assessment) → Step 1 → Step 2 → Step 3