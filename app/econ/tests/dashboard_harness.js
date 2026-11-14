// Runs the dashboard's inline <script> against a feed with a minimal DOM stub and prints
// the rendered verdict as JSON. Used by test_dashboard_verdict.py.
//   node dashboard_harness.js <index.html> <feed.json>
'use strict';
const fs = require('fs');
const [htmlPath, feedPath] = process.argv.slice(2);

const html   = fs.readFileSync(htmlPath, 'utf8');
const script = html.slice(html.lastIndexOf('<script>') + 8, html.lastIndexOf('</script>'));
const feed   = JSON.parse(fs.readFileSync(feedPath, 'utf8'));

const els = {};
const el = id => els[id] ||= {
  textContent: '', innerHTML: '', className: '', style: {}, disabled: false, value: '',
  classList: { add() {}, remove() {}, toggle() {} },
  addEventListener() {}, replaceChildren() {}, offsetWidth: 240,
  getContext: () => new Proxy({}, { get: () => () => {} }),
};
global.document = { getElementById: el, createElement: () => ({ append() {}, className: '', textContent: '' }) };
global.localStorage = { getItem: () => '[]', setItem() {} };
global.devicePixelRatio = 1;
global.fetch = async () => ({ ok: true, json: async () => feed });
global.console.warn = () => {};

eval(script);  // eslint-disable-line no-eval

setTimeout(() => {
  const tags = [...els['verdict-tags'].innerHTML.matchAll(/<span class="vtag ([^"]*)">([^<]*)<\/span>/g)]
    .map(m => ({ cls: m[1], label: m[2] }));
  process.stdout.write(JSON.stringify({
    text: els['verdict-text'].textContent,
    tags,
    error: els['error-detail'] ? els['error-detail'].textContent : '',
  }));
}, 50);
