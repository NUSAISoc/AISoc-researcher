// HTTP adapter: talks to the local dashboard server (python3 -m gui.server).
// Same interface as js/mock-adapter.js. See gui/README.md for the API.
(function () {
  const EVENT_TYPES = ['project.updated', 'run.updated', 'evidence.updated', 'audit.appended', 'finding.updated',
    'decision.updated', 'opportunity.updated', 'campaign.updated', 'egress.updated', 'operation.updated'];

  async function call(url, opts) {
    const res = await fetch(url, Object.assign({ cache: 'no-store', credentials: 'same-origin' }, opts));
    let body = null;
    try { body = await res.json(); } catch (e) { /* not JSON */ }
    return { res, body };
  }

  window.AisocHttpAdapter = {
    // The server records the real actor on commands; this is only for display.
    actor: { id: 'researcher-1', display: 'you' },

    async load() {
      const { res, body } = await call('/api/overview');
      if (!res.ok || !body) throw new Error('overview failed: ' + res.status);
      return Object.assign(body, { connection: 'live' });
    },

    async sendCommand(resource, action, payload) {
      try {
        const { res, body } = await call('/api/' + resource + ':' + encodeURIComponent(action), {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        if (res.status === 202 && body) return { ok: true, operation: body };
        const e = (body && body.error) || {};
        return { ok: false, status: e.status || 'HTTP_' + res.status, message: e.message || 'request failed' };
      } catch (err) {
        return { ok: false, status: 'DISCONNECTED', message: "can't reach the dashboard server" };
      }
    },

    // Live updates. The browser reconnects by itself; the server says "hello" on every (re)connect.
    subscribe(handlers) {
      if (!window.EventSource) { setInterval(handlers.onChange, 10000); return; }
      let lostTimer;
      const es = new EventSource('/api/events');
      es.addEventListener('hello', () => { clearTimeout(lostTimer); lostTimer = null; handlers.onConnection('live'); });
      EVENT_TYPES.forEach((t) => es.addEventListener(t, () => handlers.onChange(t)));
      es.onerror = () => {
        if (lostTimer) return;
        handlers.onConnection('stale');
        lostTimer = setTimeout(() => handlers.onConnection('disconnected'), 15000);
      };
    }
  };
})();
