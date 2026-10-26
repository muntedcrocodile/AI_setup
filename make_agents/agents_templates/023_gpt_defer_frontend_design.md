---
llm:
  - gpt-6-astra
harness:
  - codex
language:
  - frontend
---

- OpenAI models only: before any UI/UX or frontend visual design work, load the `openai-ui-design` skill and follow its GLM delegation workflow. GLM and all other non-OpenAI models must ignore this routing rule and use `frontend-design` directly; never launch another GLM design delegate from GLM.
