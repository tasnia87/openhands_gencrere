# Experimental baseline and scope

## Baseline behaviors

| Concept | Existing behavior |
|---|---|
| Accounts | Three seeded accounts with hashed passwords |
| Profiles | Fixed name, email, bio, and global role attached to each account |
| Authentication | Password login with server-signed session cookie |
| Webinars | Hosts create rooms; authenticated users list rooms |
| Roles | Host, panelist, attendee; only hosts create rooms |
| Joining | Authenticated users join any existing room, up to four connections |
| Media | Optional camera/microphone and local peer-to-peer signaling |
| Leaving | Explicit leave or 30-second heartbeat expiry |

## Candidate generated requirements: baseline overlap audit

The exact final three experimental requirements have not been confirmed. The following audit covers examples previously supplied and should be checked against the selected wording before running the study.

| Candidate feature | Baseline status |
|---|---|
| Notify panelists/users; view, save, share information | Not implemented |
| Block attendees according to authentication criteria | Not implemented as a configurable blocking feature; basic login is required |
| Submit profile when joining a webinar | Not implemented; a preexisting profile is read, not submitted during joining |
| Block profiles associated with email addresses | Not implemented |
| Configure attendees without sign-in | Not implemented; unauthenticated joins are rejected |
| Configure which attendees can view/save/share information | Not implemented |

Login and capacity limits already reject some joins. Do not count these as novel implementation of an ambiguous blocking requirement. Define expected behavior before judging a change. Roles and profiles already exist as supporting concepts.

## Freeze and run

1. Review the code and run development tests and the manual two-browser smoke check in README.md.
2. Choose and record the three verbatim GENCRE-RE requirements. Independently define expected behavior, ambiguity rules, and evaluation tests before seeing agent output.
3. Initialize a Git repository and commit/tag the reviewed baseline (for example `baseline-v1`). Record the actual commit SHA, dependency versions, Python version, agent/model version, prompt, limits, and seed if available. The supplied checksums detect file changes but are not a substitute for a Git commit.
4. Start each task from a fresh copy of that commit and a fresh SQLite database. Do not chain implementations unless cumulative work is part of the experimental design.
5. Give OpenHands the application and development tests. A starting prompt is:

   > Implement the following requirement in this application: [verbatim requirement]. Preserve existing functionality. Run the development tests and summarize your changes and test results.

6. Keep independent evaluation tests outside the agent's accessible workspace. None are included here: `tests/` contains development tests only.
7. Save full trajectories, patches, test results, elapsed time, tool calls, model usage/cost, and every human clarification or intervention. Use the same intervention policy across conditions.
8. Evaluate the final patch on a separate copy with your independent tests. Report implementation success, regressions, partial fulfillment, and ambiguity separately.

This artifact supplies infrastructure, not evidence that generated requirements are implementable or that a particular agent performs well. Video transport is ancillary to the requirement implementation experiment. Results from this small purpose-built application have limited generalizability.
