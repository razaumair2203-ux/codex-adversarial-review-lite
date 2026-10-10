> Historical launch draft for protocol 1. Runtime/setup claims below are superseded by [the current README](../README.md).

# Launch Copy

## Short Post

```text
I built Codex Adversarial Review - Lite: a Claude Code skill that asks Codex CLI to review Claude's code before you trust it.

It is intentionally small:
- Claude Code = builder
- Codex CLI = independent reviewer
- Cross-platform (Windows, macOS, Linux, WSL)
- mutation checks
- report before fixes
- user sign-off before code changes

Build with Claude. Before you trust it, run:
/codex-adversarial-review-lite audit
```

## Hacker News

Title:

```text
Show HN: A Claude Code skill that makes Codex review Claude's code
```

Body:

```text
I made a small Claude Code skill for agentic coding users who want a second model to audit code before trusting it.

The workflow is intentionally narrow: Claude Code acts as the builder, Codex CLI acts as an independent reviewer, and the skill forces a report/sign-off step before fixes are applied.

It handles platform-specific sandbox limitations (bwrap/bubblewrap is unavailable on Windows and some macOS setups). The skill uses pragmatic defaults plus mutation checks rather than pretending this is a security boundary.

It is not a replacement for tests or human review. It is a guardrail for hallucinated APIs, scope creep, weak verification, and over-obedient AI-on-AI feedback loops.
```

## Blog Outline

Title:

```text
Why I Make GPT Review Claude's Code Before I Trust It
```

Outline:

- AI coding agents are fast, but speed hides mistakes.
- Same-agent self-review often shares the original assumptions.
- A second model gives a different failure surface.
- Reviewer findings are not commands; they need builder verification.
- Platform sandbox limitations need pragmatic handling.
- The skill packages the boring safety steps people skip manually.
- Demo: run `/codex-adversarial-review-lite audit`.

## LinkedIn

Use [linkedin-post.md](linkedin-post.md) as the first LinkedIn launch draft. It is written for non-specialist readers who understand the pain of trusting AI-generated work but do not want a deeply technical post.

Recommended LinkedIn images:

- [assets/audit-report-preview.jpg](assets/audit-report-preview.jpg) for the main launch post.
- [assets/audit-report-anatomy.jpg](assets/audit-report-anatomy.jpg) for a follow-up post about the audit report format.
