# Browser research and job queue

Use this when postings sit behind a login wall (LinkedIn, SEEK) and the owner can give a signed-in browser. Everything here is read-only discovery; the rules in `SKILL.md` still govern fit, eligibility and handoff.

## Access
- Fetching these sites directly usually fails (HTTP 429/403). Use Claude in Chrome, in the owner's own signed-in Chrome, in a new tab. Close every tab you opened before finishing.
- If the browser is not signed in or the extension is not connected, say so and ask the owner. Never log in, enter credentials, solve a CAPTCHA or bypass a wall.
- Read only. Do not click Apply, Easy Apply, Save, Follow, Message or Connect, and do not change filters that write to the account (job alerts). Work at human pace; after 2–3 failures of the same step, stop and report.

## Search
- Prefer URL parameters over typed locations. A free-text `location=` is often overridden by the account's default country, so confirm the location label on the results and redo the search if it is wrong. LinkedIn: `/jobs/search/?keywords=…&geoId=<country id>` (Australia `101452733`), `f_WT=2` remote, `f_E=4` mid-senior.
- The results list reads best with `get_page_text` after waiting 8–9 seconds; an empty result means it has not rendered, so wait and retry. The list gives title, company, place, pay badge and viewed/saved marks.
- Cards carry no job links. Click a card (find it first: references go stale after a click, so find and click in separate steps), then read `currentJobId` from the tab URL and open `/jobs/view/<id>`. Do not print URLs that carry query strings; the tool blocks them.
- Expand the description with the "… plus" button, then read the page text in slices of about 900 characters; long tool output is cut. Read the whole description, including security, work-rights and language lines, before judging fit.
- The pay badge can differ from the description. Quote the description's figure and say which source it came from; a missing salary is unknown.

## SEEK
- SEEK also works through the signed-in browser. Search pages use readable paths: `/<keywords>-jobs/in-<City>-<STATE>` and `/<keywords>-jobs/remote`. Results are `article` elements; read each card's job id from its `/job/<id>` link in page script and print short lines (id, title, company, place) in slices, because long tool output is cut.
- Job pages (`/job/<id>`) return the full text with `get_page_text` after about 3 seconds, including the pay band when the employer shows one, the work arrangement and the employer's screening questions. Record those questions; they show what the form will ask (work rights, notice, licence, salary).
- SEEK flags roles the owner already applied to or saved in the list; still check the workspace folders. Banners such as "Strong applicant" are the board's estimate, not evidence.
- Ads that say "citizens only", name a clearance, or require a stated number of years in a regulated domain are hard conflicts; record the line that decides it.

## Filters, in order
1. Already applied: compare against the workspace's application folders and records. Viewed or saved on the board is not applied. When a posting may be a new requisition from a company already applied to, list it as a question instead of dropping it silently.
2. Hard eligibility: clearance, citizenship, permanent-residency or work-rights wording the evidence does not meet. Check the exact visa status on record (a temporary or bridging visa with work rights is not permanent residency). If the owner is unsure, mark it conditional and ask once; a posting that says clearance "may be required later" is a flag, not a drop.
3. Owner-declared exclusions, for example a language or stack they have no experience in. Dropping these is the owner's stated preference, not a judgement about ability.
4. Level, then domain focus the owner named, then pay.

## Queue
Give a ranked list; each entry has the direct job link, one line on why it was prioritised (the specific evidence that gives an edge), the main gap, eligibility conditions and where the pay figure came from. Say how many postings were read in full and which were only seen in a list. Only roles the owner selects are frozen with `cv create-application`.
