---
name: commit-and-push-with-tests
description: Runs tests before committing, fixes failures in a retry loop, then commits and pushes to the same current branch. Use when the user asks to commit and push safely with test-gated automation.
---

# Commit And Push With Tests

## Purpose

Create a commit and push it to the remote branch only after tests pass.

This skill is optimized for a non-interrupting flow:
- do not ask for confirmation before commit/push
- stop only when tests fail and a fix cannot be completed

## When to Use

Apply this skill when the user asks to:
- commit and push changes
- run tests before commit
- auto-fix test issues, rerun, then continue
- push to the same branch currently checked out locally

## Workflow

Run from repository root.

Task Progress:
- [ ] Step 1: Determine current branch and sync state
- [ ] Step 2: Run tests before commit
- [ ] Step 3: If tests fail, analyze and fix
- [ ] Step 4: Rerun tests until pass
- [ ] Step 5: Commit staged changes
- [ ] Step 6: Push to remote same branch

### Step 1: Determine current branch and sync state

1. Get current branch:
   - `git branch --show-current`
2. Ensure branch name is non-empty. If empty (detached HEAD), stop and report.
3. Check working tree:
   - `git status --short`
4. If nothing to commit, stop and report `No changes to commit`.

### Step 2: Run tests before commit

1. Run the project's standard test command first:
   - default: `pytest`
2. If the repository uses another required command (for example `python -m pytest` or `make test`), prefer the project standard.

Pass criteria:
- test command exits with code 0

### Step 3: If tests fail, analyze and fix

When tests fail:
1. Read the first failing test and root error.
2. Implement the smallest correct fix.
3. Avoid unrelated refactors.
4. Keep changes focused and explicit.
5. If failure is environmental or cannot be resolved safely, stop and report blocker.

### Step 4: Rerun tests until pass

Use a strict retry loop:
1. Rerun failing tests (targeted command) for fast feedback.
2. After targeted pass, rerun full test command.
3. Continue until full test suite passes or a hard blocker is found.

Never continue to commit while tests are failing.

### Step 5: Commit staged changes

1. Stage relevant files:
   - `git add <files>`
2. Create a meaningful, business-friendly commit message.
3. Commit:
   - `git commit -m "<message>"`

Rules:
- Do not include secrets or credentials.
- Do not amend existing commits unless explicitly requested.
- Message must explain business impact, not only technical changes.
- Avoid vague messages like `fix`, `update`, or `changes`.

Commit message format:
- First line: short action + business context
- Optional second line: why this matters for users, operations, or compliance

Good examples:
- `Improve invoice approval guardrails to prevent over-budget payments`
- `Strengthen policy validation for vendor invoices to reduce processing risk`
- `Fix audit event capture so finance reviews remain traceable`

### Step 6: Push to remote same branch

1. Push current local branch to the branch with the same name on `origin`.
2. If upstream is missing, set it while pushing:
   - `git push -u origin HEAD`
3. Otherwise:
   - `git push`

## Decision Rules

- Continue automatically through test, fix, commit, and push without asking for permission.
- Pause and report only when:
  - tests fail and cannot be fixed safely
  - git push is rejected (permissions, conflicts, hooks, network)
  - repository state is invalid (detached HEAD, no changes)

## Output Format

Use this response structure:

```markdown
## Commit/Push Result
- Branch: <branch_name>
- Tests: PASS | FAIL
- Commit: <commit_sha or not created>
- Push: SUCCESS | FAILED

## Actions Taken
- <short bullet list of key commands and fixes>

## Blockers
- None | <clear blocker details>
```
