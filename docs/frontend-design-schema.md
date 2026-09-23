# OpenSurgery frontend design schema

**Version:** 1.0  
**Audited:** 2026-09-22  
**Source of truth inspected:** `frontend/pages/*.html`, `frontend/assets/js/script.js`, and `app/api.py` / `app/schemas.py` / `app/serializers.py`.

## Purpose and boundaries

OpenSurgery is a server-hosted, multi-page frontend. FastAPI serves the static page files and also exposes canonical surgeon routes. The shared client controller calls `/api/v1` with same-origin credentials. This document maps every HTML page, its inbound and outbound navigation, its backend data dependencies, form submissions, and prototype-only controls.

Route conventions:

| Public concept | Canonical route | Legacy/static entry | Key identifier |
|---|---|---|---|
| Home | `/` | `home.html` | none |
| Surgeon info | `/surgeons/{slug}` | `index.html?surgeon={slug}`, `surgeon.html?surgeon={slug}` | `slug` |
| Surgeon reviews | `/surgeons/{slug}/reviews` | `reviews.html?surgeon={slug}` | `slug` |
| Surgeon talk | `/surgeons/{slug}/talk` | `talk.html?surgeon={slug}` | `slug` |
| Surgeon edit | `/surgeons/{slug}/edit` | `edit.html?surgeon={slug}` | `slug` |
| Surgeon history | `/surgeons/{slug}/history` | `history.html?surgeon={slug}` | `slug` |
| Revision | static `revision.html` | `revision.html?surgeon={slug}&revision={number}` | `slug`, `revision` |
| Review | static `review.html` | `review.html?review={slug}` | review `slug` |
| Member profile | static `profile.html` | `profile.html?user={display_name}` | `user` |

The implementation still contains sample links such as `index.html` and `revision.html?revision=124`. Once a surgeon page loads, shared JavaScript rewrites its surgeon-local links to canonical `/surgeons/{slug}` routes. A static profile page without a `surgeon` identifier redirects to the directory.

## Shared shell, state, and navigation

Every page loads `/assets/css/styles.css` and `/assets/js/script.js` (some pages add a cache version). The header has a wordmark to home, desktop search, auth/account links, and a mobile menu. When `localStorage.opensurgery_user` contains a `displayName`, the account links become Messages and Account. This is presentation state only; backend authorization relies on same-origin session cookies.

The generated mobile drawer links to Home, Directory, Procedures, Search, Add surgeon, Write review, Pending edits, Guidelines, Account, Messages, Settings, and Policies. All pages with the common header can reach those destinations. Shared search submits to `search.html?q={encoded query}`; an empty query goes to Directory. Footer links commonly lead to Policies, Privacy, and Guidelines.

| Shared UI element | Input / action | Output / destination | Backend effect |
|---|---|---|---|
| Header and home search | query `q` | Search or Directory | Search page calls surgeon and procedure APIs |
| Mobile drawer | navigation selection | page route | none directly |
| Auth/account links | session-derived display name | Account or Messages | localStorage read; cookie session remains authoritative |
| Photo toggle / photo slots | show/hide preference | CSS class and `aria-pressed` | no persistence |
| Language, more, topic-tools menus | button click | in-page or static navigation | no backend call |

## Page inventory and page connections

“In” means a normal page link, generated navigation, redirect, or browser history location that leads into the page. “Out” lists primary page destinations; the shared shell destinations above apply where present. “Data” distinguishes live API use from static/prototype UI.

