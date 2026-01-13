## 2024-10-24 - Misleading "Optional" Fields
**Learning:** Text placeholders like "(Optional)" or "Leave empty if none" are deceptive if the underlying form field is technically required (default behavior for `TextInput`). This frustrates users who follow instructions but get blocked by the interface.
**Action:** Always explicitly set `required=False` in the code when the UI text suggests an optional field.
