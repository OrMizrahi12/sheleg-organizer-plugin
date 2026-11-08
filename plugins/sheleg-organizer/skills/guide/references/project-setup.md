# Setting up a project

Managers describe a project in words, or bring what they have: a staffing table, a list of posts, a site plan, a photo of a whiteboard. You turn it into the project's setup, without anyone writing code.

## 1. Read what exists

- `me_get` gives the user's grade and the projects they manage. Only a company admin or the root admin creates a project (`projects_create`, which also creates its first sector). A project manager sets up the projects they already run.
- `config_get` (with the project's id) returns the whole current setup: sectors, facility levels, the facility tree, positions, shifts, staffing standards, weekday overrides, required tags, settings and the company's tags. Archived items are included and marked.
- `projects_getProfile` returns the project's profile: the managers' own words about the project's standing judgment. Read it before you plan.

Never create something that already exists under the same name. Reuse it, or ask.

## 2. Propose one plan

Write the whole setup as one plan the user can check at a glance. Use tables, in the user's language:

1. **Sectors.** Each sector gets its own roster, its own shifts and its own workers.
2. **Facility levels**, outermost first, if the tree has more than one tier. For example, אזור › בניין › עמדה.
3. **The facility tree**: every facility, under its parent, in roster order.
4. **Positions** at each facility, such as מאבטח or בודק בכניסה. A position may hang on any facility, not only on the innermost ones.
5. **Tags and required tags.** Which tags a position or a facility demands, such as רישיון נשק. A tag on a facility applies to every position beneath it. Use only tags the company has (`tags_list`), or list the new ones to create.
6. **Shifts** of each sector, with their default hours. An end at or before the start runs into the next day.
7. **Staffing standards**: for each position, shift and day type (midweek, friday, saturday, holiday, holiday_eve), the minimum, target and maximum. Add hours only where they differ from the shift's. Add weekday overrides only where one weekday differs, such as a gate that opens at 10:00 on Sundays.
8. **Open questions.** List everything the source did not say, such as Friday staffing, night hours or which posts need a weapon licence. Do not fill these in. Ask.

Also list anything the user asked for that the system cannot express. Offer to record each one with `settingProposals_file`, in their words.

Then stop and wait. Change nothing until the user confirms the plan, or confirms it with corrections.

## 3. Create, in order

Each step needs the ids the previous one returned.

1. `sectors_create`, for each sector beyond the project's first. Rename the first with `sectors_update` if needed.
2. `shifts_create` for each sector.
3. `facilityLevels_set`, when there is more than one level.
4. `facilities_create`, parents before children. A child takes `parentId`, and the sector follows from the parent. Give `rank` to order siblings, starting at 1. Give `levelId` only when a facility skips a level.
5. `positions_create` at each facility.
6. `tags_create` for the new tags, then `facilities_setRequiredTags` and `positions_setRequiredTags`.
7. `standards_set` for each position, shift and day type, then `standards_setOverride` for weekday exceptions.
8. `projects_updateSettings` only for settings the user asked about, such as the availability deadline or the facility coverage order.

These are setup changes. When a call returns `needs_acknowledgement` or `blocked`, stop. Tell the user, and continue only as they decide.

## 4. Read it back

Call `config_get` again. Compare it with the confirmed plan, and report in a short summary: what was created, anything that differs, and the open questions that remain. Do not claim a step succeeded unless the read-back shows it.

## Changing an existing setup

- Rename, re-rank, recolour, archive or restore with the `_update` tools. Archiving a facility or a position removes its slots that have not started. When workers hold some of them, it asks first (`archive_releases_shifts`): show the count to the user before you acknowledge.
- `facilities_move` moves a facility, with its positions, standards and slots, within its sector. To move one to another sector, duplicate it there (`facilities_duplicate`) and archive the original.
- Removing a standard (`standards_remove`) stops it producing slots. Ask first.
