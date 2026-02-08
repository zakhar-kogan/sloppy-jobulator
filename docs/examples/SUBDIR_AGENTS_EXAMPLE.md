# Subdirectory AGENTS Example

Use local `AGENTS.md` files only when a subtree has additional constraints that are not global.

## Example: `apps/web/AGENTS.md`

```md
# AGENTS (apps/web)

Inherit root `/AGENTS.md`, then apply these additional rules for this subtree only.

## Scope
Applies to files under `apps/web/`.

## Additional constraints
1. Keep bundle-impactful dependencies explicit in PR notes.
2. Every UI behavior change must include an accessibility check.
3. Run frontend checks before finalizing:
- Build: `npm run build --workspace web`
- Test: `npm run test --workspace web`
- Lint: `npm run lint --workspace web`
```

## Example: `services/api/AGENTS.md`

```md
# AGENTS (services/api)

Inherit root `/AGENTS.md`, then apply these additional rules for this subtree only.

## Scope
Applies to files under `services/api/`.

## Additional constraints
1. Preserve API schema compatibility unless migration is explicitly approved.
2. Any DB migration must include rollback notes.
3. Run API checks before finalizing:
- Build: `npm run build --workspace api`
- Test: `npm run test --workspace api`
- Typecheck: `npm run typecheck --workspace api`
```
