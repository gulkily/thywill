# Thywill Stop Command - Feature Description

## Problem
Local developers lack a streamlined way to terminate the development server started via `./thywill start`, leading to manual process hunting and inconsistent cleanup.

## User Stories
- As a developer, I want to stop the dev server with a single CLI command so that I can quickly reset my workspace.
- As a developer, I want the stop command to confirm whether a server was running so that I know if further action is needed.
- As a developer, I want the stop command to avoid killing unrelated processes so that my environment stays stable.

## Core Requirements
- Provide a `./thywill stop` command accessible through the existing CLI dispatcher.
- Detect the dev server process started by `./thywill start` and terminate it gracefully.
- Handle both foreground and orphaned uvicorn processes launched by the CLI without affecting unrelated services.
- Exit with a clear success or warning message indicating the outcome.

## User Flow
1. Developer runs `./thywill start` to launch the dev server.
2. Developer later executes `./thywill stop` from the project root.
3. CLI locates the running dev server process, if any, and issues a graceful termination.
4. CLI reports success or explains that no matching server was found.

## Success Criteria
- Running `./thywill stop` after `./thywill start` shuts down the uvicorn process within a few seconds.
- Running `./thywill stop` when no dev server is active exits cleanly with an informative message.
- Integration tests or manual verification confirm the command only targets expected uvicorn instances.
