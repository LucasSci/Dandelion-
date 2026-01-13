## 2024-05-22 - [Nav State Visuals]
**Learning:** In Discord UI Views, disabling the button for the current "tab" or active view is a highly effective way to provide navigation state feedback. It visually grays out the button, preventing redundant clicks and clearly indicating "You are here".
**Action:** Always implement a `_update_buttons(state)` helper in Views with multi-tab navigation to toggle `disabled` states on navigation buttons.
