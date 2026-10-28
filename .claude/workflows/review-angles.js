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
const SKILL = { resume: 'resume-review', cover_letter: 'cover-letter-review' }
// The readability reviewer must not know the evidence: insiders cannot see their own jargon.
const COLD = 'You are a cold reader. Read ONLY the rendered resume artifact and the frozen job text in inputs/; ' +
  'never open evidence, registry, sources, notes, projection or requirements. ' +
  'For each summary sentence and bullet, restate in one plain sentence what was done and why it matters. Report terms you ' +
  'cannot explain from general engineering knowledge or the JD, mechanism before outcome, several independent contributions ' +
  'in one bullet, and bullets past two lines; medium when the core point is lost, low otherwise. Repairs replace or drop ' +
  'insider terms, they never add explanations. Do not judge factual support. '

phase('Coverage')
const coverage = await agent(
  `${shell}Run exactly: ${status}\nReturn as todo every angle key (like "resume.factual") whose state is missing or stale. Run nothing else.`,
  { phase: 'Coverage', schema: COVERAGE, model: 'haiku', effort: 'low' })
const todo = coverage ? coverage.todo : []
log(todo.length ? `${todo.length} angle(s) need a reviewer: ${todo.join(', ')}` : 'every required angle already has a current verdict')

phase('Review')
const results = await parallel(todo.map(key => () => {
  const [document, angle] = key.split('.')
  const findings = bundle.replace(/bundle\.json$/, `review-${document}-${angle}.md`)
  return agent(
    `You are an independent reviewer: you did not write these documents. Use the ${SKILL[document]} skill, ` +
    `but review ONLY its "${angle}" angle for the ${document.replace('_', ' ')} of the revision ${bundle} ` +
    `in the workspace ${workspace}. ` + (angle === 'readability' ? COLD :
    `Read review-packet.md and the frozen inputs/ beside that bundle, and the exact rendered artifacts it lists`) + `${angle === 'visual' ? '; inspect every PDF page image with a visual tool, and if none is available your verdict is unavailable' : ''}.\n` +
    `${shell}Then record your verdict yourself, once:\n` +
    `- no concrete defect: ${cv} record-review --workspace '${workspace}' --bundle '${bundle}' --document ${document} --angle ${angle} --verdict pass --reviewer review-angles\n` +
    `- defects: write them (affected unit, evidence reference, severity, narrow repair) to ${findings} under the workspace, then the same command with --verdict findings --findings '${findings}'\n` +
    `- you could not review this angle (missing input or tool): the same command with --verdict unavailable, and say why in summary.\n` +
    `Never edit the documents, the evidence or the bundle. Never claim approval.`,
    { phase: 'Review', label: `review:${key}`, schema: RESULT, model })
}))
const done = results.filter(Boolean)
if (done.length < todo.length) log(`${todo.length - done.length} reviewer(s) returned nothing; their angles stay unrecorded`)

phase('Check')
const after = await agent(`${shell}Run exactly: ${status}\nReturn the angle keys whose state is not recorded. Run nothing else.`,
  { phase: 'Check', schema: COVERAGE, model: 'haiku', effort: 'low' })
// An empty check result means unknown coverage, not "nothing recorded".
return { reviewed: done, not_recorded: after ? after.todo : 'unknown: run cv review-status',
         review_status: 'unreviewed_preview', release_available: false }
