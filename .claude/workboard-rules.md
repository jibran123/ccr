## CCR Workboard

All CCR work is tracked in the Google Sheet "CCR Workboard" (ID 1fJborDvFrN-dVjLmSpA0TP5j9TcQhmDovoWLrX95v0w, tab Backlog), which the dashboard at https://claude.ai/artifact/EH7AH9c1ZNMfzFJKuQz76a draws live. Follow the `workboard` skill for how to read and write it. These rules apply to every session, without being asked:

- Before starting CCR work, find its row (by CCR ID or topic) and set it In progress with your agent name. If it has no row, add one first.
- Any new idea, bug, feature or follow-up that comes up, even in passing, becomes a new row straight away (Status Idea), and you tell the user its ID.
- Rewrite the row's Next step after each meaningful step and before you stop, so a new session can continue without this chat.
- Waiting on the user or anything else: Status Blocked, with Waiting on filled in. Ready for review: Status Review, with the link. Only the user sets Done.
- One session works on one row at a time. Work found outside it goes on the board, not into this session.
- If the Google Sheets connector is unavailable, print the row change for the user instead of skipping it.
