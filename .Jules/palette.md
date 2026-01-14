## 2026-01-14 - Active State & Optional Inputs
**Learning:** Users in Discord interactions rely on the "Disabled" button state to understand which tab/view is currently active. Additionally, Discord TextInputs default to `required=True`, which causes friction when placeholder text instructs users they can leave fields empty.
**Action:** Implement "Active Tab" logic by disabling the button for the current view. Verify `required=False` is set for any optional form fields.
