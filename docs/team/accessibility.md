# Usability and accessibility (Area 3)

Tools: axe-core 4.14.1 through `@axe-core/playwright` (tags `wcag2a`, `wcag2aa`, `wcag21a`,
`wcag21aa`, `wcag22aa`, `best-practice`) and Lighthouse 12.8.2 (accessibility, best practices,
SEO, desktop preset), both on the production build of the app, signed in, same seeded data.
Raw reports: `tests/team/e2e/reports/axe/{before,after}/*.json` and
`tests/team/e2e/reports/lighthouse/{before,after}/*.html|json`. The tables with all numbers are in
[accessibility_before_after.md](accessibility_before_after.md).

Key screen of each use case:

| Use case | Screen scanned |
| --- | --- |
| UC-01 apply, UC-03 cancel | My leave (`/leave`), apply dialog, request detail dialog |
| UC-02 review | Approvals (`/approvals`), review dialog |
| (entry point) | Login (`/login`) |

## 1. Task and keyboard tests

| Test | What it proves | Result |
| --- | --- | --- |
| U-01 | W1 task from the login form to a stored request. 13 casual days are refused with "Only 12 day(s) of Casual Leave remain for 2029." and the hint "Try a shorter range or another leave type"; the end date is corrected to 5 days, the screen shows "Request sent. Your manager will review it shortly.", and the API holds one pending request of 5 days | pass |
| U-02 | W2 task: admin opens the queue, sees the balance context, approves, sees "<name>'s request was approved." | pass |
| U-03 | Keyboard only: focus order is Leave type, Start date, End date, Reason, Cancel, Send request; typing the form and pressing Enter on "Send request" stores the request | pass. Note: the Cancel button sits between Reason and Send request in the page order, so the submit button is the sixth stop, not the fifth |
| U-04 | Focus moves into the dialog when it opens | failed on the original build, pass after the fix |
| U-05 | Tab stays inside the dialog | failed on the original build, pass after the fix |

The pre-fix run is saved in `tests/team/e2e/reports/logs/run1_before_fix_use-cases_usability_security.txt`.

One more usability finding came from the use case tests: the balance hint in the Apply and Review
dialogs uses the current year's balance, not the balance of the year of the chosen dates (DEF-A3-01
in [defects_area3.md](defects_area3.md)).

## 2. Merged findings (an issue found by both tools is counted once)

| Id | Issue | Found by | Element | User impact | Proposed fix | Severity |
| --- | --- | --- | --- | --- | --- | --- |
| A11Y-01 | Text contrast below 4.5:1 | **axe and Lighthouse** (counted once) | `.filter-tab` (status tabs, 3.68:1), `.status--cancelled` badge (4.3:1), `.leave-preview__copy > span` (4.09:1), `.quote-block > span`, `.review-person` text (4.09:1), avatar initials (3.7:1; 1.4:1 on the login panel), login `.demo-box__copy > span` (4.09:1) | People with low vision or in bright light cannot read the tab labels, hints and badges | Darken the `--muted` text token from `#6f7484` to `#5d6373` (4.7:1 to 5.9:1 on the cream surfaces) and the cancelled badge text to `#575349` (6.2:1); avatar and login colours separately | Serious (axe) |
| A11Y-04 | Table header cell without text | axe only | `th[aria-label="Actions"]` on My leave and Approvals | A screen reader reads an empty column header | Put "Actions" in a visually hidden span inside the `th` | Minor |
| A11Y-05 | `robots.txt` not valid | Lighthouse only | `/robots.txt` returned the app's HTML | Search crawlers get an invalid file (SEO 91) | Add `frontend/public/robots.txt` | Low |
| A11Y-02 | Dialog does not receive focus when opened | keyboard test U-04 (neither tool) | `Modal.jsx` | A keyboard or screen-reader user stays on the page behind the dialog and has to Tab through it to reach the form | Move focus to the first field when the dialog opens | Major |
| A11Y-03 | Focus is not trapped and not restored | keyboard test U-05 (neither tool) | `Modal.jsx` (`aria-modal="true"` but Tab leaves) | Tab walks through content the dialog is supposed to hide; closing loses the user's place | Keep Tab and Shift+Tab inside, restore focus to the opener on close | Major |
| A11Y-06 | Errors are `role="status"` and not tied to fields | source review | `InlineAlert.jsx`, field errors in `ApplyLeaveModal.jsx` | Error text is announced politely and field errors are not linked to their inputs | Use `role="alert"` for errors, `aria-invalid` and `aria-describedby` on inputs | Minor (open) |

Total distinct issues: 6 (1 found by both tools, 1 by axe only, 1 by Lighthouse only, 2 by the keyboard
tests only, 1 by source review). Lighthouse's accessibility audit and axe-core use the same rule engine
for contrast, which is why that issue appears in both.

## 3. The fix (My leave screen and its dialogs)

Files: `frontend/src/styles.css` (token `--muted`, `.status--cancelled`, `.sr-only`),
`frontend/src/pages/MyLeavePage.jsx` (header cell), `frontend/src/components/Modal.jsx` (focus
management), `frontend/public/robots.txt`.

Because the contrast problem sits in one colour token, darkening the token improved every screen,
not only My leave. The screen chosen for the before-and-after comparison is My leave with the apply
and request-detail dialogs.

**Result (axe elements flagged / Lighthouse accessibility score)**

| Screen | axe before | axe after | Lighthouse before | Lighthouse after |
| --- | --- | --- | --- | --- |
| My leave | 6 | **0** | 96 | **100** |
| Apply dialog | 7 | **0** | 97 | 100 |
| Request detail dialog | 12 | **0** | (not a Lighthouse page) | |
| Approvals | 11 | 1 (empty header, not fixed on this page) | 96 | 100 |
| Review dialog | 16 | 2 | | |
| Login | 3 | 2 (avatar colours) | 95 | 95 |

Lighthouse SEO went from 91 to 100 on every page (robots.txt). Best practices stayed at 100.

Remaining, not fixed in this change: the empty header on Approvals, avatar initials colours and the
login demo-box text (same pattern, a follow-up), and A11Y-06.

## 4. How to reproduce

```powershell
cd tests\team\e2e
$env:AXE_PHASE="after"; npx playwright test --project=accessibility
node lighthouse-run.mjs after
node scripts\compare-a11y.mjs
```
