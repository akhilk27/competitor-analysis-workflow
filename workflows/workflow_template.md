# Workflow: [Name]

## Objective
What this workflow accomplishes. One or two sentences describing the goal.

## Required Inputs
| Input | Description | Example |
|-------|-------------|---------|
| `input_1` | What it is | `example_value` |
| `input_2` | What it is | `example_value` |

## Tools Used
| Tool | Purpose |
|------|---------|
| `tools/example_tool.py` | What it does |

## Steps

1. **[Step name]**
   - What to do
   - Which tool to run: `python tools/example_tool.py --arg value`
   - Expected output: description of what success looks like

2. **[Step name]**
   - What to do
   - Which tool to run: `python tools/another_tool.py`
   - Expected output: description of what success looks like

3. **[Deliver output]**
   - Where the final output goes (e.g., Google Sheet, local file, API response)

## Expected Output
Description of the final deliverable — format, location, and what "done" looks like.

## Edge Cases & Error Handling

- **[Error scenario]:** What to do if this happens. E.g., "If rate-limited, wait 60s and retry."
- **[Missing input]:** What to do if a required input is absent.
- **[Tool failure]:** How to debug. Check logs in `.tmp/`, re-run with `--verbose` flag, etc.

## Notes
Any quirks, rate limits, timing constraints, or lessons learned discovered during use.
Update this section as the system evolves.
