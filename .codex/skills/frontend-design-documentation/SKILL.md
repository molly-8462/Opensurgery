---
name: frontend-design-documentation
description: Maintain OpenSurgery's frontend design schema whenever pages, routes, navigation, interactive elements, or frontend-backend data contracts change.
---

# Frontend design documentation

Use this skill for every task that creates, changes, removes, or reviews OpenSurgery frontend behavior. This includes HTML under `frontend/pages/`, `frontend/assets/js/`, frontend CSS that changes an interactive control, FastAPI page routing, and any backend endpoint or schema consumed by the frontend.

`docs/frontend-design-schema.pdf` is a required maintained deliverable. Do not finish a frontend change until its source (`docs/frontend-design-schema.md`) and the PDF describe the final implementation.

Before editing, inspect the affected page, shared JavaScript, and any API endpoint/schema it consumes. Then update the design schema with the final page purpose, inbound and outbound connections, request inputs, response fields rendered, authorization/state behavior, and any intentionally local or prototype-only control. Remove or revise obsolete entries rather than leaving historical descriptions.

Regenerate the PDF from the Markdown source and verify that it opens and has the same document content. Include the updated Markdown and PDF in the change. If a task changes frontend behavior but PDF rendering is unavailable, update the Markdown and report the rendering blocker; do not claim the documentation is complete.

For backend-only work, use this skill when the changed endpoint, field, authorization rule, or response behavior is consumed by the frontend. Do not use it for unrelated backend work.