| Page | Purpose and inbound connections | Primary outbound connections | Live backend data contract | Prototype/static behavior |
|---|---|---|---|---|
| `home.html` | Entry route; wordmark/drawer. | Directory, Procedures, Reviews, profile cards, Write review, Create account, policy pages. | `GET /surgeons`; renders first three summaries. | Topic and procedure promotion copy is static. |
| `directory.html` | From Home, Procedures, search fallback, profile country link, Add-surgeon cancel. | Canonical surgeon profile; Add surgeon; policies. | `GET /surgeons?q&country&procedure`; renders cards and total. | Long-term-results checkbox is only a legacy DOM filter; it is not sent to API. |
| `search.html` | From any search form and drawer. | Surgeon profile, procedure anchor, policy. | `GET /surgeons?q`, `GET /procedures`; client merges results. | Result category tabs filter already-rendered results. Community search has no API source. |
| `procedures.html` | From Home/drawer/search. | Filtered Directory links. | `GET /procedures`; fills category sections and procedure cards. | Categories with no API matching section remain empty. |
| `index.html` | Legacy surgeon profile entry; canonical `/surgeons/{slug}` serves this file. From Directory/Home/Reviews/Talk/Edit/History/Practice. | Surgeon reviews, talk, edit, history; Write review; practice; country-filtered directory; external practice URL. | `GET /surgeons/{slug}`; fills title, infobox, body, procedures, review count, links. `GET /me` conditionally adds admin delete. | Reference material is a server-side history pointer, not rendered citations. |
| `surgeon.html` | Alternate lightweight surgeon profile using `data-surgeon-page`. | Directory, surgeon reviews/talk, policies. | `GET /surgeons/{slug}`; fills detail fields and rewrites links. `GET /me` may add delete control. | Duplicates part of `index.html`; it is not served by a canonical route. |
| `reviews.html` | Canonical `/surgeons/{slug}/reviews`; from profile, Home, review detail. | Info, Talk, Write review, review detail, policies. | `GET /surgeons/{slug}` and `GET /surgeons/{slug}/reviews?limit&offset`; dynamically renders rows and Load more. | Procedure/sort controls are populated but never used in a request; static breakdown is hidden. |
| `review.html` | From review rows and profile activity. | Surgeon info, surgeon reviews, reviewer profile. | `GET /reviews/{reviewSlug}` renders title, author, narrative, breadcrumb. `GET /me` + `POST /admin/reviews/{slug}/remove` gives admins a prompted delete. | “Thanks” changes local button state only. |
| `write-review.html` | From Home/profile/reviews; accepts `surgeon` query to select surgeon. | Home/Login; post-submit stays in place. | `GET /surgeons`, `GET /procedures`; `POST /media` per selected image; `POST /reviews` submits review. | Draft and preview do not persist. Form does not send ratings, country code, cost amount/currency, wait time, or complication/revision detail. |
| `edit.html` | Canonical `/surgeons/{slug}/edit`; from profile edit links. | Info, History, Directory on missing slug. | `GET /surgeons/{slug}`, `GET /procedures`; `POST /surgeons/{slug}/proposals`. | Portrait preview is local only; `portrait` is never uploaded. Extra source inputs added by UI have no name and are not submitted. |
| `history.html` | Canonical `/surgeons/{slug}/history`; from profile, revision, drawer More menu. | Info, Reviews, Talk, Edit, Revision, member profile, pending, history export, policy. | `GET /surgeons/{slug}`, `GET /surgeons/{slug}/history`; renders revision list. | Filtering is DOM-only; old-page and undo controls do not call history/proposal APIs. JSON export is static fixture data. |
| `revision.html` | From History revision links. | History, current profile, Talk, member profile. | `GET /surgeons/{slug}`, `GET /surgeons/{slug}/revisions/{number}`. | Restore and permanent link/copy controls are local only; static old links omit a surgeon slug. |
| `talk.html` | Canonical `/surgeons/{slug}/talk`; from profile, reviews, history, revisions. | Info, Reviews, profile pages, Talk history, policy. | `GET /surgeons/{slug}`, `GET /surgeons/{slug}/talk`; dynamic new-topic composer calls `POST /surgeons/{slug}/talk`. | “Reply” opens a new-topic form, so replies are new root topics; watch/subscribe are local only. |
| `talk-history.html` | From Talk tools/activity. | Info, Talk, Revision, Talk policy. | none. | Entire timeline is fixture content. |
| `practice.html` | From profile practice link. | Linked canonical surgeon profiles and static policy pages. | `GET /practices/northbank-reconstructive-center`; renders locations and linked surgeons. | Practice slug is hard-coded; website is returned but not rendered. |
| `add-surgeon.html` | From drawer/Directory. | Login, Directory cancel; remains after submit. | `GET /procedures`, `GET /countries`; `POST /surgeons` creates a pending profile. | None beyond client validation. |
| `pending.html` | From drawer/Account/History. | Published profile after approval; static Talk/Revision links in original fixture. | `GET /proposals`; authenticated editor flow: `GET /me`, `GET /moderation/surgeons`, `POST .../approve`, `GET /moderation/reviews`, `POST .../approve|reject`. | General proposal cards have no approve/reject buttons; local button redirect handler mostly targets fixture markup removed by live render. |
| `profile.html` | From reviews, talk comments, history editors, messages. | Review/Talk activity links, Guidelines/Privacy. | `GET /users/{display_name}`; admins also `GET /me`, `GET /admin/users/{name}`, `PATCH .../role`, `POST .../ban`. | Message dialog sends `POST /messages` only when it closes with return value `send`; no profile-page block/report UI. |
| `messages.html` | From header/drawer/Account. | Account and selected member profile. | `GET /conversations`; `GET /conversations/{id}/messages`; `POST /conversations/{id}/messages`. | Static composer uses the same UI but live handler takes over. |
| `account.html` | From header/drawer. | Messages, own profile, reviews, pending, talk, settings, privacy. | none. | Dashboard counts and activity are sample content; sign-out is live `POST /auth/logout`. |
| `settings.html` | From drawer/Account. | Account, Privacy. | `GET /me`; `PATCH /me`; `GET /me/export` downloads JSON; `DELETE /me` deactivates after browser confirm. | Display name is shown but is not editable/submitted. |
| `create-account.html` | From header/Home/login. | Login, Terms, Guidelines, Account on success. | `POST /auth/register`; stores display name locally and redirects. | Age and terms checks are browser validation only; not included in request body. |
| `login.html` | From header, auth links, protected-form prompts. | Create account, Forgot password, Account on success. | `POST /auth/login`; stores display name locally and redirects. | none. |
| `forgot-password.html` | From Login. | Login. | `POST /auth/password-reset` with email. | none. |
| `reset-password.html` | Reset link; token read from URL fragment. | Login after success. | `POST /auth/password-reset/confirm` with fragment token and password. | Removes fragment from browser history before submission. |
| `guidelines.html` | From drawer, footer, auth/legal links. | Anchors only plus shared shell. | none. | Static policy content. |
| `policies.html` | From Home, drawer, legal links. | Anchors, Privacy, Guidelines. | none. | Static policy content. |
| `privacy.html` | From footer, policies, forms. | Anchors plus Home/Login. | none. | Static privacy content. |
| `terms.html` | From registration agreement. | Home. | none. | Static terms content. |

