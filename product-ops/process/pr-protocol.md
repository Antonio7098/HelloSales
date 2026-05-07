# Pull Request Protocol

This protocol defines how to prepare, validate, and merge a pull request.

## Purpose

The PR agent:
1. Validates that all active CI checks pass locally
2. Ensures documentation is up to date with code changes
3. Verifies file paths and cross-references are valid
4. Commits all changes, pushes, opens PR, monitors CI, merges, and cleans up

## Input

1. **Working directory** - The repository with changes to PR
2. **Branch name** - Current feature branch
3. **Target branch** - Usually `main` or `master`

## Output

Merged PR and cleaned up branch.

## Procedure

### Step 1: Review Changes

Run git commands to understand what has changed:

```bash
git status                    # See all modified and untracked files
git diff                      # Show unstaged changes
git diff --staged             # Show staged changes
git log --oneline main..HEAD  # Show commits on this branch
```

Categorize changes:
- Code changes (backend, frontend)
- Documentation changes (READMEs, docs)
- Configuration changes
- New files
- Deleted files

### Step 2: Validate Active CI Checks Locally

Identify which CI workflows are active by checking `.github/workflows/`. For each active workflow, run the corresponding local checks.

Run appropriate checks based on what changed:
- Backend changes: run backend linters, type checkers, tests
- Frontend changes: run frontend linters, type checkers, tests
- Ops changes: run any relevant validation

If local checks fail, fix before proceeding.

### Step 3: Validate Documentation

For each changed file, inspect related documentation:

1. **Grep for file path references** - Search for paths to changed/deleted files:
   ```bash
   grep -r "path/to/deleted/file" --include="*.md" .
   grep -r "old-name" --include="*.md" .
   ```

2. **Check README files** - Read relevant READMEs to verify:
   - Documented paths still exist
   - Documented commands still work
   - Documented structure matches reality

3. **Key documentation to verify**:
   - Root `README.md`
   - `backend/README.md` (if backend changed)
   - `frontend/README.md` (if frontend changed)
   - `ops/README.md` (if ops changed)
   - `ops/process/README.md` (if process changed)
   - `ops/operational-contract/README.md` (if contracts changed)

4. **Check for broken internal links**:
   ```bash
   grep -r "](" --include="README.md" .
   ```

Update any stale references.

### Step 4: Verify Project Structure

Compare documented structure to actual structure:

```bash
ls -la                    # Root directory
ls -la backend/           # Backend structure
ls -la frontend/          # Frontend structure
ls -la ops/               # Ops structure
```

Ensure documentation matches reality.

### Step 5: Changelog Entry

**Note:** Changelog automation not yet implemented.

Before proceeding, note what would need changelog entry:
- New features
- Breaking changes
- Bug fixes
- Dependencies updates

Add placeholder note in PR description or create tracking issue.

### Step 6: Ensure All Changes Are Committed

Verify no uncommitted changes remain:

```bash
git status
```

Stage and commit any remaining changes with a descriptive message.

### Step 7: Push Branch

Push the branch to remote:

```bash
git push -u origin BRANCH_NAME
```

### Step 8: Create Pull Request

Use gh cli to create PR:

```bash
gh pr create --title "Description of changes" --body "$(cat <<'EOF'
## Summary
- Change 1
- Change 2

## Testing
- [ ] CI passes
- [ ] Local checks pass

## Notes
- Documentation updated
- Changelog: (note status)
EOF
)"
```

### Step 9: Monitor CI

Wait for all CI checks to pass:

```bash
gh pr checks
```

If any check fails, investigate and fix. Push additional commits as needed.

### Step 10: Merge PR

Once all checks pass, merge:

```bash
gh pr merge --admin --delete-branch
```

Or use:
```bash
gh pr merge --squash --delete-branch
```

### Step 11: Cleanup

Verify branch is deleted locally and remotely:

```bash
git branch -a
```

Pull latest to ensure local is up to date:

```bash
git pull origin main
```

## Notes

- Always verify what CI workflows exist in `.github/workflows/` - do not hardcode
- Run all local checks that correspond to active CI workflows
- Documentation must match code - update docs when code changes
- Keep PR description concise but complete
- Wait for green CI before merging