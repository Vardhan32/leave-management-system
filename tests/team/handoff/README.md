# Handoff files

One pair of files per part of the project:

| Part | For the person | For Claude Code |
| --- | --- | --- |
| Area 1: static analysis, white-box unit tests, mutation, CI | `area1-human.md` | `area1-claude.md` |
| Area 2: API testing and data generation (what is left) | `area2-human.md` | `area2-claude.md` |
| Area 3: use cases, usability, accessibility, security, performance | `area3-human.md` | `area3-claude.md` |
| Shared: test management and final submission | `shared-human.md` | `shared-claude.md` |

**Human files** explain what to do, in what order, and what you will be asked
in the viva.

**Claude Code files** are briefings to give Claude Code. Open Claude Code in
the repository root and tell it:

```text
Read tests/team/handoff/area1-claude.md and follow it.
```

Claude Code will then ask you before decisions and will not commit for you.

## Rules that apply to everyone

- Commit your own work under your own name. Commit history is checked in the viva.
- Do not add Claude (or any AI) as a co-author or collaborator on GitHub
  commits or pull requests.
- Anything you submit, you must be able to explain. If an AI tool wrote it,
  read it until you can.
- Every use of an AI tool goes into the AI-use record
  (`docs/team/ai_use_record.md`): tool, purpose, output, what you checked or
  changed. Keep your prompts.
- Your own tests go under `tests/team/`. Upstream tests (`backend/tests/`)
  earn no marks.

## Project facts

- System: LeaveDesk, `https://github.com/Vardhan32/leave-management-system`, MIT licence
- Baseline commit: `b002faa4b46ba2090489c200c61787551591c70d`
- Stack: Flask 3 + Flask-SQLAlchemy + Flask-JWT-Extended (Python 3.12), React 18 + Vite
- Workflows under test: W1 Apply for leave, W2 Review leave (approve / reject), plus cancel
- Shared records: `LeaveBalance.used_days`, `LeaveRequest.status`
- Requirement ids: `tests/team/api/support/requirements.py` (FR-01..FR-12, BR1..BR4)
- Demo accounts: `demo@leavedesk.in` / `demo1234` (employee), `admin@leavedesk.in` / `admin1234` (admin)
- Due: 29 November 2026
