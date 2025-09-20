# OpenAI Backend Support - Step 1 Solution Assessment

## Problem Statement
Anthropic is the only configured AI provider; we need an OpenAI option without disrupting existing prayer generation flows.

## Option A — Dual Provider Service Layer (Recommended)
- **Pros**: Centralizes provider selection in one service; keeps existing Anthropic calls working; supports future providers via plug-in pattern; minimal template changes.
- **Cons**: Requires careful refactor of `generate_prayer` path; needs new configuration management and validation logic.

## Option B — Parallel OpenAI-Specific Pipeline
- **Pros**: Fastest to prototype by duplicating current Anthropic flow with OpenAI-specific helpers; isolates API differences.
- **Cons**: Duplicated logic increases drift risk; harder to maintain prompts and safety controls; more template branching.

## Option C — External Worker/Queue
- **Pros**: Decouples AI calls from web thread; allows per-provider scaling, retries, and monitoring.
- **Cons**: Significant new infrastructure (queue, worker process); overkill for initial provider toggle; delays delivery.

## Recommendation
Adopt Option A. Build a provider-agnostic prayer generation service with driver classes for Anthropic and OpenAI, selected via configuration (env + CLI checks).
This balances maintainability and near-term effort while leaving room for background workers later if needed.
