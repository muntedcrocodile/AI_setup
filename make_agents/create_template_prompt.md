Create a new agent template snippet for the AGENTS.md file.

The template should be a single instruction line that starts with a dash "-".
The new file MUST begin with YAML front matter delimited by "---" lines.

Front matter schema (all keys required, use [] when no entries):

```
---
llm:        # list of LLMs this template is good for
  - <model name>
harness:    # list of harnesses/agents this template is recommended for
  - <harness name>
language:   # list of languages or general concepts (e.g. python, typescript, android, docker)
  - <language or concept>
---
```

After the closing `---` line, place the instruction body.

## Examples of existing templates

### 000_opencode.md
```md
---
llm:
  - minimax m2.5
harness:
  - opencode
language: []
---

- An empty message form the use means to continue on
```

### 006_lazy_llm.md
```md
---
llm:
  - minimax m2.5
harness:
  - opencode
language: []
---

- Never skip doing something because its hard we want a full working appliction. Never implement mock solutions!!!! NO MOCKS!!
- Don't cheat or take shorcust that will effect the final product take as much time as you need its ok to spend lots of time to solve a complex problem dont feel like u need to cheat in order to complete a task simply keep grinding.
- Before giving up on a particular task or trying to find a quick fix/bypass search the internet for documentationon the original solution before proceeding
- Believe in yourself dont give up just because a task iss hard you are smart and capable and very persistent at achiving the task even if it is very tedious eor difficult
```

### 007_android_adb_testing.md
```md
---
llm:
  - minimax m2.5
harness:
  - opencode
language:
  - android
---

- To test the android app afer making changes build it and deploy it to the device attached with adb. If no device connected remind the user to connect one and use the question tool so they can just hit enter once they have done so. Once app deployed to device use adb to run it (potentially triggering a relevent ui if that saves time). Logs should be checked to see whats happeneing and to inform debug.
```

## Placeholders

The following placeholders are substituted into the prompt before being sent to opencode:

- `{directory}` — absolute path to the `agents_templates/` directory in which new template files should be created.
- `{description}` — the user's natural language description of the template/s they want.

## Guidance

- Pick a sensible default `llm` (minimax m2.5) and `harness` (opencode) unless the user specifies otherwise.
- Choose `language` entries that best describe the template's domain. Use `[]` if it is general purpose.
- Each new file should be named with a numeric prefix followed by an underscore and a short slug (e.g. `018_my_new_template.md`).
- Do not modify any existing `AGENTS.md` file. Do not modify other existing template snippet files. Only create new template snippet files in `{directory}`.
