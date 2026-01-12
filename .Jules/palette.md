## 2024-05-23 - Discord Modal State Sync
**Learning:** Modals create a new interaction context. To update the *original* message (like a dashboard/sheet) after a modal submission, you must pass the `interaction.message` object to the modal and call `message.edit` on it, as the modal's interaction response (even `edit_original_response`) only affects the modal's ephemeral context.
**Action:** Always pass `message` or `view` with message reference to Modals that need to update parent UI.
