export const meta = {
  name: 'review-angles',
  description: 'Dispatch one independent reviewer per missing or stale review angle of a built revision and record each verdict',
  whenToUse: 'After cv build-application, from the application-materials workflow on Claude Code. args: {cv, workspace, bundle, model?}',
  phases: [
    { title: 'Coverage', detail: 'cv review-status lists the angles still needing a verdict', model: 'haiku' },
    { title: 'Review', detail: 'one fresh reviewer per angle, recording its verdict with cv record-review', model: 'sonnet' },
    { title: 'Check', detail: 'cv review-status again; every angle not recorded is reported', model: 'haiku' },
  ],
}

// args.cv: the pinned command prefix, e.g. "& 'C:\\proj\\.venv\\Scripts\\python.exe' -m cv_toolkit.cli"
// args.model: optional reviewer model; the status agents only run one command, so they stay on haiku.
const { cv, workspace, bundle, model = 'sonnet' } = args || {}
if (!cv || !workspace || !bundle) throw new Error('review-angles needs args {cv, workspace, bundle}')
// A prefix starting with "& " is PowerShell syntax; Bash rejects it.
const shell = cv.startsWith('&') ? 'Run every cv command below with the PowerShell tool, never Bash. ' : ''
const status = `${cv} review-status --workspace '${workspace}' --bundle '${bundle}'`

const COVERAGE = {
  type: 'object',
  properties: { todo: { type: 'array', items: { type: 'string' } } },
  required: ['todo'],
}
const RESULT = {
  type: 'object',
  properties: {
    angle: { type: 'string' },
    verdict: { type: 'string', enum: ['pass', 'findings', 'unavailable'] },
    recorded: { type: 'boolean' },
    summary: { type: 'string' },
  },
  required: ['angle', 'verdict', 'recorded', 'summary'],
}
// The reviewer briefs live in the toolkit (cv review-plan), so Claude Code and Codex review alike.
const plan = (angle) => `${cv} review-plan --workspace '${workspace}' --bundle '${bundle}' --command "${cv}"` + (angle ? ` --angle ${angle}` : '')

phase('Coverage')
const coverage = await agent(
  `${shell}Run exactly: ${plan()}\nReturn its todo list of angle keys (like "resume.factual") unchanged. Run nothing else.`,
  { phase: 'Coverage', schema: COVERAGE, model: 'haiku', effort: 'low' })
const todo = coverage ? coverage.todo : []
log(todo.length ? `${todo.length} angle(s) need a reviewer: ${todo.join(', ')}` : 'every required angle already has a current verdict')

phase('Review')
const results = await parallel(todo.map(key => () => agent(
  `${shell}Run exactly: ${plan(key)}\n` +
  `It prints JSON; briefs["${key}"] is your complete task. Follow that brief exactly, as an independent reviewer ` +
  `of the ${key} angle only, and record your verdict once as it says. Return the angle key, your verdict, whether ` +
  `the record-review command succeeded, and a one-line summary.`,
  { phase: 'Review', label: `review:${key}`, schema: RESULT, model })))
const done = results.filter(Boolean)
if (done.length < todo.length) log(`${todo.length - done.length} reviewer(s) returned nothing; their angles stay unrecorded`)

phase('Check')
const after = await agent(`${shell}Run exactly: ${status}\nReturn the angle keys whose state is not recorded. Run nothing else.`,
  { phase: 'Check', schema: COVERAGE, model: 'haiku', effort: 'low' })
// An empty check result means unknown coverage, not "nothing recorded".
return { reviewed: done, not_recorded: after ? after.todo : 'unknown: run cv review-status',
         review_status: 'unreviewed_preview', release_available: false }
