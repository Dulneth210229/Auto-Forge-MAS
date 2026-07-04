# UI/UX Design: Signup

> Review the attached page screenshots alongside this summary. The screenshots show the literal generated components -- there is no later regeneration step that could introduce drift from what you approve here.

---

## Page: Signup Page

- **Route:** `/signup`
- **Actors:** Customer
- **Covers requirements:** FR-001, FR-002, FR-003, FR-004, FR-005, US-001, AC-001, AC-002, AC-003
- **States:** idle, loading, error, success

### Components

- **SignupForm** (new)
  - Covers UI expectations: Signup form with fields for full name, email, password, and confirm password
  - Why new: No existing component matches the specific form structure required for signup with full name, email, password, and confirm password fields.
- **LoginForm** (reused)
  - Covers UI expectations: Link to the existing login page for users who already have an account

---

## Design System Impact

### New components introduced
- SignupForm

### New design tokens introduced
None -- fully reused the existing design system.
