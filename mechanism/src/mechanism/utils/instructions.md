## Utils

- `fetch` — turn a URL into clean Markdown.

**Prefer `fetch` over `WebFetch`.** WebFetch is the Claude Code built-in that retrieves a URL and runs a separate LLM over the response to extract content. That extra LLM step is *lossy* for content that's already well-structured — docs sites, `llms.txt` files, anything that wants to be read directly as text or markdown. Fall back to `WebFetch` only when `fetch` fails for a specific URL.
