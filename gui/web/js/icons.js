// Small inline icon set, bundled locally (no CDN: the app must work offline).
(function () {
  const P = {
    chevronRight: '<path d="M9 6l6 6-6 6"/>',
    chevronDown: '<path d="M6 9l6 6 6-6"/>',
    chevronLeft: '<path d="M15 6l-6 6 6 6"/>',
    x: '<path d="M18 6L6 18M6 6l12 12"/>',
    check: '<path d="M5 12l5 5L20 7"/>',
    alertCircle: '<circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16h.01"/>',
    help: '<circle cx="12" cy="12" r="9"/><path d="M12 17h.01M9.2 9a3 3 0 1 1 3.8 2.9c-.6.3-1 .8-1 1.5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    loader: '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/>',
    filter: '<path d="M4 5h16l-6 8v5l-4 2v-7z"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14.9-3M4 4v4h4M4 13a8 8 0 0 0 14.9 3M20 20v-4h-4"/>',
    pause: '<path d="M8 5v14M16 5v14"/>',
    flask: '<path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 1.7 3h10.6a2 2 0 0 0 1.7-3l-5-9V3"/>',
    robot: '<rect x="5" y="8" width="14" height="11" rx="2"/><path d="M12 4v4M9 13h.01M15 13h.01M9 16h6"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M5 21a7 7 0 0 1 14 0"/>',
    arrowUp: '<path d="M12 19V5M6 11l6-6 6 6"/>',
    world: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    flag: '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    book: '<path d="M4 19V5a2 2 0 0 1 2-2h13v14H6a2 2 0 0 0-2 2zm0 0a2 2 0 0 0 2 2h13"/>',
    bulb: '<path d="M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0 0 12 3z"/>',
    play: '<path d="M7 4l13 8-13 8z"/>',
    chart: '<path d="M4 20h16M7 16v-4M12 16V8M17 16v-7"/>',
    alertTriangle: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    recheck: '<path d="M20 11a8 8 0 1 0-2.3 5.7M20 5v6h-6"/><path d="M12 8v4M12 15h.01"/>',
    unplug: '<path d="M7 12l5-5 5 5-5 5z"/><path d="M3 3l18 18"/>'
  };
  window.icon = function (name, extraClass) {
    const body = P[name] || '';
    return '<svg class="ic ' + (extraClass || '') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      body + '</svg>';
  };
})();
