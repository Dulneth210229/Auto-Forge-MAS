# UI/UX Design: Item Listing (CRUD)

> Review the attached page screenshots alongside this summary. The screenshots show the literal generated components -- there is no later regeneration step that could introduce drift from what you approve here.

---

## Page: Item Listing

- **Route:** `/items`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-001, FR-006, FR-007, FR-008, FR-009, FR-010, US-004, US-005, US-006, US-008, US-009, AC-001, AC-003, AC-005, AC-007, AC-008
- **States:** idle, loading, error, success

### Components

- **SearchFilterBar** (reused)
  - Covers UI expectations: Live search input with debouncing, plus filter dropdowns for category and price range
- **ItemTable** (reused)
  - Covers UI expectations: A main page showing all items in a list/table/grid layout
- **Pagination** (reused)
  - Covers UI expectations: Pagination controls at the bottom of the list (previous/next, jump to page)

---

## Page: Item Detail

- **Route:** `/items/:id`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-002, US-005, US-006, US-008, US-009, AC-004
- **States:** idle, loading, error, success

### Components

- **ItemDetailCard** (reused)
  - Covers UI expectations: An "Add Item" button that opens a form to create a new item, Each item has "Edit" and "Delete" actions, Editing opens the same form pre-filled with the item's current data

---

## Page: Create Item

- **Route:** `/items/create`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-003, US-005, US-006, US-007, AC-001, AC-002
- **States:** idle, loading, error, success

### Components

- **ItemForm** (reused)
  - Covers UI expectations: An "Add Item" button that opens a form to create a new item, Editing opens the same form pre-filled with the item's current data, Show a loading spinner on the submit button while the form is submitting

---

## Page: Edit Item

- **Route:** `/items/:id/edit`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-004, US-005, US-006, US-008, US-009, AC-004
- **States:** idle, loading, error, success

### Components

- **ItemForm** (reused)
  - Covers UI expectations: Editing opens the same form pre-filled with the item's current data, Show a loading spinner on the submit button while the form is submitting

---

## Page: Delete Item Confirmation

- **Route:** `/items/:id/delete`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-005, US-003, US-005, US-006, US-010, AC-003
- **States:** idle, loading, error, success

### Components

- **DeleteConfirmationDialog** (reused)
  - Covers UI expectations: Deleting shows a confirm dialog before removing the item

---

## Design System Impact

### New components introduced
None -- fully reused existing components.

### New design tokens introduced
None -- fully reused the existing design system.
