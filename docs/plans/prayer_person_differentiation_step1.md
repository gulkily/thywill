# Prayer Person Differentiation Feature - Step 1: Feature Description

## Overview
Enhance the prayer generation system to intelligently differentiate between individual and collective prayer requests,
creating appropriate prayer formats based on the pronouns used in the original request.

## Problem Statement
Currently, all prayer requests are converted to third-person community prayers where the community prays FOR the
requester. This works well for individual needs ("help me") but feels awkward for collective requests ("help us grow
as a community" becomes "help them grow as a community" instead of the more natural "help us grow as a community").

## User Stories

### Current Behavior (Individual Requests)
- **User Input**: "Please help me with my job interview tomorrow"
- **Current Output**: "Divine Creator, we pray for our friend who faces a job interview tomorrow..."
- **Who Prays**: Community members pray FOR the individual
- **Desired**: Keep this behavior (working correctly)

### Desired New Behavior (Collective Requests)  
- **User Input**: "Please help us grow closer to God as a community"
- **Current Output**: "Divine Creator, we pray for our friends who seek to grow closer to You..."
- **Desired Output**: "Divine Creator, help us grow closer to You as a community..."
- **Who Prays**: Community prays together AS a unified body

### Additional Examples

**Individual/Third-Party (Keep Current)**:
- "Help me find peace" → "...pray for our friend seeking peace..."
- "Pray for my sick mother" → "...pray for our friend's mother who is ill..."
- "My family needs guidance" → "...pray for our friend's family seeking guidance..."

**Collective (New Behavior)**:
- "Help us be more loving" → "Divine Creator, help us be more loving..."
- "Bless our church family" → "Lord, bless our church family..."
- "Guide us in our decisions" → "Heavenly Father, guide us in our decisions..."

## User Experience Goals

1. **Intuitive Prayer Flow**: Prayers should feel natural when spoken by the community
2. **Preserved Reverence**: Maintain the spiritual tone and proper address to the Divine
3. **Seamless Detection**: AI should automatically detect intent without user configuration
4. **Backward Compatibility**: Existing individual prayer patterns remain unchanged

## Technical Requirements

1. **No Preprocessing**: Detection and differentiation should happen within the AI prompt itself, not through separate analysis steps
2. **Single API Call**: Maintain current performance with one call to Anthropic API
3. **Modular Prompt Architecture**: Use existing `PromptCompositionService` pattern with new prompt text file
4. **Feature Flag Control**: Implement `PRAYER_PERSON_DIFFERENTIATION_ENABLED` flag for controlled rollout
5. **Backward Compatibility**: When disabled, behavior remains exactly as current system

## Success Criteria

1. **Accurate Detection**: AI correctly identifies collective vs individual requests
2. **Appropriate Formatting**: 
   - Individual requests → third person community prayers (current)
   - Collective requests → second person community prayers (new)
3. **Maintained Quality**: Prayer quality, reverence, and scripture inclusion unchanged
4. **Performance**: No increase in API response time or token usage

## Out of Scope

- Multi-language support
- User preference settings for prayer style
- Advanced grammatical analysis beyond pronoun detection
- Changes to prayer storage or display logic

## Risk Considerations

1. **Misdetection**: AI might incorrectly categorize some requests
2. **Quality Impact**: New instructions might affect overall prayer quality
3. **User Confusion**: Community might be surprised by different prayer formats
4. **Scripture Integration**: Need to ensure scripture references work in both formats

## Rollout Strategy

### Feature Flag Benefits
- **Safe Testing**: Enable for admin users or subset of community initially
- **A/B Comparison**: Compare prayer quality between old and new approaches
- **Easy Rollback**: Instant disable if issues arise during deployment
- **Gradual Adoption**: Controlled rollout to monitor community response

### Implementation Phases
1. **Development**: Feature flag disabled by default
2. **Internal Testing**: Enable for admin/developer accounts
3. **Beta Testing**: Enable for willing community members
4. **Full Rollout**: Enable for all users after validation
5. **Cleanup**: Remove flag after stable operation (optional)

## Next Steps (Pending Approval)

After approval, Step 2 will detail:
- New `prompts/prayer_person_differentiation.txt` content
- `PromptCompositionService` modifications for feature flag integration
- Environment variable configuration (`PRAYER_PERSON_DIFFERENTIATION_ENABLED`)
- Testing strategy covering both individual and collective prayer scenarios
- Validation approach for prayer quality and accuracy
- Rollback procedures if issues arise