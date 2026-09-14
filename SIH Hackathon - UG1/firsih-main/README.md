# CaseVault: local backend prototype

This version fixes the browser-only persistence and authorization gaps for a **synthetic-data local demo**. It is not a production police evidence system. No Grok call or cloud deployment has been configured.

## Start (one terminal, including when npm is missing)

From this folder, run:

```sh
python3 -B start_demo.py
```

Open http://localhost:5173 after the launcher prints READY. Keep this terminal open; Ctrl+C stops both services. It uses installed Node.js or the existing bundled runtime on this Mac, installs frontend dependencies on first run, and starts both servers. This launcher uses backend port 8001; the manual two-terminal method below uses 8000. Do not start multiple copies of the launcher. A working internet connection is required if first-time dependencies are not cached.

If you previously started the backend alone, you may stop that earlier terminal with Ctrl+C. The launcher uses the same persistent database.

For a normal Node/npm setup on any computer, install the LTS release from https://nodejs.org/en/download, reopen Terminal, and check `node -v` and `npm -v`. Python is already available on this Mac. The bundled-runtime fallback is only a convenience for this machine.

## Start manually (two terminals)

Install Node.js (LTS) and Python 3.9 or newer. Open two terminals in this folder.

Terminal 1:

```sh
python3 -B backend/server.py
```

Terminal 2:

