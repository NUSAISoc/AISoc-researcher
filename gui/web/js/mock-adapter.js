// Mock adapter: placeholder data for design work and review.
//
// Same interface as js/http-adapter.js:
//   load()                               -> Promise<overview read model>
//   sendCommand(resource, action, body)  -> Promise<{ ok: true, operation } | { ok: false, status, message }>
//   subscribe({ onChange, onConnection }) (no-op here)
//
// Used when the page is opened from disk or with ?adapter=mock. Nothing here is real data.
(function () {
  const params = new URLSearchParams(location.search);
  // Preview states for design review: ?state=loading|stale|disconnected|new
  const previewState = params.get('state') || 'live';

  const data = {
    project: {
      researchQuestion: 'Do structured hints improve novice debugging performance compared with unstructured hints?',
      stage: 'Experiment campaigns',
      modelTraffic: { mode: 'provider', provider: 'provider-a', limitUsedPct: 80 },
      data: { hasData: true, anonymisedOnly: true },
      asOf: '14:08',
      lastKnown: '14:03'
    },

    pipeline: [
      { stage: 'Evidence', icon: 'book', counts: [['read', 42], ['unread', 8], ['contradicted', 3, 'bad']] },
      { stage: 'Opportunities', icon: 'bulb', counts: [['proposed', 5], ['approved', 2], ['rejected', 3]] },
      { stage: 'Campaigns', icon: 'flask', counts: [['active', 1], ['blocked', 1], ['done', 1]] },
      { stage: 'Runs', icon: 'play', counts: [['ok', 12], ['failed', 2, 'bad'], ['inconclusive', 1], ['running', 1]] },
      { stage: 'Findings', icon: 'chart', counts: [['verified', 1], ['to review', 2], ['rejected', 1]] }
    ],

    // Work items: decisions, problems, and runs.
    // urgency fields (paused, blocks, waitingHours) must come from the contract, not the UI.
    work: [
      { id: 'D-METRIC', version: 1, status: 'decision', type: 'doc change', title: 'Rename outcome metric in docs/05', ids: 'C2 · s5',
        summary: 'Waiting 3 h', urgency: { paused: false, blocks: 0, waitingHours: 3 },
        experiment: ['C2', 'docs/05'], agent: ['proposed by s5', 'codex', 'egress #3'],
        details: [['What changes', "'accuracy' → 'task success rate'"], ['Sync targets', 'docs/07, ProjectProposal, report']],
        actions: ['review'], links: ['Diff'] },
      { id: 'D-EGRESS', version: 4, status: 'decision', type: 'egress', title: 'Model traffic limit 80% used', ids: 'egress #3',
        summary: 'Agent s4 paused until you decide', urgency: { paused: true, blocks: 2, waitingHours: 1 },
        experiment: ['project-wide'], agent: ['s4', 'claude-code', 'egress #3'],
        details: [['Used', '80% of approved limit'], ['Paused', 's4 (R19, R20 waiting)']],
        actions: ['review'], links: ['Usage'] },
      { id: 'D-PROTO', version: 2, status: 'decision', type: 'protocol', title: 'Approve protocol v3 for campaign C2', ids: 'C2 · s4',
        summary: 'Waiting 2 days · blocks 3 runs', urgency: { paused: false, blocks: 3, waitingHours: 48 },
        experiment: ['C2', 'H1', 'protocol v2 → v3'], agent: ['proposed by s4', 'claude-code', 'egress #3'],
        details: [['What changes', 'Sample 20 → 40 per condition'], ['Uncertainty', 'Not yet checked against analysis plan']],
        actions: ['review'], links: ['Protocol diff'] },
      { id: 'R17', resource: 'runs/R17', version: 1, status: 'inconclusive', title: 'Run R17 result unclear', ids: 'C2 · s5',
        summary: 'Effect interval crosses zero', urgency: { paused: false, blocks: 0, waitingHours: 5 },
        experiment: ['C2', 'H1', 'protocol v2', 'synthetic'], agent: ['s5', 'codex', 'model-y', 'egress #3'],
        details: [['Outcome', '95% interval includes zero'], ['Mode', 'synthetic, not reportable']],
        actions: ['review'], links: ['Evidence', 'Log'] },
      { id: 'R14', resource: 'runs/R14', version: 3, status: 'failed', title: 'Run R14 timed out', ids: 'C2 · s4',
        summary: 'After 30 min · blocks C2', urgency: { paused: false, blocks: 1, waitingHours: 1 },
        experiment: ['C2', 'H1', 'protocol v2', 'live'], agent: ['s4', 'claude-code', 'model-x', 'egress #3'],
        details: [['Outcome', 'timeout, 0 of 8 units'], ['Ledger row', '…-live-9c1e']],
        actions: ['rerun'], links: ['Log'] },
      { id: 'R09', resource: 'runs/R09', version: 1, status: 'failed', title: 'Run R09 crashed', ids: 'C1 · s2',
        summary: 'ImportError in sandbox', urgency: { paused: false, blocks: 0, waitingHours: 20 },
        experiment: ['C1', 'H2', 'protocol v1', 'synthetic'], agent: ['s2', 'claude-code', 'model-x', 'egress #2'],
        details: [['Outcome', 'error before first unit'], ['Ledger row', '…-synthetic-07aa']],
        actions: ['rerun'], links: ['Log'] },
      { id: 'C3', version: 1, status: 'blocked', title: 'Campaign C3 waiting', ids: 'C3',
        summary: 'Needs protocol approval first', urgency: { paused: false, blocks: 0, waitingHours: 24 },
        experiment: ['C3', 'H3'], agent: ['none assigned'],
        details: [['Blocked by', 'C2 protocol v3 decision']], actions: [], links: ['Open C2'] },
      { id: 'R18', resource: 'runs/R18', version: 5, status: 'running', title: 'Run R18', ids: 'C2 · s4',
        summary: '5 of 8 units recorded', urgency: { paused: false, blocks: 0, waitingHours: 0 },
        experiment: ['C2', 'H2', 'protocol v2', 'synthetic'], agent: ['s4', 'claude-code', 'model-x', 'egress #3'],
        details: [['Started', '14:02 · 6 min elapsed']], actions: ['pause', 'stop'], links: ['Live log'] },
      { id: 'R11', resource: 'runs/R11', version: 2, status: 'ok', title: 'Run R11 completed', ids: 'C1 · s2',
        summary: 'Recorded 40 of 40 units', urgency: { paused: false, blocks: 0, waitingHours: 0 },
        experiment: ['C1', 'H2', 'protocol v1', 'live'], agent: ['s2', 'claude-code', 'model-x', 'egress #2'],
        details: [['Outcome', 'completed, finding F2 inferred']], actions: [], links: ['Evidence'] }
    ],

    // Findings. verification: unverified | recheck | verified | rejected.
    // unverified and recheck need the researcher, so the UI lists them under "Needs your decision".
    findings: [
      { id: 'F4', version: 1, verification: 'unverified', claim: 'Larger effect for novices than intermediates',
        effect: 'Inferred effect: larger for novices, direction uncertain', uncertainty: 'interval crosses zero · n = 16 · C2 · R17',
        synthetic: true, ids: 'C2 · s5', waitingHours: 1,
        inferredBy: { session: 's5', agent: 'codex', model: 'model-y', at: 'today 13:10' }, links: ['Evidence'] },
      { id: 'F1', version: 3, verification: 'recheck', claim: 'Structured hints reduce time-to-fix vs control',
        effect: 'Inferred effect: faster with structured hints', uncertainty: 'd = 0.41, 95% CI 0.08 to 0.74 · n = 40 · C1 · R06, R07',
        ids: 'C1 · s4', waitingHours: 26,
        inferredBy: { session: 's4', agent: 'claude-code', model: 'model-x', at: '25 Sep' },
        reviewedBy: { verb: 'Verified', name: 'researcher-1 (you)', at: '26 Sep', rationale: 'Matches pre-registered rule for H1' },
        recheckReason: 'Evidence changed since verification: R07 log amended 27 Sep', links: ['What changed', 'Evidence'] },
      { id: 'F2', version: 1, verification: 'verified', claim: 'Hint timing makes no meaningful difference to final accuracy',
        effect: 'Inferred effect: no meaningful difference (effects above ±0.1 ruled out)', uncertainty: 'diff 0.01, 95% CI −0.09 to 0.11 · n = 40 · C1 · R11',
        inferredBy: { session: 's2', agent: 'claude-code', model: 'model-x', at: '24 Sep' },
        reviewedBy: { verb: 'Verified', name: 'researcher-1 (you)', at: '24 Sep', rationale: 'Interval within pre-registered equivalence bounds' },
        links: ['Evidence', 'Runs'] },
      { id: 'F0', version: 1, verification: 'rejected', claim: 'Hints improve long-term retention',
        effect: 'Inferred effect: better retention after one week', uncertainty: 'n = 6 · C1 · R03',
        inferredBy: { session: 's2', agent: 'claude-code', model: 'model-x', at: '20 Sep' },
        reviewedBy: { verb: 'Rejected', name: 'researcher-1 (you)', at: '21 Sep', rationale: 'Retention was not measured in protocol v1; inference goes beyond the data' },
        links: ['Evidence'] }
    ],

    // Recent actions (audit excerpt). actor.kind: human | agent | system
    actions: [
      { at: '14:08', actor: { kind: 'system', name: 'system' }, what: 'Agent s4 paused', context: 'model traffic limit reached 80%' },
      { at: '13:40', actor: { kind: 'human', name: 'researcher-1 (you)' }, what: 'Approved opportunity O5', rationale: 'Clear gap in novice studies, feasible in 2 weeks' },
      { at: '13:32', actor: { kind: 'agent', name: 's4' }, what: 'Started run R14', context: 'campaign C2, live' },
      { at: '13:10', actor: { kind: 'agent', name: 's5' }, what: 'Inferred finding F4', context: 'from R17, synthetic' },
      { at: '11:15', actor: { kind: 'human', name: 'researcher-1 (you)' }, what: 'Rejected opportunity O4', rationale: 'Duplicates Smith 2023, no new mechanism' }
    ]
  };

  let seq = 0;
  const clone = (x) => JSON.parse(JSON.stringify(x));
  const fail = (status, message) => Promise.resolve({ ok: false, status, message });

  window.AisocMockAdapter = {
    actor: { id: 'researcher-1', display: 'researcher-1 (you)' },

    load() {
      if (previewState === 'loading') return new Promise(() => {}); // stays loading
      const view = clone(data);
      view.schemaVersion = 1;
      if (previewState === 'new') {
        view.project.researchQuestion = null;
        view.project.stage = 'Setup';
        view.project.modelTraffic = { mode: 'local' };
        view.project.data = { hasData: false };
        view.pipeline.forEach((p) => p.counts.forEach((c) => { c[1] = 0; }));
        view.work = []; view.findings = []; view.actions = [];
      }
      view.connection = previewState === 'stale' ? 'stale'
        : previewState === 'disconnected' ? 'disconnected' : 'live';
      return view;
    },

    // Same rules as the server: rationale, expected version and request id are required.
    // The mock records the request and returns an operation that is not done; it never marks work as done.
    sendCommand(resource, action, body) {
      if (previewState === 'disconnected') return fail('DISCONNECTED', "can't reach the dashboard server");
      if (!body || !body.rationale || !String(body.rationale).trim()) return fail('RATIONALE_REQUIRED', 'a rationale is required');
      const item = data.work.find((w) => w.resource === resource);
      if (!item) return fail('NOT_FOUND', 'unknown target');
      if (item.version !== body.expectedVersion) return fail('VERSION_CONFLICT', 'the item changed since you loaded it');
      const op = {
        name: 'operations/op-' + (++seq), done: false,
        metadata: { command: resource + ':' + action, actor: this.actor.id, requestedAt: new Date().toISOString() }
      };
      item.pendingOperation = { name: op.name, done: false, command: op.metadata.command };
      data.actions.unshift({
        at: new Date().toTimeString().slice(0, 5),
        actor: { kind: 'human', name: this.actor.display },
        what: 'Requested ' + action + ' of ' + item.id,
        rationale: String(body.rationale).trim()
      });
      return Promise.resolve({ ok: true, operation: op });
    },

    subscribe() { /* the mock never changes on its own */ }
  };
})();
