export const meta = {
  name: 'review-angles',
  description: 'Dispatch one independent reviewer per missing or stale review angle of a built revision and record each verdict',
  whenToUse: 'After cv build-application, from the application-materials workflow on Claude Code. args: {cv, workspace, bundle}',
  phases: [
    { title: 'Coverage', detail: 'cv review-status lists the angles still needing a verdict' },
    { title: 'Review', detail: 'one fresh reviewer per angle, recording its verdict with cv record-review' },
    { title: 'Check', detail: 'cv review-status again; every angle not recorded is reported' },
  ],
}

// args.cv: the pinned command prefix, e.g. "& 'C:\\proj\\.venv\\Scripts\\python.exe' -m cv_toolkit.cli"
const { cv, workspace, bundle } = args || {}
if (!cv || !workspace || !bundle) throw new Error('review-angles needs args {cv, workspace, bundle}')
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

phase('Coverage')
const coverage = await agent(
  `Run exactly: ${status}\nReturn as todo every angle key (like "resume.factual") whose state is missing or stale. Run nothing else.`,
  { phase: 'Coverage', schema: COVERAGE, effort: 'low' })
const todo = coverage ? coverage.todo : []
log(todo.length ? `${todo.length} angle(s) need a reviewer: ${todo.join(', ')}` : 'every required angle already has a current verdict')

phase('Review')
const results = await parallel(todo.map(key => () => {
  const [document, angle] = key.split('.')
  const findings = bundle.replace(/bundle\.json$/, `review-${document}-${angle}.md`)
  return agent(
    `You are an independent reviewer: you did not write these documents. Use the ${SKILL[document]} skill, ` +
    `but review ONLY its "${angle}" angle for the ${document.replace('_', ' ')} of the revision ${bundle} ` +
    `in the workspace ${workspace}. Read review-packet.md and the frozen inputs/ beside that bundle, and the exact ` +
    `rendered artifacts it lists${angle === 'visual' ? '; inspect every PDF page image with a visual tool, and if none is available your verdict is unavailable' : ''}.\n` +
    `Then record your verdict yourself, once:\n` +
    `- no concrete defect: ${cv} record-review --workspace '${workspace}' --bundle '${bundle}' --document ${document} --angle ${angle} --verdict pass --reviewer review-angles\n` +
    `- defects: write them (affected unit, evidence reference, severity, narrow repair) to ${findings} under the workspace, then the same command with --verdict findings --findings '${findings}'\n` +
    `- you could not review this angle (missing input or tool): the same command with --verdict unavailable, and say why in summary.\n` +
    `Never edit the documents, the evidence or the bundle. Never claim approval.`,
    { phase: 'Review', label: `review:${key}`, schema: RESULT })
}))
const done = results.filter(Boolean)
if (done.length < todo.length) log(`${todo.length - done.length} reviewer(s) returned nothing; their angles stay unrecorded`)

phase('Check')
const after = await agent(`Run exactly: ${status}\nReturn the angle keys whose state is not recorded. Run nothing else.`,
  { phase: 'Check', schema: COVERAGE, effort: 'low' })
return { reviewed: done, not_recorded: after ? after.todo : todo,
         review_status: 'unreviewed_preview', release_available: false }
