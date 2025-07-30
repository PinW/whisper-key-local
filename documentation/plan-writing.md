# Implementation Plans

`/documentation/implementation-plans`: plans for features & improvements

## Purpose

Implementation plans serve as:
- **Step-by-step guides** for complex feature development
- **Progress tracking** with checkboxes and completion notes
- **Documentation** of design decisions and technical approaches
- **Historical records** of how features were implemented

## Plan Format

Each implementation plan should follow this structure:

### Header
```markdown
# [Feature Name] Implementation Plan

**Note: Execute one line-item at a time and confirm with user before proceeding to next**
**Note: Update this document as you go, checking off tasks and taking notes needed for later**
```

### Current State Analysis
Concise bullet lists:
- Document existing functionality
- Identify gaps and issues
- Note what's already working

### Implementation Plan
Break down into numbered steps with:
- Clear, actionable tasks
- Checkboxes for tracking progress (`- [ ]` for pending, `- [x]` for complete)
- Priority indicators where relevant

### Implementation Details
- Code patterns and examples
- Technical specifications
- Architecture decisions

### Files to Modify
- List all files that need changes
- Brief description of what changes each file needs

### Success Criteria
- Define specific, testable outcomes that confirm feature functionality

## Output Format

Create .md file with descriptive name:
- [TIMESTAMP] = bash `date +%Y-%m-%d`
- `documentation/implementation-plans/[TIMESTAMP]-feature-name-implementation.md`
- Example: `2025-01-28-state-management-update.md`

## Example Plans

- `implementation-plans/auto-enter-hotkey-implementation-2025-01-29.md`