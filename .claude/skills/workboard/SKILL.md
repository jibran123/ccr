---
name: workboard
description: Keeps the CCR Workboard (a Google Sheet drawn live by a dashboard) current. Use whenever CCR work starts, continues, changes state or ends; whenever the user mentions a new idea, feature, bug or follow-up, even in passing; when a board ID such as CCR-012 is named; and when the user asks what is on the board, next, blocked, ready or in progress. Covers picking up a task, checkpointing progress, blocking, sending to review and adding ideas.
---

# CCR Workboard

All CCR work is tracked in one Google Sheet. The CCR Workboard dashboard draws it live, so what you write to the sheet is what the user and every other session see.

- Sheet: "CCR Workboard", ID `1fJborDvFrN-dVjLmSpA0TP5j9TcQhmDovoWLrX95v0w`, tab `Backlog`, header in row 1
- Sheet link: https://docs.google.com/spreadsheets/d/1fJborDvFrN-dVjLmSpA0TP5j9TcQhmDovoWLrX95v0w/edit
- Dashboard: https://claude.ai/artifact/EH7AH9c1ZNMfzFJKuQz76a

Use the Google Sheets connector: `get_values` to read, `update_values` to change cells, `append_values` to add rows. Tool name prefixes differ between apps, and some apps load tools on demand, so search for "google sheets" tools if they are not listed. If no Google Sheets tool is available, never skip the update silently: print the exact row change for the user and ask them to make it or to turn the connector on.

## Columns

| Col | Name | What goes in it |
|---|---|---|
| A | ID | `CCR-` and three digits. Never reuse or renumber an ID. |
| B | Item | One line a teammate understands without the chat. |
| C | Feature | Group name. Reuse an existing one when it fits. |
| D | Status | Exactly one of: Idea, Backlog, Ready, In progress, Blocked, Review, Done |
| E | Priority | P0 (now), P1, P2, P3 (someday) |
| F | Agent | The session working on it (see "Your agent name"). Empty when nobody holds it. |
| G | Runs on | Exactly one of: VM, Cloud, Cowork, Chat, You |
| H | Next step | The next concrete action, written so a fresh session can continue with no chat history: files, commands, decisions already made. |
| I | Waiting on | What blocks it: a person, a credential, another ID. |
| J | Link | Session URL, merge request or pull request URL. |
| K | Updated | Today's date as text with a leading apostrophe: `'2026-11-08` |
| L | Source | Where it came from: a plan folder (`.superpowers/sdd/...`), a session, a review, a user idea. |

## Your agent name

Pick one name per session and use it on every row you touch: the session's title if you know it, otherwise `<Runs on>: <short topic>`, for example `VM: api-recon handover`. The dashboard groups its cards by this exact text, so keep it identical across rows. Put the session's URL in Link when you know it (cloud and Remote Control sessions have one).

## When to write (always, without being asked)

1. **Starting work.** Before changing anything, find the row: by ID if the user gave one, otherwise by matching Item and Feature. If found, set Status `In progress`, Agent, Runs on, Link and Updated, then read Next step and Source and continue from there. If not found, add a row first (see below), then claim it. If the row is already `In progress` under another Agent, ask the user before taking it over.
2. **A new idea, bug, feature or follow-up comes up**, from the user or from something you find: add a row straight away with Status `Idea` (or `Backlog` if the user has decided to do it), Priority P3 unless the user says otherwise, and Source naming this session or plan. Tell the user "Added CCR-0NN to the board." Don't start on it in this session unless the user asks.
3. **Checkpoint** after each meaningful step (a test passes, a commit, a decision, a finding) and whenever the user steps away: rewrite Next step and Updated. A short checkpoint too often is better than lost progress.
4. **Blocked:** Status `Blocked`. Waiting on says exactly what is needed and from whom. Next step says what to do once it arrives.
5. **Ready for the user:** Status `Review`, the merge request, pull request or commit in Link, and Next step saying what the user should check. Only the user sets `Done`; set it yourself only when they tell you to.
6. **Before the session ends or switches task:** a final checkpoint on every row you hold. Keep Agent filled while the row is `In progress` or `Blocked`; clear it when you hand the row back to `Ready` or `Backlog`.

One session works on one row at a time. Work found outside that row goes on the board as a new row, not into this session.

## Writing safely

- Read `Backlog!A1:L500` first. A row's sheet number is its index in `values` plus 1, because the header is row 1.
- Change only your row's cells, for example `Backlog!D7:K7`, never the whole sheet. Re-read that row just before writing; if someone changed it since, merge their change instead of overwriting it.
- Adding a row: re-read column A, take the highest number plus 1, write to the first empty row (or use `append_values`), then read the row back to check no other row has the same ID. On a clash, take the next number.
- Plain text only, no markdown. Never write credentials, tokens, passwords or personal data into the sheet.
- After writing, read the row back once to confirm it says what you meant.

## When the user asks about the board

For "what's on the board", "what's next" or "what's blocked": read the sheet and answer in this order: Blocked (with Waiting on), In progress (by Agent), Review, then Ready by priority. End with the dashboard link.
