# Feature Development Collaboration Process

## Overview
A structured 3-step process for collaborating on new feature development, ensuring clear communication and preventing scope creep.

## The 3-Step Process

### Step 1: Feature Description
**Goal**: Create a concise, high-level overview for initial review

**Format**: Brief document (1-2 pages max)
**Content Should Include**:
- **Problem Statement**: What problem does this solve?
- **User Stories**: 3-5 stories in "As a [role], I want [goal] so that [benefit]" format
- **Core Requirements**: 3-7 bullet points of key functionality
- **User Flow**: Simple description of how users interact with the feature
- **Success Criteria**: How do we know it's working?
- **Constraints**: Any limitations or requirements to consider

**What to AVOID**:
- Implementation details
- Code snippets (except minimal examples for clarity)
- Database schema specifics
- UI mockups (unless essential for understanding)

**Example Structure**:
```markdown
# Feature: [Name]
## Problem
[2-3 sentences describing the issue]

## User Stories
- As an [admin], I want [capability] so that [benefit]
- As a [community member], I want [capability] so that [benefit]
- As a [user], I want [capability] so that [benefit]

## Core Requirements
1. [Requirement 1]
2. [Requirement 2]
...

## User Flow
[Simple paragraph describing user interaction]

## Success Criteria
- [Measurable outcome 1]
- [Measurable outcome 2]
```

**Approval Gate**: User reviews and approves concept before proceeding

This file should be added to docs/plans/ directory and committed to master before proceeding with Step 2.

---

### Step 2: Development Plan
**Goal**: Create atomic implementation steps with minimal code

**Format**: Structured plan with numbered stages
**Content Should Include**:
- **Atomic Stages**: Each stage should be implementable in <2 hours
- **Dependencies**: What must be done before each stage
- **Database Changes**: High-level schema modifications (no SQL)
- **Key Functions**: Function signatures and purposes (no implementation)
- **Testing Strategy**: What needs to be tested at each stage
- **Risk Assessment**: What could go wrong and mitigation

**What to AVOID**:
- Full code implementations
- Complete HTML templates
- Detailed SQL migrations
- Extensive code examples

**Example Structure**:
```markdown
# Development Plan: [Feature Name]

## Stage 1: Database Foundation
**Goal**: [What this stage accomplishes]
**Dependencies**: None
**Changes**: Add X table with Y fields
**Testing**: Unit tests for model creation
**Risk**: [Potential issue and mitigation]

## Stage 2: Backend Service
**Goal**: [What this stage accomplishes]  
**Dependencies**: Stage 1 complete
**Changes**: Create XService with methods: create(), validate(), process()
**Testing**: Service unit tests
**Risk**: [Potential issue and mitigation]

[Continue for each stage...]
```

**Approval Gate**: User reviews plan structure and stages before implementation

This file should be added to docs/plans/ directory and committed to master before proceeding with Step 3.

---

### Step 3: Implementation
**Goal**: Execute the development plan systematically

**Process**:
1. **Follow the Plan**: Implement each stage in order
2. **Stage Completion**: Mark each stage complete before moving to next
3. **Test as You Go**: Run tests after each stage
4. **Document Deviations**: If plan changes, note why and update plan
5. **Regular Check-ins**: Confirm direction at key milestones

**Implementation Guidelines**:
- Start a new branch for implementing the feature
- Complete one atomic stage at a time
- Commit to the branch after each stage
- Test functionality before proceeding
- Update TodoWrite with progress
- Flag any issues that require plan changes
- Maintain code quality standards throughout
- Do not stop or restart the server; Pause to let the collaborator do it

**Completion Criteria**:
- All stages implemented and tested
- Success criteria from Step 1 met
- Documentation updated (CLAUDE.md, etc.)
- Ready for user acceptance testing

---

## Communication Rules

### For Claude Code:
- **Stay in Step**: Don't jump ahead to implementation details in Step 1
- **Ask for Approval**: Wait for explicit approval before proceeding to next step
- **Flag Scope Creep**: If requirements expand, return to appropriate step
- **Be Atomic**: Each stage should be small and focused
- **Document Everything**: Keep plans and implementation synchronized

### For User:
- **Review Thoroughly**: Each step builds on the previous
- **Approve Explicitly**: Clear approval before Claude proceeds
- **Flag Issues Early**: Easier to change in earlier steps
- **Stay Focused**: Resist adding features mid-implementation

## Warning Signs Process Is Going Off-Rails

### Step 1 Issues:
- Document is >3 pages
- Contains code implementations
- Gets into UI design details
- Includes database schema SQL

### Step 2 Issues:
- Stages take >2 hours to implement
- Dependencies are complex/circular
- Plan lacks testing strategy
- Risk assessment is missing

### Step 3 Issues:
- Implementing features not in plan
- Skipping stages or testing
- Requirements changing during implementation
- Plan and implementation diverging

## Recovery Process
If process goes off-rails:
1. **Stop Current Work**: Don't continue implementation
2. **Identify Step**: Which step are we actually in?
3. **Return to Appropriate Step**: Go back to where the process broke
4. **Revise Documents**: Update plans to match current understanding
5. **Get Approval**: Re-sync with user before proceeding

## Example Workflow

```
User: "I want feature X"
↓
Claude: Creates Step 1 document
↓
User: Reviews and approves concept
↓
Claude: Creates Step 2 development plan
↓
User: Reviews plan structure and stages
↓
Claude: Implements Stage 1, tests, marks complete
↓
Claude: Implements Stage 2, tests, marks complete
↓
[Continue until all stages complete]
↓
Claude: Feature complete, documentation updated
```

## Success Metrics
- **Clear Expectations**: Both parties understand what's being built
- **No Scope Creep**: Implementation matches original concept
- **Atomic Progress**: Each stage delivers working functionality
- **Quality Results**: Feature works as intended with proper testing
- **Maintainable Code**: Implementation follows project patterns

This process ensures we build the right thing, build it well, and avoid the frustration of scope creep and miscommunication.