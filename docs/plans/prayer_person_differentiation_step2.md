# Prayer Person Differentiation Feature - Step 2: Development Plan

## Implementation Overview
Implement prayer person differentiation through modular prompt architecture with feature flag control, following existing `PromptCompositionService` patterns.

## Development Stages

### Stage 1: Create Person Differentiation Prompt (~30 minutes)
**Deliverable**: `prompts/prayer_person_differentiation.txt`

**Tasks**:
- Create new prompt file with instructions for detecting collective pronouns
- Include guidance for second-person prayer formatting 
- Maintain consistency with existing prayer quality standards
- Test prompt content for clarity and specificity

**Acceptance Criteria**:
- Prompt clearly distinguishes between "us/our/we" vs "me/my/I" patterns
- Instructions maintain reverent tone and scripture inclusion requirements
- File follows existing prompt file formatting conventions

### Stage 2: Update Environment Configuration (~15 minutes)
**Deliverable**: Updated `.env.example` and documentation

**Tasks**:
- Add `PRAYER_PERSON_DIFFERENTIATION_ENABLED=false` to `.env.example`
- Update CLAUDE.md with new environment variable documentation
- Ensure default disabled state for safe rollout

**Acceptance Criteria**:
- New environment variable documented with clear description
- Default value set to `false` for backward compatibility
- Documentation includes feature explanation

### Stage 3: Extend PromptCompositionService (~45 minutes)
**Deliverable**: Updated `PromptCompositionService` with person differentiation support

**Tasks**:
- Add person differentiation feature flag detection
- Integrate new prompt file into composition logic
- Update validation to include new required file
- Add feature info to composition debugging output

**Files Modified**:
- `app_helpers/services/prompt_composition_service.py`

**Acceptance Criteria**:
- Service reads `PRAYER_PERSON_DIFFERENTIATION_ENABLED` flag correctly
- When enabled, includes person differentiation prompt in composition
- When disabled, behavior identical to current system
- Validation ensures new prompt file exists
- Composition info includes person differentiation status

### Stage 4: Testing Infrastructure (~30 minutes)
**Deliverable**: Test cases for both prayer modes

**Tasks**:
- Create test cases for individual pronoun detection
- Create test cases for collective pronoun detection
- Add tests for feature flag enabled/disabled states
- Test prayer quality consistency

**Files Modified**:
- `tests/unit/test_prayer_helpers.py` or new test file

**Test Scenarios**:
- Individual requests: "help me", "pray for my family", "I need guidance"
- Collective requests: "help us", "bless our community", "we need wisdom"
- Edge cases: mixed pronouns, ambiguous requests
- Feature flag on/off behavior validation

**Acceptance Criteria**:
- Tests cover both individual and collective prayer generation
- Feature flag behavior properly tested
- Prayer quality maintained in both modes
- Edge cases handled appropriately

### Stage 5: Manual Validation (~30 minutes)
**Deliverable**: Validated prayer generation across scenarios

**Tasks**:
- Test with feature flag disabled (current behavior)
- Test with feature flag enabled (new behavior)
- Validate prayer quality and reverence maintained
- Check scripture inclusion in both modes
- Test various pronoun combinations

**Manual Test Cases**:
```
Individual Requests:
- "Please help me with my anxiety"
- "Pray for my sick grandmother"
- "I'm struggling with my job search"

Collective Requests:
- "Help us grow closer as a church family"
- "Bless our community outreach efforts" 
- "Guide us in our decision making"

Mixed/Edge Cases:
- "Help me and my family heal from our loss"
- "We need prayer for my upcoming surgery"
- "Pray that our church helps me find peace"
```

**Acceptance Criteria**:
- Individual requests generate third-person prayers (unchanged)
- Collective requests generate second-person prayers (new)
- All prayers maintain quality, reverence, scripture inclusion
- Edge cases handled gracefully without errors

## Risk Mitigation

### Quality Assurance
- **Before**: Capture sample prayers from current system for comparison
- **During**: Manual testing of diverse prayer requests
- **After**: Quality spot-checks post-deployment

### Rollback Strategy
- **Immediate**: Set `PRAYER_PERSON_DIFFERENTIATION_ENABLED=false`
- **Code Level**: Feature flag provides instant rollback without code changes
- **Validation**: Confirm rollback returns to exact previous behavior

### Performance Monitoring
- Monitor API response times during testing
- Ensure no increase in token usage
- Validate single API call maintained

## Implementation Order
1. **Stage 1**: Create prompt file (foundation)
2. **Stage 2**: Environment setup (configuration)
3. **Stage 3**: Service integration (core logic)
4. **Stage 4**: Test coverage (validation)
5. **Stage 5**: Manual validation (quality assurance)

## Success Metrics
- Feature flag toggles behavior correctly
- Individual prayers unchanged from current system
- Collective prayers use natural second-person format
- No performance regression
- All tests pass
- Prayer quality maintained across both modes

## Post-Implementation
- Deploy with feature flag disabled
- Enable for admin users first
- Gradual rollout based on community feedback
- Monitor prayer generation quality
- Document lessons learned for future prompt modifications