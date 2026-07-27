# UI/UX Design: Task Comments

> Review the attached page screenshots alongside this summary. The screenshots show the literal generated components -- there is no later regeneration step that could introduce drift from what you approve here.

---

## Page: Task Comments

- **Route:** `/tasks/:taskId/comments`
- **Actors:** Team Member, Admin
- **Covers requirements:** FR-001, FR-002, FR-003, FR-004, US-001, US-002, AC-001, AC-002, AC-003
- **States:** idle, loading, error, success

### Components

- **CommentInput** (new)
  - Covers UI expectations: A comment input box at the bottom of the task detail view
  - Why new: No existing component matches the specific requirement for a comment input box at the bottom of the task detail view with validation and submission behavior.
- **CommentList** (new)
  - Covers UI expectations: A scrollable list of existing comments, newest last, A delete icon shown only on the current user's own comments
  - Why new: No existing component supports a scrollable list of comments with author name, timestamp, and conditional delete icons based on ownership.

---

## Design System Impact

### New components introduced
- CommentInput
- CommentList

### New design tokens introduced
None -- fully reused the existing design system.
