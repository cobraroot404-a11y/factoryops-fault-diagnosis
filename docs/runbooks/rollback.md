# Runbook: rollback

```bash
./scripts/rollback.sh
```

This redeploys the previously recorded release tag
(`infra/compose/PREVIOUS_RELEASE`, written by `scripts/deploy.sh` right before
it overwrites `CURRENT_RELEASE`), then health-checks it the same way
`deploy.sh` does.

## Rollback limits — read before relying on this

- **Only one level of history is kept.** There is no rollback stack; running
  `deploy.sh` twice and then `rollback.sh` returns you to the *first*
  deploy's tag, not further back. Keep track of tags yourself
  (`docker images | grep factoryops`) if you need deeper history.
- **Application images only.** Rollback does not touch the database schema.
  If the release you're rolling back FROM added a migration that the release
  you're rolling back TO doesn't understand, rolling back the app without
  also reverting the migration can break it. This project's migrations are
  additive-only by convention (no destructive schema changes) specifically so
  that an older app version keeps working against a newer schema — but this
  is a convention, not something enforced automatically.
- **Persistent data (readings, incidents, tickets) is never rolled back.**
  Rollback changes which code is running, not what's in the database.
- The previously built image must still exist in this machine's local Docker
  image cache (`docker compose ... build` from the earlier deploy created it;
  nothing here re-pulls it from anywhere, since there is no remote registry in
  this zero-cost setup).
