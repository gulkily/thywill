# Bug Report Writing Guidelines

Based on analysis of existing bug reports in the ThyWill project, this guide provides a standardized format for documenting bugs effectively.

## File Naming Convention
- Use sequential numbering: `1.txt`, `2.txt`, `3.txt`, etc.
- Use `.txt` extension for simple text format
- Place all bug reports in `docs/bug/` directory

## Required Sections

### 1. Title/Summary (First Line)
**Format**: Clear, concise description of the issue
- Focus on what is broken, not why it might be broken
- Use present tense
- Be specific about the affected component/feature

**Examples**:
- ✅ "Archive and Praise menu choices disappear after Prayed button is pressed"
- ✅ "Prayer actions dropdown menu text overflow"
- ❌ "Menu broken" (too vague)
- ❌ "HTMX issue with prayer marks" (focuses on suspected cause, not symptom)

### 2. Steps to Reproduce
**Format**: Numbered list with precise, actionable steps
- Start with step 0 for initial setup/preconditions if needed
- Use specific UI element names (button text, menu names, etc.)
- Include user role/permissions when relevant
- Be detailed enough that someone else can follow exactly

**Template**:
```
Steps to reproduce:

0. [Preconditions - user role, data setup, etc.]
1. [First action]
2. [Second action]
3. [Observe specific element/behavior]
4. [Action that triggers the bug]
5. [Verification step]
```

### 3. Expected vs Actual Behavior
**Format**: Two clear sections showing the contrast
- **Expected**: What should happen
- **Actual**: What actually happens
- Be specific and measurable
- Focus on user-visible behavior

**Template**:
```
Expected:
[Clear description of correct behavior]

Actual:
[Clear description of what actually happens]
```

## Optional Enhancement Sections

### 4. Notes (for additional context)
- Impact on user experience
- Related observations
- Platform-specific behaviors
- Workarounds if available

### 5. Root Cause Analysis (for complex bugs)
- Technical investigation findings
- Code/template references
- HTMX endpoint details
- Template context issues

### 6. Related Issues
- Reference to similar bugs
- Affected components
- Common patterns

### 7. Technical Details
- Specific endpoints involved
- Template files affected
- HTMX targets and responses
- Missing context variables

### 8. Priority and Impact Assessment
- **Priority**: High/Medium/Low
- **Impact**: Description of user/admin workflow disruption
- **Workaround**: Temporary solutions if available

## Quality Standards

### Essential Characteristics
1. **Reproducible**: Anyone can follow the steps and see the issue
2. **Specific**: Uses exact UI text, menu names, button labels
3. **User-focused**: Describes what the user experiences, not internal technical details
4. **Complete**: Includes all necessary context and steps

### Writing Style
- Use present tense for describing current behavior
- Be objective and factual
- Avoid speculation about causes in the main description
- Use bullet points and numbered lists for clarity
- Include technical analysis in separate sections

### Common Mistakes to Avoid
- Starting with suspected technical cause instead of user-visible symptom
- Vague descriptions ("doesn't work", "broken", "weird behavior")
- Missing critical steps or preconditions
- Mixing expected/actual behavior descriptions
- Not specifying user roles or permissions when relevant

## Example Structure

```
[Clear title describing the user-visible issue]

Steps to reproduce:

0. [Setup/preconditions]
1. [Step 1]
2. [Step 2]
3. [Step 3]

Expected:
[What should happen]

Actual:
[What actually happens]

Notes:
- [Additional context]
- [Platform specifics]
- [Impact description]

Technical Details: (optional)
- Endpoint: [API endpoint]
- Template: [affected template]
- Missing Context: [specific variables]

Priority: [High/Medium/Low]
Impact: [Description of disruption]
Workaround: [Temporary solution if available]
```

## Maintenance
- Review and update bug reports as issues are investigated
- Add technical findings to enhance debugging
- Cross-reference related bugs
- Update status when bugs are fixed or become obsolete

This standardized approach ensures bug reports are actionable, complete, and useful for both immediate debugging and long-term project maintenance.