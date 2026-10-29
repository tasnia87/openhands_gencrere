# Gather — webinar study baseline

A small, local video-conferencing prototype for the GENCRE-RE / OpenHands pilot. Python + Flask + SQLite + plain JavaScript + WebRTC. No API key, paid video service, frontend build, or Docker is required. Python 3.12 is the tested version.

## Start on Windows (PowerShell)

Extract the archive, open the `webinar_baseline` folder, and run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

If your installed Python is a different supported version, replace `py -3.12` with `py`. Open http://localhost:5000. Keep the terminal open. Press Ctrl+C to stop.

On Linux / inside an OpenHands workspace:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

The development server binds to localhost only. Backend tests need no server and no camera.

## Demo accounts

| Email | Role | Password |
|---|---|---|
| host@demo.test | Host; can create webinars | StudyDemo123! |
| panelist@demo.test | Panelist; can join | StudyDemo123! |
| attendee@demo.test | Attendee; can join | StudyDemo123! |

These are intentionally public demo credentials for local experiments, not personal accounts. Existing name, email, bio, and role are stored in SQLite. Profile editing/submission is not implemented. Roles are account-wide in this simplified model; panelists and attendees currently have the same room permissions.

## Try it

1. Sign in as host. Create a webinar or join **The research room**.
2. Open an incognito window or another browser; sign in as attendee. Ordinary tabs share a login cookie, so use separate browser sessions for different accounts.
3. Join the same room. Both names should appear in the participant list.
4. Enable camera or microphone using the buttons. Grant the browser permission. Use headphones to avoid feedback.
5. Disable media or leave. Other participants disappear after leave, or after roughly 30 seconds if their browser disconnects.

Media is real browser-to-browser WebRTC, not a simulated camera tile. This initial configuration has **no STUN/TURN servers**, and is intended for two browser sessions on the same computer. Cross-device and internet calls are not guaranteed. Camera/microphone access requires localhost or HTTPS. Remote deployment would additionally require secure hosting, ICE server configuration, and production hardening. No recordings are made. The signaling service stores short-lived connection metadata, cleaned up during polling; it does not store media.

Rooms are capped at four participant connections, including duplicate browser sessions. Blank video tiles are normal until media is enabled. WebRTC may be blocked by browser settings, network restrictions, or a camera already in use.

## Tests

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Linux:

```bash
.venv/bin/python -m pytest -q
```

22 backend tests passed during creation. JavaScript passed `node --check static/app.js`. Automated tests cover login, profiles, roles, webinar creation/listing, joins, capacity, signaling isolation, leave, logout, and cross-site write rejection. **Real camera/microphone exchange and visual browser QA have not been verified in the build environment.** Perform the two-browser check above before freezing this baseline. Backend tests do not establish audiovisual quality.

## Files

- `app.py`: application factory, database initialization, authentication, webinar and signaling API.
- `templates/index.html`: interface.
- `static/app.js`: UI and peer-to-peer media handling.
- `static/style.css`: responsive interface styles.
- `tests/test_baseline.py`: development/regression tests, visible to the agent.
- `STUDY_PROTOCOL.md`: boundaries and experimental workflow.
- `BASELINE_SHA256.json`: source checksums at packaging time.

The first run creates `instance/webinar.sqlite`. Stop the server and delete that file to reset local records; the next start restores the three accounts and one seed room. Server restarts invalidate logins unless you set a stable `SECRET_KEY` environment variable. Each experimental run should use a fresh database.

## Sources

- https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Signaling_and_video_calling
- https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia

This is an experimental prototype, not a production conferencing service.
