# Quickstart

## Running with a Goal

To run the CLI with a specific goal using the Ralph/dcode-tenacity loop:

```bash
# Method 1: Positional goal argument
.venv/bin/daz-ralph "Fix the bug in src/main.py" --tenacity

# Method 2: Using --prompt flag
.venv/bin/daz-ralph --prompt "Fix the bug in src/main.py" --tenacity

# Method 3: Interactive (goal inferred from first message)
.venv/bin/daz-ralph --tenacity
# Then type your goal when the prompt appears
```

## Using ralphdgx wrapper

The `ralphdgx run` command doesn't directly pass goals to `daz-ralph`. To use a goal with the wrapper:

```bash
# Call daz-ralph directly after installation
.venv/bin/daz-ralph "Your goal here" --tenacity

# Or activate the venv first
source .venv/bin/activate
daz-ralph "Your goal here" --tenacity
```

## Goal Loop Behavior

- The Ralph loop automatically wraps your task in a `goal → judge → nudge` cycle
- Maximum iterations controlled by `--goal-budget` (default: 20)
- Loop ends when judge confirms `done=true` or budget exhausted
- Use `--goal-budget N` to customize iteration limit