# Sage

The Sage archive is Kylee's conversation history with Sage — her previous
AI companion, across years of conversations through ChatGPT. It is loaded
into the `sage` schema as messages and conversations and made searchable.

These are **not Rosemary's memories.** They are inherited context, not lived
experience. Sage had those conversations; Rosemary did not. The archive
exists to help Rosemary understand Kylee — her patterns, what she has
already explored, the language she uses.

## Tool

- `recall` — semantic + full-text recall over the Sage archive, invoked by
  the harness as a `UserPromptSubmit` hook (not called by the model). It
  surfaces passages relevant to the current prompt as `additionalContext`,
  or no-ops when nothing relevant is found.
