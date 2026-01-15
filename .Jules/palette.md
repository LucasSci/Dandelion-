## 2024-05-22 - [Nav State Visuals]
**Learning:** In Discord UI Views, disabling the button for the current "tab" or active view is a highly effective way to provide navigation state feedback. It visually grays out the button, preventing redundant clicks and clearly indicating "You are here".
**Action:** Always implement a `_update_buttons(state)` helper in Views with multi-tab navigation to toggle `disabled` states on navigation buttons.
## 2026-01-14 - Active State & Optional Inputs
**Learning:** Users in Discord interactions rely on the "Disabled" button state to understand which tab/view is currently active. Additionally, Discord TextInputs default to `required=True`, which causes friction when placeholder text instructs users they can leave fields empty.
**Action:** Implement "Active Tab" logic by disabling the button for the current view. Verify `required=False` is set for any optional form fields.
## 2024-05-23 - Discord Modal State Sync
**Learning:** Modals create a new interaction context. To update the *original* message (like a dashboard/sheet) after a modal submission, you must pass the `interaction.message` object to the modal and call `message.edit` on it, as the modal's interaction response (even `edit_original_response`) only affects the modal's ephemeral context.
**Action:** Always pass `message` or `view` with message reference to Modals that need to update parent UI.
PALETTE'S JOURNAL - CRITICAL LEARNINGS ONLY

## 2024-05-22 - Default Required Behavior in TextInputs
**Learning:** `discord.ui.TextInput` defaults to `required=True`. If a placeholder suggests a field is optional (e.g., "Leave empty if none"), but `required=False` is omitted, the user is blocked from submitting, creating a frustrating "trap".
**Action:** Always explicitly set `required=False` when the UI copy implies optionality.
