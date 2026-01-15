## 2024-05-23 - Discord View Navigation Pattern
**Learning:** Using `disabled=True` alone for active tabs can be visually ambiguous if the button style doesn't change.
**Action:** For tabbed navigation, set the active button to `ButtonStyle.primary` + `disabled=True`, and inactive buttons to `ButtonStyle.secondary` + `disabled=False`. Use `ButtonStyle.success` for positive actions (create/add) to separate them from navigation.
