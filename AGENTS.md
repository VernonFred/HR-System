# Project Operating Rules

## Deployment Handoff Workflow

After a development thread has completed a change, committed it, and pushed it to GitHub, it must hand deployment work to this project's deployment thread instead of deploying from the development thread.

Default deployment thread:

- `019f3a3c-c454-7420-b389-8f3ec23abd9b`

The development thread must send the deployment thread a concise handoff message containing all of the following:

- Commit hash and commit subject.
- Branch and remote repository.
- Changed files, grouped by service or area.
- Services that need deployment, for example frontend, backend, database migration, static assets, or docs.
- Backend deployment scope. In this project, backend deployment should generally deploy only changed backend files unless a full restart, dependency install, migration, or broader sync is explicitly needed.
- Frontend deployment scope. If frontend source changed, the deployment thread should build and deploy the frontend using the project's existing production workflow.
- Verification paths or commands, including URLs/pages/API routes that should be checked after deployment.
- Any migration, environment variable, dependency, cache, restart, or rollback notes.
- Known unrelated local working tree changes that must not be included.

Use the GitHub commit as the source of truth for deployment. Do not deploy uncommitted local changes from the development thread's working tree.

Recommended handoff template:

```text
Please deploy the latest pushed change.

Commit:
- <hash> <subject>

Branch / remote:
- <branch>
- <remote-url>

Changed files:
- frontend: <files>
- backend: <files>
- other: <files>

Services to deploy:
- <frontend/backend/etc.>

Backend deployment scope:
- Deploy only changed backend files unless a full backend sync or restart is required.

Verification:
- <page or route>
- <API route or command>
- <expected behavior>

Notes:
- <migrations/env/cache/restart/rollback/unrelated changes>
```

The deployment thread should confirm the commit it deployed, list the files or services deployed, run the stated verification, and report any warnings or follow-up actions.
