# UI/UX Design: Item Listing (CRUD)

> Review the attached page screenshots alongside this summary. The screenshots show the literal generated components -- there is no later regeneration step that could introduce drift from what you approve here.

---

## Page: Item Listing

- **Route:** `/items`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-001, FR-006, FR-007, FR-008, FR-009, FR-010, US-004, US-005, US-006, US-008, US-009, AC-005, AC-007, AC-008
- **States:** idle, loading, error, success

### Components

- **ItemTable** (new)
  - Covers UI expectations: A main page showing all items in a list/table/grid layout, Each item has "Edit" and "Delete" actions, Pagination controls at the bottom of the list (previous/next, jump to page), Live search input with debouncing, plus filter dropdowns for category and price range
  - Why new: The existing design system does not have a table component that supports sorting, filtering, and pagination as required by this feature.
- **SearchFilterBar** (new)
  - Covers UI expectations: Live search input with debouncing, plus filter dropdowns for category and price range
  - Why new: No existing component matches the required combination of live search, category filter, and price range filter.
- **Pagination** (reused)
  - Covers UI expectations: Pagination controls at the bottom of the list (previous/next, jump to page)

---

## Page: Item Detail

- **Route:** `/items/:id`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-002, US-005, US-006, US-008
- **States:** idle, loading, error, success

### Components

- **ItemDetailCard** (new)
  - Covers UI expectations: An item's full details are displayed
  - Why new: No existing component displays full item details in a structured card layout.

---

## Page: Item Form

- **Route:** `/items/form`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-003, FR-004, FR-005, US-005, US-006, US-007, US-008, US-010, AC-001, AC-002, AC-003, AC-004
- **States:** idle, loading, error, success

### Components

- **ItemForm** (new)
  - Covers UI expectations: An "Add Item" button that opens a form to create a new item, Editing opens the same form pre-filled with the item's current data, Submitting the create/edit form with a missing name, non-positive price, or negative quantity shows a validation error and does not save
  - Why new: No existing component supports a full CRUD form with validation and submission handling.

---

## Page: Item Delete Confirmation

- **Route:** `/items/:id/delete`
- **Actors:** Admin/Manager
- **Covers requirements:** FR-005, US-003, US-005, US-006, US-010, AC-003
- **States:** idle, loading, error, success

### Components

- **DeleteConfirmationDialog** (new)
  - Covers UI expectations: Deleting shows a confirm dialog before removing the item, Canceling the confirmation leaves the item untouched
  - Why new: No existing component handles confirmation prompts for destructive actions like deletion.

---

## Design System Impact

### New components introduced
- ItemTable
- SearchFilterBar
- ItemDetailCard
- ItemForm
- DeleteConfirmationDialog

### New design tokens introduced
None -- fully reused the existing design system.
