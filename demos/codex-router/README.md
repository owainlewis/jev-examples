# Codex Router

Describe a task. Jev classifies its complexity. Codex opens a new task with the
configured model and a complete brief.

```text
$codex-router Investigate the race condition in our job worker and add a regression test.
```

This is a standalone skill you can copy and share. It does not modify Codex,
proxy API traffic, or switch the model in your existing conversation.

## Requirements

- [uv](https://docs.astral.sh/uv/getting-started/installation/) to run the Python script.
- A [TypeSafe API key](https://docs.typesafe.ai/) with credit for real Jev calls.
- A signed-in Codex desktop host exposing `create_thread` and `list_projects`,
  with model selection on task creation. Check these tools are available in your
  installation; a skill cannot add them. The Python classifier also runs alone,
  but plain CLI skill support does not supply the desktop handoff tools.
- Access to the models configured in `models.json`.

Codex uses your existing account for the new task. This skill needs no separate
OpenAI API key. Jev usage and Codex usage remain separate. The parent Codex task
also consumes usage while preparing and routing the brief.

## Install

From a checkout of this repository, copy the complete folder into your personal
skills directory. These commands refuse to overwrite an existing installation:

```bash
mkdir -p "$HOME/.agents/skills"
test ! -e "$HOME/.agents/skills/codex-router" && cp -R demos/codex-router "$HOME/.agents/skills/codex-router"
```

If the destination already exists, compare it before replacing your local model
settings. Alternatively, copy the folder into a project's `.agents/skills/`.
Codex discovers this location through its [skill system](https://developers.openai.com/codex/skills/).
Restart Codex if the new skill does not appear. Explicit invocation is required;
it will not route ordinary messages automatically.

## Store your key

For a desktop app, a private file is usually easier than relying on inherited
shell environment variables:

```bash
mkdir -p "$HOME/.config/codex-router"
chmod 700 "$HOME/.config/codex-router"
touch "$HOME/.config/codex-router/.env"
chmod 600 "$HOME/.config/codex-router/.env"
```

Open that file in your editor and add:

```dotenv
TYPESAFE_API_KEY=your_key_here
```

Keep it outside this repository. Do not paste the key into a chat. An existing
`TYPESAFE_API_KEY` environment variable takes precedence. The script does not
automatically load `.env` files from the project you happen to be working in.
Use `--env-file /absolute/path/to/.env` to explicitly select another file.

The classification brief is sent to TypeSafe. The skill prepares a short brief
without credentials or unnecessary private content. It does not upload the
repository. Running the script directly sends the text you supply.

## Choose models

Edit the installed `models.json` to match the models and reasoning levels your
Codex host supports. The supplied mapping uses choices exposed by the author's
host at development time; availability is not universal.

| Classification | Default model | Reasoning |
| --- | --- | --- |
| routine | `gpt-5.6-luna` | low |
| standard | `gpt-5.6-terra` | medium |
| complex | `gpt-6-astra` | high |

Jev uses Choice to judge effort and risk. Python maps the class to a model;
Jev never supplies executable commands or arbitrary model ids. At less than
`min_probability` (default 0.8), the script uses the complex route. API errors,
timeouts, and invalid responses also use that route, with null probability.
Missing credentials, invalid configuration, and empty or oversized input stop
the command with exit code 2 instead of creating a task.

The reported probability belongs to the complexity classification. It is not a
success estimate for the selected model. The mapping is a heuristic, not a
benchmark, a live price lookup, or a guarantee of savings.

## Try the classifier

This makes a real Jev call without creating a Codex task:

```bash
uv run "$HOME/.agents/skills/codex-router/scripts/route.py" 'Explain a small Python function in plain language.'
```

For longer briefs, put the text in a file and pass it through standard input:

```bash
uv run "$HOME/.agents/skills/codex-router/scripts/route.py" < task.txt
```

Output includes the selected route, model, reasoning, Jev classification, its
probability, the distribution, and the routing reason. Nothing is spawned by
Python. Codex reads the JSON and calls its task-creation tool.

## Demo it

Start with a project that has no uncommitted work the new task needs. Try one
invocation at a time:

```text
$codex-router Explain how the main entry point works. Do not edit files.
$codex-router Add input validation to this endpoint and test invalid requests.
$codex-router Investigate concurrent updates that lose data and implement a tested fix.
```

Show the actual routing result, then follow the created task. Don't script
specific probabilities or promise that these prompts always land in different
classes. A task needing your current changes requires an explicit choice of
starting state; a new default worktree starts from the project's default branch.

## Verification

From this repository:

```bash
uv run --with typesafe-sdk==0.7.0 --with python-dotenv==1.2.1 python -m unittest discover -s demos/codex-router/tests -v
```

Tests cover class mapping, uncertainty, malformed responses, provider failure,
key handling, and command output without a live API. A live classifier check
proves the SDK integration. Desktop task creation is controlled by the host
and should be rehearsed in your installation before recording or sharing a
claim of end-to-end compatibility.

The files in this folder are available under the included MIT license.
