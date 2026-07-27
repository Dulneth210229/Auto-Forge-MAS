# UI/UX Design: Login

> Review the attached page screenshots alongside this summary. The screenshots show the literal generated components -- there is no later regeneration step that could introduce drift from what you approve here.

---

## Page: Login Page

- **Route:** `/login`
- **Actors:** Customer, Admin
- **Covers requirements:** FR-001, FR-002, FR-003, FR-004, US-001, US-002, AC-001, AC-002, AC-003
- **States:** idle, loading, error, success

### Components

- **LoginForm** (new)
  - Covers UI expectations: Login Form, Forgot Password Link
  - Why new: Custom form required to handle login-specific validation and submission logic not covered by existing components.

---

## Design System Impact

### New components introduced
- LoginForm

### New design tokens introduced
None -- fully reused the existing design system.
