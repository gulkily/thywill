# Thywill Stop Command - Development Plan

## Stage 1: Process discovery and design
- Goal: Understand how `./thywill start` spawns uvicorn, decide how to reliably identify and stop that process, and outline CLI help updates.
- Dependencies: Step 2 approval (complete), existing `cmd_start` implementation.
- Changes: Review `cmd_start` to confirm command signature; determine PID storage vs. process search; draft stop command interface and messaging.
- Testing: Manual verification of current start command behaviour; confirm uvicorn process command-line structure.
- Risks: Uvicorn may run in foreground making graceful stop via CLI tricky; PID files risk stale entries.

## Stage 2: Implement `cmd_stop`
- Goal: Add CLI handler that finds the running dev server and stops it cleanly.
- Dependencies: Stage 1 design choice.
- Changes: Update `thywill` script with new `cmd_stop` function, dispatch case, and documentation in `show_help`; implement PID tracking or targeted process kill; ensure compatibility with existing start behaviour.
- Testing: Start server via `./thywill start`, run `./thywill stop`, verify exit codes/messages; run stop twice to confirm graceful warning when nothing running.
- Risks: Misidentifying processes and terminating unrelated uvicorn instances; improper signal handling leaving zombie processes.

## Stage 3: Documentation and validation
- Goal: Align docs and QA with new command.
- Dependencies: Stage 2 implementation.
- Changes: Update README or relevant docs mentioning dev workflow; refresh `AI_PROJECT_GUIDE.md` and `CLAUDE.md` per repo expectations; note usage in `thywill` help output.
- Testing: Run `./thywill help` to confirm help text; basic lint/shellcheck if available; manual doc review.
- Risks: Missing documentation sync; shellcheck might flag new logic.