```sh
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** (use this exact hostname). Vite proxies `/api` to the local backend on port 8000. Keep both terminals running. A backend-only launch does not open the UI. Python uses only its standard library.

If using pnpm instead of npm, `pnpm install` and `pnpm dev` work too. A pnpm lockfile is included.

## Demo accounts

These are intentionally public **synthetic** credentials, seeded only by the backend. They are not included in the frontend bundle. Do not reuse them for real users.

| Person | Login | Password | Assigned access |
|---|---|---|---|
| Rahul Menon | rmenon | Kochi@004 | MG Road cases 101 and 104; can upload |
| Vishnu Prasad | vprasad | Kochi@010 | Case 104; request access to 105 |
| Priya Nair | pnair | Kochi@002 | Reviews MG Road cases |
| Anil Kumar | akumar | Kochi@001 | Explicit fallback reviewer for case 105, not blanket Level 5 access |

Five synthetic cases and two actual synthetic TXT documents are created on first start. Sample files are attached to cases 104 and 105. The seed no longer claims that an FIR/forensic original exists when there are only labels.

## Show the full workflow

1. Start the API and frontend. Sign in as Rahul.
2. Add Record → existing case 104 → upload a synthetic TXT/PDF/PNG/JPG, adding a distinctive note. File limit: 50 MB. Content signatures are checked for image/PDF formats; this is not malware scanning.
3. Search the note, open case 104 and download the original. Refresh and sign back in if needed. Restart the API and verify the same file still downloads.
4. Sign in as Vishnu. Search **Highway** or **2024-CR-105**, enter a reason, and request access. Do not search its private summary before approval: that summary is deliberately excluded.
5. Sign in as Anil. In Review Inbox, approve the request for one day. Alternatively reject it.
6. Sign back in as Vishnu, open case 105, and download its synthetic sample file.
7. Sign in as Anil and revoke the grant. Vishnu's next download/view is denied. Grant expiry also removes access automatically on the server.
8. Open Audit history from the sidebar. Approved/revoked state appears after an action or the 5-second refresh. Already viewed/downloaded information cannot be retroactively erased from a person's device.

## What is actually implemented

- Server-side login with individually salted PBKDF2-HMAC-SHA256 hashes (600,000 iterations), random one-hour sessions stored as token hashes, HttpOnly/SameSite cookies, logout invalidation, login attempt limiting, and origin checks for writes. HTTP is only for localhost; HTTPS sets Secure cookies.
- A server-side SQLite database with users, cases, exact user-ID assignments, explicit reviewers, sessions, requests/grants, documents and audit events.
- Original file bytes, immutable upload IDs, per-upload metadata, checksum, and audit entry committed in the same database transaction. Every upload creates another file record; no silent overwrite. Failed transactions do not report success.
- Server checks on case viewing, search, upload, download, requesting and reviewing. The client cannot grant itself access by changing an officer ID or revealing a button.
- Request reasons, reviewer-only approve/reject, grants lasting at most 30 days, expiry, revocation, duplicate-pending prevention and self-approval prevention.
- Audit events for logins/logout, search, uploads, requests, decisions, case views, downloads and denied operations. Audit visibility is limited to the actor and assigned case reviewer.
- Keyword search of case data and uploaded metadata. File contents are NOT OCR-extracted or indexed.

## Permission policy for this demo

Case ID, crime type and station are deliberately discoverable by all signed-in synthetic officers. No suspect, incident location, summary, document metadata or file body is returned for unauthorized cases. Search operates on this same split: private terms cannot match restricted cases.

An explicit case assignment or reviewer assignment permits reading and upload. A current approved grant permits reading/download only. Level 5 has no global bypass. Case 105 has Anil as its explicit fallback reviewer; station inspectors review their own seeded station cases. Only Level 3/4 officers may create cases, and the backend assigns their real profile's station and identity.

This demo uses **case-level access**: a case grant covers all its documents. Separate restricted-document policies, organization/station administration, reviewer delegation, and external-role restrictions need agreement and implementation before real use.

## Where files are saved

`backend/data/casevault.sqlite3` stores both document bytes and records on the machine running the API. It survives browser refresh and backend restart; it is not tied to a user's browser. The database is excluded from version control. Losing that file loses demo records, so back it up if needed. Do not delete it to apply code updates.

Legacy browser-local records are not imported automatically. The previous version never stored original file bytes, so those originals must be uploaded again. Its localStorage data is ignored by this version.

## Still planned

- Shared deployment: Supabase Auth + PostgreSQL + a private Storage bucket, or a hosted backend with equivalent controls. The Python/SQLite implementation here is a runnable local milestone, not the earlier proposed Node/Express/Supabase deployment. Do not host this standard-library development HTTP server publicly.
- HTTPS hosting, production accounts/identity provisioning, hardened session handling, backups and restore tests, malware scanning, operational monitoring, durable private object storage, and explicit document-level policies.
- Application-level file encryption and external key management. The database/file bytes are **not encrypted by this application**. Host disk encryption is a separate setting.
- OCR, Grok extraction/summarization and semantic search. No xAI key is required to use the current app.
- Stronger audit integrity. The current database administrator can alter the log; it is not blockchain, tamper-proof evidence, or proof of court admissibility.

## Where Grok fits

Use the database for authoritative users, assignments, permissions, requests, grants, metadata and audit events. Use private object storage for originals in the hosted version. Grok helps extract fields, summarize permitted documents or interpret searches; it does not replace either service and must not decide permissions.

Recommended sequence: authenticate → determine permitted case/document IDs → retrieve only permitted material → optionally send that material to Grok → validate its output → return an answer with source IDs. Treat uploaded document instructions as untrusted content. Keep API keys in backend environment variables, never React or GitHub. Do not give a model unrestricted access to a collection containing all cases. Revocation must remove a document from the allowed retrieval set on the next request.

If using xAI Collections, upload a permitted indexing copy through the backend, attach it to a collection, and store its xAI file/collection IDs alongside your document record. Collections provides persistent searchable documents, but your own database remains the source of truth for permissions and workflow. Only use synthetic copies until an appropriate data-handling policy is agreed.

Official references:
- https://docs.x.ai/developers/files/collections/api
- https://supabase.com/docs/guides/auth
- https://supabase.com/docs/guides/storage/security/access-control

## Verification

```sh
python3 -B backend/test_server.py
cd frontend
npm run build
```

The integration test uses a temporary on-disk database and localhost port 18090. It covers invalid login, unauthorized state/view/download/upload, protected search, upload byte preservation, validation failures, create-case restrictions, wrong reviewer and self-approval, invalid origin, approve/reject/revoke/expire, server restart, audit and logout. It deletes its temporary test database; it does not touch your demo database.

## GitHub

The supplied Downloads folder was not a Git checkout and has no configured remote. Edits to it are real local file changes, but they do not update GitHub. Copy the reviewed source changes into your team's actual clone, commit, then push. A connected hosting service may deploy that push depending on its settings. Never commit the runtime database, real evidence, `.env`, secrets, or `node_modules`.

## Upload limit and video

The file limit is now **50 MB (50 × 1024 × 1024 bytes)** in both browser and backend. Formats remain PDF, PNG, JPG/JPEG and UTF-8 TXT. Videos are not accepted yet. The request limit also allows for base64 encoding overhead.

This local demo buffers uploads in memory and saves file bytes in SQLite. For very large videos, implement private object storage with resumable/multipart uploads; put file IDs, permissions and checksums in the database. Preserve the original and generate previews separately. Merely increasing this limit to gigabytes is not the right video-storage design.

## API and restarting it

An API is the interface the website uses to ask the backend to log in, save files, search records, or approve requests. The backend performs permission checks and talks to the database.

Restarting the API means stopping the backend process with Ctrl+C and running its start command again. It does not mean deleting or resetting the database. With `start_demo.py`, Ctrl+C and rerun the launcher; with manual startup, restart Terminal 1 only.

## Audit access today

Open Audit history from the sidebar. A signed-in officer sees their own events plus events for cases where they are explicitly assigned as reviewer. Anil reviews case 105; Priya reviews MG Road cases. There is currently no separate admin-only Audit Integrity screen or hash-chain verifier.

## Later: OCR semantic search

Extract OCR on the backend, divide text into chunks, and link every chunk to its case/document permissions. Generate embeddings using one chosen embedding model, store them in PostgreSQL/pgvector, and search only permitted chunks. Keep full OCR text and vectors private. Recheck current grants before returning snippets or sending them to Grok; Grok can summarize permitted results, with source document/page citations. OCR and semantic search are not enabled in this version.

## Updated workspace and notifications

- **Overview:** role-appropriate shortcuts, request cards and unread notification counts. The Review Inbox is shown only to explicitly assigned reviewers; Rahul sees My Requests.
- **My Requests:** case names, request reasons, reviewer/status, expiry, and an Open case link for approved active requests. Filters cover pending, active, rejected, expired and revoked requests.
- **Review Inbox:** pending approvals and active grants, separate from the case search screen. Grant durations are 1, 2, 3, 5, 10, 15, 20 or 30 days, or a custom whole number between 1 and 30. The API enforces a maximum of 720 hours (30 days, not a variable calendar month).
- **Revoke access:** opens a confirmation dialog. Keep access cancels without changing the grant; Confirm revocation submits the action. The notice explains immediate loss of this grant, other possible valid assignments, and the inability to recall downloaded files.
- **Notifications:** persistent, user-specific in-app messages for new reviewer requests and requester approvals, rejections, revocations and expiry. Unread badges and a banner appear across the workspace. Mark read state survives refresh and backend restart. No email, SMS, or operating-system push notifications are sent. While the app is open, polling every 5 seconds detects changes; while away, updates are shown on the next sign-in. Expiry is always enforced by timestamps; expiry notifications are materialized when authenticated workspace state is fetched or the server restarts.
- **Audit history:** separate screen with the existing actor/reviewer visibility policy. This update does not add admin-only audit access or hash-chain verification.
- **Theme:** use the sun/moon button at the top right. Light/dark preference is stored in this browser and is also available on the sign-in screen.

The sign-in title is “Secure Legal & Investigation Document Management”. The tagline “Secure case files. Smarter search. Controlled access. Tamper-proof justice.” expresses the intended product; the adjacent prototype note discloses that encryption, AI search and tamper-proof audit integrity are planned.

Existing request decisions and files are preserved during this update. Existing pending/current decisions receive a notification on the first upgraded server start; deduplication prevents repeated messages on later starts.
