# Step 1: Salvation Checkbox Feature Description

## User Story
As a user requesting prayer, I want to be able to optionally check a checkbox "I have accepted Jesus Christ as my Lord and Savior" so that the prayer text generated for me reflects my faith status appropriately.

## Business Context
The prayer platform currently generates prayers using a single system prompt that assumes a general Christian audience. However, there's a meaningful distinction between prayers for:
1. **Believers** - Those who have accepted Jesus Christ as their Lord and Savior
2. **Seekers/General** - Those who may be exploring faith, non-believers, or who prefer not to specify

This distinction would allow for more contextually appropriate prayer generation while maintaining the community prayer format.

## Requirements

### Functional Requirements
1. **Optional Checkbox**: Add an optional checkbox to the prayer request form with the text "I have accepted Jesus Christ as my Lord and Savior"
2. **Differential Prayer Generation**: Generate different prayer text based on checkbox state:
   - **Checked (Believer)**: Use enhanced Christian-specific language, assume salvation, focus on growth/discipleship themes
   - **Unchecked (General)**: Use current inclusive approach, may include salvation/evangelistic elements
3. **Prompt Separation**: Extract salvation-specific content from current prompt into separate, modular prompts
4. **Backward Compatibility**: Existing prayer generation behavior should remain unchanged for unchecked state

### Non-Functional Requirements
1. **Persistence**: User's salvation status should be stored in their profile and remembered across sessions
2. **Privacy**: Salvation status should not be displayed to other users (private profile setting)
3. **Performance**: No significant impact on prayer generation speed
4. **Accessibility**: Checkbox must be accessible to screen readers and keyboard navigation
5. **Mobile Responsive**: Checkbox should work well on mobile devices

### User Experience Requirements
1. **Optional by Default**: Checkbox should be unchecked by default for new users (general audience)
2. **Remembered Setting**: Once set, user's choice should be remembered and checkbox pre-checked accordingly
3. **Clear Labeling**: Checkbox text should be clear and theologically appropriate
4. **No Judgment**: UI should not imply one choice is "better" than another
5. **Seamless Integration**: Should fit naturally into existing prayer form workflow

## Technical Considerations

### Current Architecture Analysis
- Prayer generation uses modular prompt composition system in `PromptCompositionService`
- Base prompt is in `prompts/prayer_generation_system.txt`
- System supports feature flags and modular prompt composition (like prayer categorization)
- Prayer form is in `templates/components/prayer_form.html`
- Generation happens in `prayer_helpers.generate_prayer()`
- User model already has fields like `is_supporter`, `supporter_since` for user attributes

### Proposed Architecture Changes
1. **Database Schema**: Add `salvation_status` boolean field to User model (defaults to false)
2. **New Prompt File**: `prompts/salvation_specific_additions.txt` - Additional content for believers
3. **Prompt Composition**: Extend `PromptCompositionService` to conditionally include salvation-specific content
4. **Form Enhancement**: Add checkbox to prayer form that reads/updates user's salvation status
5. **API Enhancement**: Pass user's salvation status to prayer generation service

### Data Flow
1. User loads prayer form - checkbox state reflects their saved `salvation_status` from database
2. User can modify checkbox state which updates their profile immediately or on form submission
3. Prayer generation service receives user's salvation status and composes appropriate prompt
4. If salvation_status is true, additional believer-specific prompt content is included
5. Generated prayer reflects appropriate theological context based on user's saved preference

## Success Criteria
1. **Functional**: Prayers generated for believers include enhanced Christian-specific language
2. **Functional**: Prayers generated for non-believers maintain current inclusive tone
3. **Persistence**: User's salvation status is remembered across sessions
4. **Technical**: No performance degradation in prayer generation
5. **User Experience**: Users can easily understand and use the checkbox
6. **Quality**: Both prayer types maintain high spiritual and literary quality

## Example Prayer Differences

### General Audience (salvation_status = false) - Current Behavior
> "Divine Creator, we lift up our friend who asks for help with job searching. May your will be done in their life and may they find the path you have prepared for them. Guide their steps and open doors of opportunity. Amen."

### Believer Version (salvation_status = true) - With Additional Content
> "Heavenly Father, we lift up our brother/sister in Christ who seeks employment, knowing that you have plans to prosper them and not to harm them (Jeremiah 29:11). Strengthen their faith during this season of waiting and help them trust in your perfect timing as their Provider. May this trial draw them closer to you. Amen."

## Out of Scope
- Different prayer categories based on denomination
- Email notifications or follow-up based on salvation status
- Analytics or reporting on salvation checkbox usage
- Public display of user's salvation status
- Salvation status affecting user roles or permissions

## Risks and Considerations
1. **Theological Sensitivity**: Must ensure both prompt versions are theologically sound
2. **Inclusivity**: General version must remain welcoming to all faith levels
3. **Quality Consistency**: Both versions must maintain same quality standards
4. **Testing**: Need to test both prayer generation paths thoroughly
5. **Community Impact**: Changes should enhance rather than divide community experience

## Next Steps
Upon approval of this feature description, proceed to Step 2: Development Plan which will break down implementation into atomic stages of less than 2 hours each.