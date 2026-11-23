// Renders every <pre class="mermaid"> block. Loaded (deferred, after the vendored
// mermaid.min.js) only on pages that contain a diagram -- see
// hugo/layouts/partials/extend_post_content.html.
mermaid.initialize({ startOnLoad: true, theme: 'neutral' });