## Backend data-flow schema

All calls use JSON except `POST /media`, which sends `multipart/form-data`; the helper automatically omits JSON content-type for `FormData`. Errors expect a JSON `{detail}` and are displayed in local status elements. Session-protected endpoints use the browser’s same-origin cookie.

| Frontend flow | Reads from backend | Sends to backend | Backend data returned to UI |
|---|---|---|---|
| Authentication | none | Register `{email, display_name, password, approximate_region}`; Login `{identity,password}`; reset `{email}` or `{token,password}`; logout empty | Register/login return user data; reset request returns generic message. |
| Account settings | `GET /me` | `PATCH /me` with bio, region, message/account/contact notification flags; `DELETE /me` | User object; export returns account JSON blob. |
| Surgeon discovery | `GET /surgeons?q&country&procedure` | none | `{items,total}`; summary fields: slug, name, initials, specialty, city, region, country, website, review count, procedures, updated timestamp. |
| Surgeon profile | `GET /surgeons/{slug}` | Admin delete sends reason/status to `POST /moderation/surgeons/{slug}/remove` | Summary plus `article_body`, profile snapshot, current revision number. |
| New surgeon | `GET /procedures`, `GET /countries` | `POST /surgeons` with identity/location/site/practice/article/procedure/source data | `{id,slug,status}`; profile remains pending until editor approval. |
| Editorial proposal | `GET /surgeons/{slug}`, `GET /procedures` | `POST /surgeons/{slug}/proposals` with merged article body, summary, source, selected procedures, profile snapshot | `{id,state}`. |
| Revision history | `GET /surgeons/{slug}/history`; revision detail by number | none | History items contain revision number/date/editor/summary/change type/kind; revision includes body and snapshot. |
| Reviews | `GET /surgeons/{slug}/reviews`, `GET /reviews/{slug}`, source lists | Uploads `file` to `POST /media`; `POST /reviews` references returned media IDs | Published review contains surgery/reviewer/procedure/narrative/status/ratings/approved photos. |
| Talk | `GET /surgeons/{slug}/talk` | `POST /surgeons/{slug}/talk` `{title,body}` | Topic contains slug/title and published comments. |
| Members and messages | `GET /users/{name}`, `GET /conversations`, messages per conversation | `POST /messages` opens/reuses conversation; reply endpoint sends `{body}` | Profile counters/bio; conversation previews; messages include sender/body/date/mine. |
| Moderation | `GET /me`; pending surgeon/review lists | Approval/rejection/removal endpoints, admin role/ban endpoints | State updates; published surgeon approval returns its slug. |
| Practice and procedure reference data | `GET /practices/{slug}`, `GET /procedures`, `GET /countries` | none | Practice locations/linked surgeons; procedure categories/descriptions/techniques; country names/codes. |

