PALETTE'S JOURNAL - CRITICAL LEARNINGS ONLY

## 2024-05-22 - Default Required Behavior in TextInputs
**Learning:** `discord.ui.TextInput` defaults to `required=True`. If a placeholder suggests a field is optional (e.g., "Leave empty if none"), but `required=False` is omitted, the user is blocked from submitting, creating a frustrating "trap".
**Action:** Always explicitly set `required=False` when the UI copy implies optionality.
