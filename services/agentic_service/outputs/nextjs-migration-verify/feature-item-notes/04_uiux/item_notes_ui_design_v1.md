# UI/UX Design: Item Notes

> Review the attached page screenshots alongside this summary. The screenshots show the literal generated components -- there is no later regeneration step that could introduce drift from what you approve here.

---

## Page: Item Notes

- **Route:** `/item-notes`
- **Actors:** Registered User
- **Covers requirements:** FR-001, US-001, AC-001, AC-002, US-002
- **States:** idle, loading, error, success

### Components

- **ItemNotesList** (reused)
  - Covers UI expectations: A section displaying all notes for an item, sorted newest first.
- **NoteInputField** (new)
  - Covers UI expectations: A text input field for adding a note.
  - Why new: no existing component fits

---

## Design System Impact

### New components introduced
- NoteInputField

### New design tokens introduced
None -- fully reused the existing design system.
