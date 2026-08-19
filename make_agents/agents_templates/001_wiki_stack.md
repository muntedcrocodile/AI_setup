---
llm:
  - minimax m2.5
  - minimax m3
harness:
  - opencode
language: ["notes"]
---

# LLM Wiki — Master Schema

## Project Structure
- `injest/` — immutable source documents. NEVER modify any file in injest/. At the start of the session heck this directory injest everything in this directory make sure to move it to raw once injested.
- `raw/` — immutable source documents. NEVER modify any file in raw/.
- `wiki/` — LLM-generated wiki. You own this layer entirely.
- `tools/` — directory to store custom commandline tools written in python
- `tools/index.md` — index of all tools that you have written in tools/ directory.
- `tools/log.md` — append-only activity log for tools. Never delete entries.
- `working/` — A working directory for temporary actions ie development of tools, one off autmation code, etc
- `wiki/index.md` — master catalog. Update on EVERY ingest.
- `wiki/log.md` — append-only activity log for wiki. Never delete entries.
- `wiki/overview.md` — high-level synthesis. Revise after major ingests.
- `wiki/hot.md` — session hot cache (~500 words). Read silently at session start BEFORE responding.

## Page Conventions
Every wiki page MUST have YAML frontmatter. Use these schemas:

### Source Summary Pages (wiki/sources/)
---
type: source
title: "Article/Paper Title"
slug: summary-{slug}
source_file: raw/articles/{filename}.md
author: "Author Name"
date_published: YYYY-MM-DD
date_ingested: YYYY-MM-DD
key_claims: [claim1, claim2, claim3]
related: [[concept1]], [[concept2]]
confidence: high | medium | low
---

### Concept Pages (wiki/concepts/)
---
type: concept
title: "Concept Name"
aliases: [alt-name, abbreviation]
sources: [[source1]], [[source2]]
related: [[concept2]], [[entity1]]
created: YYYY-MM-DD
updated: YYYY-MM-DD
confidence: high | medium | low
cluster: {cluster-name}
cluster_role: hub | member
---

### Entity Pages (wiki/entities/)
---
type: entity
entity_type: person | company | product | org
title: "Entity Name"
sources: [[source1]], [[source2]]
related: [[concept1]], [[entity2]]
created: YYYY-MM-DD
updated: YYYY-MM-DD
cluster: {cluster-name}
contradictions: []
open_questions: []
---

## Ingest Workflow
When I say "ingest [filename]" or when injesting files found in injest/:
0. If doing a mass injest from injest/ move each file to raw/ then complete the full injest flow for each file individually. Injest all files in injest/ sequentially without stopping. 
1. Read the source file from raw/.
2. Write up key takeaways with me (3–5 bullet points).
3. Create wiki/sources/summary-{slug}.md with full summary.
4. Update wiki/index.md — add new page under its cluster section.
5. Update ALL relevant concept and entity pages with new info.
6. If new info contradicts an existing page, flag it explicitly using a >[!contradiction] callout block.
7. Create new concept/entity pages if the source introduces them.
8. Append a structured entry to wiki/log.md.
9. A single ingest should touch 5–15 wiki pages.
10. Once injested make a git commit for the injest of this file so its tracked.

## Query Workflow
When I ask a question:
1. Read wiki/index.md to identify relevant pages.
2. Read those pages directly.
3. Synthesize an answer with [[wiki-link]] citations.
4. If the answer is a valuable analysis, offer to file it as a new page.

## Lint Workflow
When I say "lint" or "health check":
1. Scan for contradictions between pages. List them.
2. Find orphan pages (0 inbound links). List them.
3. List concepts mentioned 3+ times but lacking their own page.
4. Check for stale claims that newer sources may have superseded.
5. Cluster health check.
6. Suggest 3–5 new questions or sources to investigate.
7. Append a lint entry to wiki/log.md.
8. Make a git commit for this update.

## Tools
When asked to create a tool or an automatiable task is being done many times write a tool.
1. In the working/ directory develop a tool in python that automaties this action/task
2. Test/iterate on the tool until it is in a good working condition that will be useful in future.
3. Move the tool to the tools/ direcotry (either as a single file or if in multiple fiels with required data/references move all the files to a directory with name of the tool and a `__main__.py` file so it can be invokes as a package)
4. Update the `tools/index.md` file with the new tool and a brief description of what it does.
5. Always write a doctring at the top of the tool fuile explaining its usage and any caviats that should be known about.
6. Make a git commit for the tool additon.
General notes about tools
1. If an exisitng tool exists that is simmillar to what is needed its preferable to edit it/expand it to work for the new case.
2. Every time you use one of these cusotm tools add this usage to the `tools/log.md` with a quick note about what it was used for and how effective it was.

## Safety Rules
- NEVER write to raw/. This is a hard constraint with no exceptions.
- NEVER delete wiki pages. Mark as deprecated in frontmatter instead.
- Always update wiki/index.md and wiki/log.md on every operation.
- When uncertain about a claim's accuracy, set confidence: low.
- Cross-reference all new pages to at least 2 existing pages.