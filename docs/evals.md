# The eval kit: measuring AI tasks and their judges

## Why

HQ's prompts grew one incident at a time. Every bad output got a new instruction, and nothing
measured whether a change helped or broke something else. This is the failure in Hamel Husain's
"Your AI product needs evals" (hamel.dev/blog/posts/evals). The cure is his loop:

1. Look at real outputs.
2. Label them pass or fail.
3. Turn the labels into eval sets.
4. Score every prompt change on them.
5. Use an AI judge only as far as it agrees with the human's labels.

Doctrine builds that loop in and makes CI hold it.

## What: an AI task

An AI task is declared in the project's `doctrine.toml`:

```toml
[[ai_tasks]]
name = "fit-score"                       # evals/fit-score/ holds its files
prompt = "prompts/fit-score.md"          # the prompt file
command = ["python", "-m", "jobs.adapters.fit_eval"]   # answers one case
minimum = 0.85                           # share of cases it must get right
judge = false                            # true for a judge (below)
```

| File | Who writes it | What it holds |
|---|---|---|
| `evals/<task>/cases.jsonl` | Omar, or the labelling page | One case per line: `{"id", "input", "expected"}`. `expected` is one answer or a list of accepted ones |
| `evals/<task>/results.jsonl` | `doctrine eval run` only (protected) | One recorded run per line: prompt and eval set digests, score, total, failed case ids, time |

**The command's protocol:** it is run once per case, with the case's `input` as JSON on standard
input. It prints its answer on standard output. A crash, a timeout (300 s) or an empty answer
counts as wrong. Answers are compared after collapsing whitespace and ignoring case. Any language
works.

## How: changing a prompt

```
# edit prompts/fit-score.md
doctrine eval run fit-score     # prints the score and the failed cases, records the run
git add prompts/fit-score.md evals/fit-score/results.jsonl
```

`doctrine eval run` exits with failure under the minimum. The run is still recorded, so the failure
is visible.

**In CI (`doctrine ci evals`),** for every task whose prompt or eval set the pull request changed:

- no recorded run on the new version (the prompt's and eval set's content digests) is refused;
- a run under the minimum is refused;
- a lower score than base's best on the same eval set waits for Omar's approval;
- a grown eval set is judged by the minimum only. New cases are meant to be hard.

**Goalposts:** lowering a minimum, removing a task, turning a judge into a plain task, and changing
or removing an existing case's expected answer all need Omar's approval. Adding cases is free.

**Fingerprints** ignore CRLF versus LF, so a Windows checkout and CI's Linux checkout agree.

## Judges

A judge is an AI task that says `pass` or `fail` on another task's output. Mark it `judge = true`.
Its eval set is Omar's labels: each case's input is a trace (`{"input", "output"}`), and its
expected answer is `pass` or `fail`.

**How it is scored:** by the lower of two rates.

- **passes kept:** the share of Omar's passes the judge passes;
- **fails caught:** the share of Omar's fails the judge fails.

**Why not plain accuracy:** when 90% of outputs pass, a judge that passes everything is 90%
"accurate" and catches nothing. Here it scores 0. Without both kinds of label, a judge scores 0:
it can't be measured.

## The labelling page

```
doctrine eval label fit-judge --traces traces/fit.jsonl
```

- **Traces file:** one real input/output pair per line, `{"id"?, "input", "output"}`. The project
  writes it from production. A trace without an id is named by its content.
- **The page:** it opens in the browser, served from this computer only (127.0.0.1). It shows one
  trace at a time with Pass, Fail and an optional note ("why"). Each click appends a case to the
  judge's eval set at once.
- **Stopping:** Ctrl+C in the terminal. Started again, it goes on with the traces not yet
  labelled.
- **What it doesn't do:** summarize or judge the traces. Omar does the judging; the page does the
  mechanics.

## The loop, end to end

1. The project logs real traces of a task (input, output).
2. Omar labels a sample on the page: `doctrine eval label <judge> --traces <file>`.
3. `doctrine eval run <judge>` measures the judge's agreement with him. Improve the judge's prompt
   until it holds its minimum.
4. The judge can then grade the main task's outputs at scale. Each change to the main task's prompt
   comes with `doctrine eval run <task>`, and CI holds both.

## Where in the code

- `domain/evals/`: cases, scoring, alignment, labels, results and the gate's rule.
- `application/evals.py`: a run.
- `adapters/storage/eval_files.py`, `adapters/tools/task_command.py`, `adapters/web/label_page.py`.
- The commands are in `adapters/cli/commands/eval_command.py` and `label_command.py`. The gate is
  `adapters/cli/gates/eval_gate.py`.

## Known limits

- CI can't re-run tasks itself, because that needs a paid model API.
- A change to a task's code alone doesn't trigger the gate.
- Claude could append made-up labels to a judge's eval set. Issue #34 would protect it.
