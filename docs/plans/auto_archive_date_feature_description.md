# Auto-Archive Date Feature Description

## Problem Statement
Prayers currently require manual archiving by authors, but many prayers have natural temporal boundaries (events, healing periods, job situations) that could be predicted and automated to improve prayer lifecycle management.

## User Stories
- **As a prayer author**, I want the system to suggest when my prayer might be ready for archiving so I don't forget about completed prayer requests
- **As a prayer author**, I want context-specific archive dates (e.g., surgery dates + recovery time) so my prayers stay relevant for the appropriate duration
- **As a community member**, I want to see prayers that are still current and relevant rather than outdated requests that were never properly archived
- **As an admin**, I want visibility into prayers approaching their suggested archive dates to help maintain community feed quality
- **As a prayer author**, I want the option to override or ignore suggested archive dates when my situation requires longer prayer support

## Core Requirements
- AI analysis during prayer generation determines appropriate archive timeline based on prayer content context
- System stores suggested archive date as metadata without automatic archiving (author retains control)
- UI notifications/prompts when prayers approach suggested archive dates
- Author can accept, postpone, or dismiss archive suggestions
- Archive suggestions respect prayer privacy and avoid assumptions about outcomes

## User Flow
1. User submits prayer request
2. AI generates prayer and analyzes content for temporal context (surgery dates, job interviews, etc.)
3. System calculates suggested archive date and stores it with prayer
4. Prayer displays normally with optional archive date indicator
5. As archive date approaches, author receives gentle prompt to review prayer status
6. Author can archive immediately, postpone suggestion, or dismiss entirely
7. System learns from author decisions to improve future suggestions

## Success Criteria
- 70%+ of prayers with clear temporal boundaries receive appropriate archive date suggestions
- Users engage positively with archive prompts (accept/postpone vs. dismiss)
- Community feeds show improved relevance with less outdated content
- Zero automatic archiving occurs (maintains author control)
- Archive suggestions integrate seamlessly with existing prayer lifecycle management