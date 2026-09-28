// Overview screen. Presentation only: reads the adapter's read model and sends commands.
(function () {
  // Adapter choice: the mock when opened from disk or with ?adapter=mock, otherwise the local server.
  const params = new URLSearchParams(location.search);
  const useMock = params.get('adapter') === 'mock' || location.protocol === 'file:' || !window.AisocHttpAdapter;
  const adapter = useMock ? window.AisocMockAdapter : window.AisocHttpAdapter;
  const $app = document.getElementById('app');

  // Status labels for work items. [label, abbreviation or null, icon, css class]
  const STATUS = {
    decision: ['decision', null, 'alertCircle', 's-dec'],
    failed: ['failed', null, 'x', 's-fail'],
    inconclusive: ['inconclusive', 'inconcl.', 'help', 's-inc'],
    blocked: ['blocked', null, 'lock', 's-blk'],
    running: ['running', null, 'loader', 's-run'],
    ok: ['ok', null, 'check', 's-ok']
  };
  const ORDER = ['decision', 'failed', 'inconclusive', 'blocked', 'running', 'ok'];
  const SECTIONS = [
    { key: 'decisions', name: 'Needs your decision', statuses: ['decision'], decision: true },
    { key: 'problems', name: 'Problems', statuses: ['failed', 'inconclusive', 'blocked'] },
    { key: 'progress', name: 'In progress and recent', statuses: ['running', 'ok'] }
  ];
  const VERIFY = {
    unverified: ['unverified', 'help', 'v-unv'],
    recheck: ['re-check', 'recheck', 'v-rec'],
    verified: ['verified', 'check', 'v-ver'],
    rejected: ['rejected', 'x', 'v-rej']
  };

  // Display-only state. Safe to lose (never research state).
  const ui = { active: new Set(ORDER), menuOpen: false, detailed: false, open: new Set(), sideOpen: false, collapsed: new Set() };
  // Elements that just appeared because of the last interaction. They get the class "is-fresh",
  // which only css/motion.css uses (for subtle entry animations). Cleared after every render.
  const fresh = new Set();
  const fr = (key) => (fresh.has(key) ? ' is-fresh' : '');
  try { ui.detailed = localStorage.getItem('aisoc.detailed') === '1'; } catch (e) { /* storage unavailable */ }

  // Everything from the read model is untrusted (agents write it), so escape it.
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // Markers from the read model: a value with no source, or a source that could not be read.
  const isNT = (x) => !!x && typeof x === 'object' && x.tracked === false;
  const isUN = (x) => !!x && typeof x === 'object' && x.available === false;
  const arr = (x) => (Array.isArray(x) ? x : []);
  const NT_TEXT = '<span class="muted">not tracked yet</span>';
  const unText = (x) => '<span class="c-warn">couldn\'t read: ' + esc(x.reason) + '</span>';
  // Only same-origin paths from the read model become real links; anything else is ignored.
  const safeHref = (h) => (typeof h === 'string' && /^\/(?!\/)/.test(h) ? h : null);

  // ---------- derived view ----------
  // Findings that still need the researcher are shown as decisions with a "finding" type label.
  function findingAsWork(f) {
    const who = f.inferredBy;
    const details = [['Inferred effect', f.effect.replace(/^Inferred effect: /, '')], ['Uncertainty', f.uncertainty]];
    if (f.recheckReason) details.push(['Why re-check', f.recheckReason]);
    if (f.reviewedBy) details.push(['Previously', f.reviewedBy.verb + ' by ' + f.reviewedBy.name + ', ' + f.reviewedBy.at]);
    return {
      id: f.id, version: f.version, status: 'decision', type: 'finding', verification: f.verification,
      title: (f.verification === 'recheck' ? 'Re-check finding: ' : 'Verify finding: ') + f.claim,
      ids: f.ids, summary: f.verification === 'recheck' ? f.recheckReason : 'Inferred by agent ' + who.session + ' · not yet verified',
      synthetic: f.synthetic,
      urgency: { paused: false, blocks: 0, waitingHours: f.waitingHours || 0 },
      experiment: [f.uncertainty.split(' · ').slice(-2).join(' · ')], agent: ['inferred by ' + who.session, who.agent, who.model],
      details, actions: ['review'], links: f.links
    };
  }

  const isUrgent = (i) => i.urgency.paused || i.urgency.blocks > 0;
  const score = (i) => (isUrgent(i) ? 1e6 : 0) + (i.urgency.paused ? 5e5 : 0) + i.urgency.blocks * 1e3 + i.urgency.waitingHours;

  // ---------- small render helpers ----------
  function statusTag(status) {
    const [label, abbr, ic, cls] = STATUS[status];
    const text = abbr ? '<abbr title="' + label + '" aria-label="' + label + '">' + abbr + '</abbr>' : label;
    return '<span class="tag ' + cls + '">' + icon(ic) + '<span class="tx">' + text + '</span></span>';
  }
  function verifyTag(v) {
    const [label, ic, cls] = VERIFY[v];
    return '<span class="tag ' + cls + '">' + icon(ic) + '<span class="tx">' + label + '</span></span>';
  }
  // Links are plain labels (screens not built yet) or { label, href } for real same-origin targets.
  function links(list, target) {
    if (!list || !list.length) return '';
    return '<div class="links">' + list.map((l) => {
      const label = typeof l === 'string' ? l : l.label;
      const href = typeof l === 'string' ? null : safeHref(l.href);
      return href
        ? '<a href="' + esc(href) + '" target="_blank" rel="noopener">' + esc(label) + '</a>'
        : '<a href="#" data-action="link" data-target="' + esc(target) + '" data-link="' + esc(label) + '">' + esc(label) + '</a>';
    }).join('<span class="sep" aria-hidden="true">·</span>') + icon('chevronRight', 'cv') + '</div>';
  }
  // Buttons appear only for actions the read model lists. Commands need the item's resource path.
  function actionButtons(item) {
    const b = [];
    arr(item.actions).forEach((a) => {
      const common = ' data-id="' + esc(item.id) + '" data-version="' + esc(item.version) + '"';
      const cmd = item.resource ? common + ' data-res="' + esc(item.resource) + '" data-cmd="' + a + '"' : null;
      if (a === 'review') b.push('<button class="btn btn-primary" data-action="review"' + common + '>Review' + icon('chevronRight') + '</button>');
      if (!cmd) return;
      if (a === 'rerun') b.push('<button class="btn btn-secondary" data-action="cmd"' + cmd + '>' + icon('refresh') + 'Rerun</button>');
      if (a === 'pause') b.push('<button class="btn btn-secondary" data-action="cmd"' + cmd + '>' + icon('pause') + 'Pause</button>');
      if (a === 'resume') b.push('<button class="btn btn-secondary" data-action="cmd"' + cmd + '>' + icon('play') + 'Resume</button>');
      if (a === 'stop') b.push('<button class="btn btn-danger" data-action="cmd"' + cmd + '>Stop</button>');
    });
    return b.length ? '<div class="btns">' + b.join('') + '</div>' : '';
  }
  const VERB = { rerun: 'Rerun', pause: 'Pause', resume: 'Resume', stop: 'Stop' };
  function pendingText(op) {
    const action = String(op.command || '').split(':').pop();
    return (VERB[action] || 'Command') + ' requested · waiting for control plane';
  }
  const metaLine = (ic, label, parts) => '<div class="meta">' + icon(ic) + '<span class="k tx">' + label + '</span>' +
    parts.map((p) => '<code class="tx">' + esc(p) + '</code>').join('<span class="d" aria-hidden="true">·</span>') + '</div>';
  const skeleton = (w) => '<span class="sk" style="width:' + w + 'px"></span>';

  // Keep the chevron on the same line as the last word, so it never wraps onto a line by itself.
  function titleWithChevron(title) {
    const t = String(title), cut = t.lastIndexOf(' ');
    const head = cut > 0 ? t.slice(0, cut + 1) : '', last = cut > 0 ? t.slice(cut + 1) : t;
    return (head ? '<b class="tx">' + esc(head) + '</b>' : '') +
      '<span class="nw"><b class="tx">' + esc(last) + '</b>' + icon('chevronDown', 'exp') + '</span>';
  }

  function workRow(item) {
    const open = ui.open.has(item.id);
    const typeLabel = item.type ? '<span class="type tx">' + (item.type === 'finding' ? icon('chart') : '') + esc(item.type) + '</span>' : '';
    return '<div class="item' + (open ? ' open' : '') + '">' +
      '<div class="row" tabindex="0" role="button" aria-expanded="' + open + '" data-row="' + esc(item.id) + '">' +
        // Status column. On phones the urgent marker moves here as an icon under the status icon.
        '<div class="tagcol">' + statusTag(item.status) +
          (isUrgent(item) ? '<span class="urg-ic" role="img" aria-label="urgent">' + icon('arrowUp') + '</span>' : '') +
        '</div>' +
        '<div class="t">' +
          typeLabel + titleWithChevron(item.title) +
          (isUrgent(item) ? '<span class="urg tx">' + icon('arrowUp') + 'urgent</span>' : '') +
          (item.synthetic ? '<span class="flag tx">' + icon('alertTriangle') + 'synthetic, not reportable</span>' : '') +
          '<span class="mini tx">' + esc(item.ids) + '</span><br>' +
          '<small class="tx">' + esc(item.summary) + '</small>' +
          (item.pendingOperation && !item.pendingOperation.done ? '<div class="pending tx' + fr('pending:' + item.id) + '">' + icon('clock') + esc(pendingText(item.pendingOperation)) + '</div>' : '') +
          metaLine('flask', 'Experiment', arr(item.experiment)) + metaLine('robot', 'Agent', arr(item.agent)) +
        '</div>' +
        '<div class="acts">' + actionButtons(item) + links(item.links, item.id) + '</div>' +
      '</div>' +
      '<div class="det"><div class="det-inner"><div class="det-body"><dl class="dg">' + arr(item.details).map(([k, v]) =>
        '<div><dt>' + esc(k) + '</dt><dd>' + esc(v) + '</dd></div>').join('') + '</dl></div></div></div>' +
    '</div>';
  }

  // ---------- sections ----------
  function renderHeader(v) {
    const L = v.connection === 'loading';
    const p = v.project || {};
    const lastKnown = p.lastKnown || (lastGood && lastGood.project && lastGood.project.asOf) || 'unknown';
    let rq;
    if (L) rq = skeleton(420);
    else if (isUN(p.researchQuestion)) rq = unText(p.researchQuestion);
    else if (!p.researchQuestion) rq = '<span class="muted">Not set yet. </span><a href="#" data-action="link" data-link="docs/03-research-question.md">Open docs/03-research-question.md</a>' + icon('chevronRight', 'cv');
    else rq = esc(p.researchQuestion);

    const mt = p.modelTraffic;
    let traffic;
    if (L) traffic = skeleton(140);
    else if (!mt || isNT(mt)) traffic = NT_TEXT;
    else if (mt.mode === 'local') traffic = 'Local only · no provider approved';
    else traffic = esc(mt.provider) + ' · ' + esc(mt.limitUsedPct) + '% of limit <span class="nw"><a href="#" data-action="link" data-link="Egress">Egress</a>' + icon('chevronRight', 'cv') + '</span>';

    const d = p.data;
    let data;
    if (L) data = skeleton(110);
    else if (!d || isNT(d)) data = NT_TEXT;
    else if (isUN(d)) data = unText(d);
    else if (d.anonymisedOnly) data = 'Anonymised only';
    else data = d.hasData ? 'Has data' : 'No data yet';

    let stage;
    if (L) stage = skeleton(110);
    else if (!p.stage || isNT(p.stage)) stage = NT_TEXT;
    else stage = esc(p.stage);

    let updated;
    if (L) updated = '<span class="muted">loading…</span>';
    else if (v.connection === 'stale') updated = '<span class="c-warn">' + esc(lastKnown) + ' · reconnecting</span>';
    else if (v.connection === 'disconnected') updated = '<span class="c-bad">last known ' + esc(lastKnown) + '</span>';
    else updated = esc(p.asOf) + ' · <span class="live">live</span>';

    const trafficIconClass = !L && mt && !isNT(mt) && mt.mode !== 'local' ? 'c-warn' : '';
    return '<section class="card hd" aria-label="Project">' +
      '<div class="rq"><span class="lbl">Research question</span><h1>' + rq + '</h1></div>' +
      '<div class="hg">' +
        '<div><span class="k">' + icon('flag') + 'Stage</span><div class="v">' + stage + '</div></div>' +
        '<div><span class="k"><span class="' + trafficIconClass + '">' + icon('world') + '</span>Model traffic</span><div class="v">' + traffic + '</div></div>' +
        '<div><span class="k">' + icon('shield') + 'Data</span><div class="v">' + data + '</div></div>' +
        '<div><span class="k">' + icon('clock') + 'Updated</span><div class="v mono">' + updated + '</div></div>' +
      '</div></section>';
  }

  function renderBanner(v) {
    const p = v.project || {};
    const lastKnown = p.lastKnown || (lastGood && lastGood.project && lastGood.project.asOf);
    if (v.connection === 'stale') return '<div class="banner warn" role="status">' + icon('clock') +
      '<div>Connection interrupted; the data may be out of date. Reconnecting. Decisions still check the latest version before they apply.</div></div>';
    if (v.connection === 'disconnected') return '<div class="banner bad" role="alert">' + icon('unplug') +
      '<div>Can\'t reach the dashboard server. ' + (lastKnown ? 'Showing the last known state from ' + esc(lastKnown) + '. ' : '') +
      'Actions are paused until the connection is back. <a href="#" data-action="retry">Retry now</a></div></div>';
    const warn = arr(v.warnings);
    if (warn.length) return '<div class="banner warn" role="status">' + icon('alertTriangle') + '<div>' + warn.map(esc).join('<br>') + '</div></div>';
    return '';
  }

  function renderPipeline(v) {
    const L = v.connection === 'loading';
    const stages = L ? [['Evidence', 'book'], ['Opportunities', 'bulb'], ['Campaigns', 'flask'], ['Runs', 'play'], ['Findings', 'chart']]
      .map(([s, i]) => ({ stage: s, icon: i, counts: [['', null], ['', null], ['', null]] })) : arr(v.pipeline);
    const count = (st, [label, n, tone]) => {
      if (L) return '<div class="pl">' + skeleton(60) + skeleton(14) + '</div>';
      if (isNT(n)) return '<div class="pl"><span class="nm">' + esc(label) + '</span><span class="n muted" title="not tracked yet" aria-label="not tracked yet">–</span></div>';
      return '<a href="#" class="pl" data-action="link" data-link="' + esc(st.stage + ' · ' + label) + '"><span class="nm">' + esc(label) +
        '</span><span class="n' + (tone === 'bad' && n ? ' c-bad' : '') + '">' + esc(n) + '</span></a>';
    };
    return '<section class="card pipe" aria-label="Pipeline">' + stages.map((st) =>
      '<div class="pc"><h2>' + icon(st.icon) + esc(st.stage) + '</h2>' +
        (st.tracked === false ? '<div class="pl pl-note">' + NT_TEXT + '</div>'
          : isUN(st) ? '<div class="pl pl-note">' + unText(st) + '</div>'
          : arr(st.counts).map((c) => count(st, c)).join('')) +
      '</div>').join('') + '</section>';
  }

  function renderWork(v) {
    const L = v.connection === 'loading';
    const pendingFindings = arr(v.findings).filter((f) => f.verification === 'unverified' || f.verification === 'recheck').map(findingAsWork);
    const items = L ? [] : arr(v.work).concat(pendingFindings);
    const count = (s) => items.filter((i) => i.status === s).length;
    const all = ui.active.size === ORDER.length;
    const hiddenDecisions = ui.active.has('decision') ? 0 : count('decision');

    let h = '<section aria-label="Work"><div class="toolbar"><h2 class="h">Work</h2><div class="ctl">' +
      '<div class="fw"><button class="fbtn' + (all ? '' : ' act') + '" data-action="filter" aria-haspopup="true" aria-expanded="' + ui.menuOpen + '">' +
        icon('filter') + 'Status: ' + (all ? 'all' : ui.active.size + ' of ' + ORDER.length) + '<span class="dot" aria-hidden="true"></span>' + icon('chevronDown') + '</button>' +
        '<div class="menu' + (ui.menuOpen ? ' open' : '') + fr('menu') + '" role="group" aria-label="Filter by status">' +
          ORDER.map((s) => '<label class="opt"><input type="checkbox" data-filter="' + s + '"' + (ui.active.has(s) ? ' checked' : '') + '>' +
            '<span class="swt ' + STATUS[s][3] + '"></span><span class="nm">' + STATUS[s][0] + '</span><span class="n">' + count(s) + '</span></label>').join('') +
          '<div class="mf"><button class="linkbtn" data-action="filter-all">Select all</button><button class="linkbtn" data-action="filter-none">Clear</button></div>' +
        '</div></div>' +
      '<button class="switch' + fr('switch') + '" role="switch" aria-checked="' + ui.detailed + '" data-action="detailed"><span>Detailed view</span><span class="tr" aria-hidden="true"><span class="th"></span></span></button>' +
    '</div></div>';

    if (hiddenDecisions) h += '<div class="note" role="status">' + icon('alertCircle') + hiddenDecisions + ' pending decision' + (hiddenDecisions === 1 ? '' : 's') + ' hidden by your filter</div>';

    if (L) return h + '<div class="box">' + [1, 2, 3].map(() => '<div class="row static">' + skeleton(82) + '<div>' + skeleton(260) + '<br>' + skeleton(160) + '</div>' + skeleton(78) + '</div>').join('') + '</div></section>';
    if (!items.length) return h + '<div class="box"><p class="empty">No decisions, problems or runs yet. Work appears here once agents start proposing evidence and experiments.</p></div></section>';

    let any = false;
    SECTIONS.forEach((sec) => {
      if (!sec.statuses.some((s) => ui.active.has(s))) return;
      any = true;
      const vis = items.filter((i) => sec.statuses.includes(i.status) && ui.active.has(i.status))
        .sort((a, b) => score(b) - score(a) || ORDER.indexOf(a.status) - ORDER.indexOf(b.status));
      // Each section can be collapsed. The header keeps its name and count visible either way.
      const shut = ui.collapsed.has(sec.key);
      // Decisions without a source are "not tracked", which is different from "none pending".
      const untracked = sec.decision && (isNT(v.decisions) || isUN(v.decisions)) && !vis.length;
      h += '<div class="sec-wrap' + (shut ? ' collapsed' : '') + '" data-sec="' + sec.key + '">' +
        '<h3 class="sec' + (sec.decision ? ' sec-dec' : '') + '"><button class="sec-btn" data-action="section" data-sec="' + sec.key + '" ' +
          'aria-expanded="' + !shut + '" aria-controls="sec-' + sec.key + '">' +
          (sec.decision ? icon('alertCircle') : '') + esc(sec.name) + (untracked ? '' : ' (' + vis.length + ')') + icon('chevronDown', 'sec-exp') + '</button></h3>' +
        '<div class="sec-body" id="sec-' + sec.key + '"><div class="sec-inner">' +
          '<div class="box' + (sec.decision ? ' box-dec' : '') + '">' + (vis.length ? vis.map(workRow).join('') : untracked ? '<p class="empty">' + (isUN(v.decisions) ? unText(v.decisions) : 'Not tracked yet. Decisions appear once they are recorded in the event log (control/events.jsonl).') + '</p>' : '<p class="empty">Nothing here</p>') + '</div>' +
        '</div></div></div>';
    });
    if (!any) h += '<p class="empty">No statuses selected</p>';
    return h + '</section>';
  }

  function renderFindings(v) {
    const L = v.connection === 'loading';
    const all = arr(v.findings);
    const settled = all.filter((f) => f.verification === 'verified' || f.verification === 'rejected');
    const waiting = all.length - settled.length;
    let h = '<section aria-label="Recent findings"><div class="toolbar"><h2 class="h">Recent findings</h2><a href="#" data-action="link" data-link="All findings" class="small">All findings</a></div>';
    if (waiting) h += '<p class="aside-note">' + icon('arrowUp') + waiting + ' finding' + (waiting === 1 ? '' : 's') + ' waiting for your review, listed under Needs your decision</p>';
    if (L) return h + '<div class="box">' + [1, 2].map(() => '<div class="frow">' + skeleton(82) + '<div>' + skeleton(200) + '<br>' + skeleton(140) + '</div></div>').join('') + '</div></section>';
    if (!L && isUN(v.findings)) return h + '<div class="box"><p class="empty">' + unText(v.findings) + '</p></div></section>';
    if (!L && isNT(v.findings)) return h + '<div class="box"><p class="empty">Not tracked yet. Findings appear once they are recorded in the event log (control/events.jsonl).</p></div></section>';
    if (!settled.length) return h + '<div class="box"><p class="empty">No reviewed findings yet. Findings appear here after a researcher verifies or rejects them.</p></div></section>';
    return h + '<div class="box">' + settled.map((f) => {
      const who = f.inferredBy, r = f.reviewedBy;
      return '<div class="frow">' + verifyTag(f.verification) + '<div class="fc">' +
        '<b>' + esc(f.claim) + '</b>' +
        '<div class="eff">' + esc(f.effect) + '</div>' +
        '<div class="unc">' + esc(f.uncertainty) + '</div>' +
        '<div class="at">' + icon('robot') + 'Inferred by agent <code>' + esc(who.session) + '</code> · ' + esc(who.agent) + ' · ' + esc(who.model) + ' · ' + esc(who.at) + '</div>' +
        '<div class="at">' + icon('user', 'c-acc') + esc(r.verb) + ' by <b>' + esc(r.name) + '</b> · ' + esc(r.at) + '</div>' +
        '<div class="why">“' + esc(r.rationale) + '”</div>' +
        links(f.links, f.id) +
      '</div></div>';
    }).join('') + '</div></section>';
  }

  function renderActions(v) {
    const L = v.connection === 'loading';
    const acts = arr(v.actions);
    let h = '<section aria-label="Recent actions"><div class="toolbar"><h2 class="h">Recent actions</h2><a href="#" data-action="link" data-link="Audit trail" class="small">Full audit trail</a></div>';
    if (L) return h + '<div class="box tl">' + [1, 2, 3].map(() => '<div class="te">' + skeleton(36) + skeleton(12) + skeleton(180) + '</div>').join('') + '</div></section>';
    if (isNT(v.actions)) return h + '<div class="box"><p class="empty">Not tracked yet.</p></div></section>';
    if (isUN(v.actions)) return h + '<div class="box"><p class="empty">' + unText(v.actions) + '</p></div></section>';
    if (!acts.length) return h + '<div class="box"><p class="empty">No actions recorded yet.</p></div></section>';
    const ic = { human: ['user', 'c-acc'], agent: ['robot', ''], system: ['robot', ''], unknown: ['help', ''] };
    return h + '<ol class="box tl">' + acts.map((a, i) =>
      '<li class="te' + (i === 0 ? fr('action0') : '') + '"><span class="tm">' + esc(a.at) + '</span>' + icon((ic[a.actor.kind] || ic.unknown)[0], (ic[a.actor.kind] || ic.unknown)[1]) + '<div>' +
        '<span class="who">' + esc(a.actor.name) + '</span> ' + esc(a.what) +
        (a.context ? ' <span class="muted">· ' + esc(a.context) + '</span>' : '') +
        (a.rationale ? '<span class="why">“' + esc(a.rationale) + '”</span>' : '') +
      '</div></li>').join('') + '</ol></section>';
  }

  // ---------- main render ----------
  // Data state. The view is replaced whenever the adapter delivers a new read model.
  let view = { connection: 'loading' };
  let lastGood = null;
  function render() {
    $app.className = 'layout' + (ui.detailed ? ' detailed' : '') + (view.connection === 'disconnected' ? ' offline' : '') + (ui.sideOpen ? ' side-open' : '');
    const toReview = arr(view.findings).filter((f) => f.verification === 'unverified' || f.verification === 'recheck').length;
    // On narrower screens (tablet portrait) the side column becomes a collapsible drawer.
    // On desktop the tab, scrim and drawer header are hidden by CSS and the column is always shown.
    $app.innerHTML =
      '<div class="col-main">' + renderHeader(view) + renderBanner(view) + renderPipeline(view) + renderWork(view) + '</div>' +
      '<button class="side-tab" data-action="side-open" aria-controls="side" aria-expanded="' + ui.sideOpen + '" ' +
        'aria-label="Show findings and actions' + (toReview ? ', ' + toReview + ' finding' + (toReview === 1 ? '' : 's') + ' waiting for review' : '') + '">' +
        icon('chevronLeft') + '<span class="side-tab-label">Findings · Actions</span>' +
        (toReview ? '<span class="badge" aria-hidden="true">' + toReview + '</span>' : '') + '</button>' +
      '<div class="scrim" data-action="side-close" aria-hidden="true"></div>' +
      '<aside id="side" class="col-side" aria-label="Findings and actions">' +
        '<div class="side-head"><h2>Findings and actions</h2>' +
        '<button class="btn btn-secondary side-close" data-action="side-close" aria-label="Hide findings and actions">Hide' + icon('chevronRight') + '</button></div>' +
        renderFindings(view) + renderActions(view) + '</aside>';
    fresh.clear();
  }

  // ---------- loading ----------
  let refreshing = null;
  function refresh() {
    if (refreshing) return refreshing;
    refreshing = Promise.resolve().then(() => adapter.load()).then((v) => {
      lastGood = v;
      view = Object.assign({}, v, { connection: v.connection || 'live' });
    }).catch(() => {
      view = lastGood ? Object.assign({}, lastGood, { connection: 'disconnected' }) : { connection: 'disconnected' };
    }).then(() => { refreshing = null; render(); });
    return refreshing;
  }
  let changeTimer;
  const onChange = () => { clearTimeout(changeTimer); changeTimer = setTimeout(refresh, 150); };
  function onConnection(state) {
    if (state === 'live') { refresh(); return; }
    if (lastGood) view = Object.assign({}, lastGood, { connection: state });
    else view = { connection: state === 'stale' ? 'loading' : 'disconnected' };
    render();
  }

  // ---------- toast ----------
  const $toast = document.getElementById('toast');
  let toastTimer;
  function toast(msg) {
    $toast.textContent = msg; $toast.hidden = false;
    clearTimeout(toastTimer); toastTimer = setTimeout(() => { $toast.hidden = true; }, 3500);
  }

  // ---------- confirmation dialog (state-changing commands) ----------
  const $dlg = document.getElementById('confirm');
  const $reason = document.getElementById('confirm-reason');
  const $err = document.getElementById('confirm-error');
  let pendingCmd = null;
  const CMD_TEXT = {
    rerun: ['Rerun ', 'Starts a new run with the same approved protocol. The earlier run stays in the record.', 'Rerun', 'btn-primary'],
    pause: ['Pause ', 'Pauses the run after the current unit. You can resume it later.', 'Pause run', 'btn-primary'],
    resume: ['Resume ', 'Resumes the paused run.', 'Resume run', 'btn-primary'],
    stop: ['Stop ', 'Stops the run now. Units already recorded are kept; the run is marked cancelled.', 'Stop run', 'btn-danger-solid']
  };
  function openConfirm(res, action, id, version) {
    const [t, body, ok, cls] = CMD_TEXT[action];
    pendingCmd = { res, action, id, version: Number(version) };
    document.getElementById('confirm-title').textContent = t + id + '?';
    document.getElementById('confirm-body').textContent = body;
    const $ok = document.getElementById('confirm-ok');
    $ok.textContent = ok; $ok.className = 'btn ' + cls;
    $reason.value = ''; $err.hidden = true;
    $dlg.showModal(); $reason.focus();
  }
  const newRequestId = () => (window.crypto && crypto.randomUUID ? crypto.randomUUID() : Date.now().toString(36) + Math.random().toString(36).slice(2));
  document.getElementById('confirm-cancel').addEventListener('click', () => $dlg.close());
  $reason.addEventListener('input', () => { $err.hidden = true; });
  document.getElementById('confirm-form').addEventListener('submit', (e) => {
    e.preventDefault();
    if (!$reason.value.trim()) { $err.hidden = false; $reason.focus(); return; }
    const c = pendingCmd;
    const $ok = document.getElementById('confirm-ok');
    $ok.disabled = true;
    adapter.sendCommand(c.res, c.action, { rationale: $reason.value.trim(), expectedVersion: c.version, requestId: newRequestId() })
      .then((r) => {
        $ok.disabled = false;
        $dlg.close();
        if (r.ok) {
          fresh.add('pending:' + c.id); fresh.add('action0');
          toast('Request recorded. Waiting for the control plane to confirm.');
        } else if (r.status === 'UNSUPPORTED') {
          toast('Not available yet: no control plane can carry this out (#6). Nothing was changed; your request was logged.');
        } else {
          toast('Not sent: ' + r.message + '. Nothing was changed.');
        }
        refresh();
      });
  });

  // Open and close the tablet drawer without re-rendering, so CSS can animate both directions.
  function setSide(open) {
    ui.sideOpen = open;
    $app.classList.toggle('side-open', open);
    const tab = $app.querySelector('.side-tab');
    if (tab) tab.setAttribute('aria-expanded', String(open));
    const target = $app.querySelector(open ? '.side-close' : '.side-tab');
    if (target && target.getClientRects().length) target.focus();
  }

  // ---------- events (delegated, so re-rendering never loses listeners) ----------
  // Collapse or expand a Work section in place (no re-render) so CSS can animate it.
  function toggleSection(btn) {
    const key = btn.dataset.sec;
    const shut = !ui.collapsed.has(key);
    if (shut) ui.collapsed.add(key); else ui.collapsed.delete(key);
    btn.closest('.sec-wrap').classList.toggle('collapsed', shut);
    btn.setAttribute('aria-expanded', String(!shut));
  }

  function toggleRow(row) {
    const id = row.dataset.row;
    // Toggle in place (no re-render) so CSS can animate both expanding and collapsing.
    const open = !ui.open.has(id);
    if (open) ui.open.add(id); else ui.open.delete(id);
    row.parentElement.classList.toggle('open', open);
    row.setAttribute('aria-expanded', String(open));
  }

  $app.addEventListener('click', (e) => {
    const a = e.target.closest('[data-action]');
    if (a) {
      e.preventDefault();
      const act = a.dataset.action;
      if (act === 'filter') { e.stopPropagation(); ui.menuOpen = !ui.menuOpen; if (ui.menuOpen) fresh.add('menu'); render(); return; }
      if (act === 'filter-all') { e.stopPropagation(); ui.active = new Set(ORDER); render(); return; }
      if (act === 'filter-none') { e.stopPropagation(); ui.active = new Set(); render(); return; }
      if (act === 'detailed') {
        ui.detailed = !ui.detailed;
        fresh.add('switch');
        try { localStorage.setItem('aisoc.detailed', ui.detailed ? '1' : '0'); } catch (err) { /* ignore */ }
        render(); return;
      }
      if (act === 'section') { toggleSection(a); return; }
      if (act === 'side-open' || act === 'side-close') { setSide(act === 'side-open'); return; }
      if (act === 'retry') { refresh(); return; }
      if (act === 'review') { toast('Review page for ' + a.dataset.id + ' is not built yet. Approve and reject will live there.'); return; }
      if (act === 'link') { toast('"' + a.dataset.link + '" opens a screen that is not built yet.'); return; }
      if (act === 'cmd') {
        if (view.connection === 'disconnected') { toast('Can\'t send while disconnected. Your request was not recorded.'); return; }
        openConfirm(a.dataset.res, a.dataset.cmd, a.dataset.id, a.dataset.version); return;
      }
    }
    if (e.target.closest('.menu')) { e.stopPropagation(); return; }
    const row = e.target.closest('.row[data-row]');
    if (row && !e.target.closest('button, a, .tx, input, label')) {
      const sel = window.getSelection();
      if (sel && String(sel).length) return;
      toggleRow(row);
    }
  });

  $app.addEventListener('change', (e) => {
    const f = e.target.dataset && e.target.dataset.filter;
    if (!f) return;
    e.target.checked ? ui.active.add(f) : ui.active.delete(f);
    render();
  });

  $app.addEventListener('keydown', (e) => {
    const row = e.target.closest && e.target.closest('.row[data-row]');
    if (row && e.target === row && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); toggleRow(row); }
  });

  document.addEventListener('click', () => { if (ui.menuOpen) { ui.menuOpen = false; render(); } });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (ui.menuOpen) { ui.menuOpen = false; render(); return; }
    if (ui.sideOpen && !document.getElementById('confirm').open) setSide(false);
  });

  render();
  refresh();
  if (adapter.subscribe) adapter.subscribe({ onChange, onConnection });
})();
