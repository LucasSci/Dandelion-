## 2024-05-23 - Discord View Navigation Pattern
**Learning:** Using `disabled=True` alone for active tabs can be visually ambiguous if the button style doesn't change.
**Action:** For tabbed navigation, set the active button to `ButtonStyle.primary` + `disabled=True`, and inactive buttons to `ButtonStyle.secondary` + `disabled=False`. Use `ButtonStyle.success` for positive actions (create/add) to separate them from navigation.
# Palette's Journal - Critical Learnings

## 2026-01-17 - Discord Button Layout & Visual Hierarchy
**Learning:** Hardcoding `row` indices on Discord buttons (e.g., `row=1`) strictly limits that row to 5 items and causes crashes if exceeded. Auto-layout (`row=None`) is safer for dynamic lists.
**Action:** Use distinct ButtonStyles and emojis to differentiate interactive (rollable) vs informational elements to improve scannability. Always leave `row=None` for dynamic lists unless specific grid alignment is required.
## 2024-05-22 - Visual Affordance in RPG Interfaces
**Learning:** Players react faster when action types are visually distinct. Using `🎲` for rollable actions and `✨` for passive/utility actions reduces cognitive load compared to reading text labels.
**Action:** Use consistent emoji and color coding across all interactive elements (Buttons, Select Menus) to indicate "Action Type".
## 2024-10-26 - Visual Affordance in Skill Lists
**Learning:** Users can process lists of actions faster when interactive elements (like rollable skills) are visually distinct from informational elements (passive skills).
**Action:** Use distinct emoji (🎲 vs ✨) and button styles (Primary vs Secondary) to differentiate active vs passive capabilities in future UI lists.
# Palette's Journal - Critical UX Learnings

## 2024-05-21 - Visual Affordance for Skill Types
**Learning:** Users can distinguish between active (rollable) and passive (utility) skills faster when visual cues (color + emoji) are used.
**Action:** Use `ButtonStyle.primary` + 🎲 for rollable actions, and `ButtonStyle.secondary` + ✨ for passive/utility actions.

## 2026-01-20 - Destructive Action Confirmation Pattern
**Learning:** Users often click buttons accidentally on mobile. Immediate destruction without confirmation leads to frustration and data loss.
**Action:** Implement `ConfirmarExclusaoView` (or similar confirmation dialog) for all delete/destructive actions. Replace the current view with the confirmation view, offering "Confirm" (Danger) and "Cancel" (Secondary) options.

## 2024-05-24 - Semantic Button Icons
**Learning:** Embedding emojis in button label strings (e.g., "🗑️ Excluir") creates inconsistent rendering and hampers accessibility compared to using the dedicated `emoji` parameter.
**Action:** Always separate the icon into the `emoji` parameter and keep the `label` text clean for better screen reader support and UI consistency.

## 2026-01-20 - Dynamic Status Bar Colors
**Learning:** Fixed-color health bars (always green) fail to convey urgency. Using color-coded emojis based on health percentage improves at-a-glance readability.
**Action:** Use Green (🟩) for >60%, Yellow (🟨) for 31-60%, and Red (🟥) for <=30% in all text-based status bars.

## 2024-05-24 - Testing Discord TextInputs
**Learning:** `discord.ui.TextInput.value` is a read-only property that pulls from internal state. In unit tests mocking interactions, you cannot set `.value` directly to simulate user input.
**Action:** Set the internal `_value` attribute of the TextInput instance in test setup to simulate user input.
## 2024-05-24 - Actionable Permission Denied Messages
**Learning:** Generic "Access Denied" messages frustrate users by blocking them without offering a path forward.
**Action:** When blocking an interaction, always explain *why* (e.g., "This sheet belongs to @User") and provide a Call to Action (e.g., "Use /create to make yours") to convert the friction into engagement.

## 2025-05-27 - Context-Aware Access Control
**Learning:** Checking user state (e.g., "Has Character?") during permission checks transforms a negative "Access Denied" into a personalized onboarding flow (e.g., "Create yours" vs "View yours").
**Action:** In `interaction_check`, perform lightweight state checks to offer the most relevant next step, rather than a generic "Access Denied" message.
