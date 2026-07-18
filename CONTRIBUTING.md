# Contributing / conventions

Solo project, but run like a team repo:

- **Branches:** `main` is protected in spirit — feature branches `feat/<slug>`, `fix/<slug>`,
  `chore/<slug>`; merge via PR once the GitHub remote exists.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`).
- **Before pushing:** `make lint typecheck test` must pass.
- **Docs discipline:** finishing a task = tick it in `docs/TASKS.md` + update `PROGRESS.md`
  in the same commit. Architecture changes update `docs/ARCHITECTURE.md` in the same PR.
- **Content:** lesson/drill positions must pass the python-chess validator before seeding.