## Data ownership, authorization, and state transitions

| Entity | Public read | Authenticated write | Editorial/admin actions | UI surfaces |
|---|---|---|---|---|
| Surgeon | published only | new surgeon submission; editorial proposal | editor approves new profile/proposal; admin removes; editor restores endpoint lacks UI | Directory, profile, edit, history, pending |
| Review and photo | published review/photo only | review author uploads media then submits review | editor approves/rejects review/photos; admin removes review | Reviews, review detail, write review, pending |
| Talk topic | published topics/comments only | authenticated user creates root topic with first comment | no moderation UI despite report/moderation APIs | Talk |
| User | active profile data | own account settings; message reply | admin role and ban controls | Profile, settings, messages |
| Proposal | pending proposals exposed publicly by current endpoint | authenticated user creates | editor approval/rejection API; only pending page exposes approval of new surgeon/review, not generic proposal | Edit, pending |

## Gaps and integration risks

1. `surgeon.html` is an alternate profile implementation; its static links and its distinct `data-surgeon-page` make it a potential maintenance duplicate of canonical `index.html`.
2. Directory, search, and procedure flows use inconsistent query values in some static links: the API supports either a procedure slug or name, but generated procedure links use slugs.
3. Static fixture controls can imply persistence where none exists: watch/subscribe, thank-you, revision undo/restore, review filters, history paging/export, draft/preview, portrait upload, long-term directory filter, and Talk replies.
4. The backend exposes block, unblock, report, proposal approve/reject, surgeon restore, photo moderation, and report moderation APIs with no corresponding active frontend surfaces.
5. The edit page includes portrait and multiple sources in the interface but does not send them. The review payload leaves several supported backend fields unset.
6. `pending.html` renders public pending proposal metadata and only wires approval for new surgeon/review submissions. Generic edit proposal approval/rejection lacks buttons and role-safe UI.
7. Local storage only stores a display name, so a stale local display can disagree with a deleted or expired server session. Every privileged UI path must continue to rely on the backend response.

## Maintenance rule

For every frontend change, update this Markdown source and regenerate `docs/frontend-design-schema.pdf` in the same change. A frontend change includes a page, route, hyperlink, query parameter, form field, JavaScript behavior, API request/response consumption, client-side state, CSS-driven interactive control, or backend endpoint used by the frontend. The project skill at `.codex/skills/frontend-design-documentation/SKILL.md` makes this a required completion step.
