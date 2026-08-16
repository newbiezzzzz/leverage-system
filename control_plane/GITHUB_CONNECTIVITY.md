# GitHub Connectivity Protocol

Purpose: keep Project Leverage synchronized with the real repository and avoid stale/phantom GitHub state.

## Required pre-flight on every `Leverage Day X`

1. Verify the authenticated GitHub profile.
2. List repositories for the authenticated owner and confirm `newbiezzzzz/leverage-system` exists, is on `main`, and is accessible.
3. Fetch repository metadata using the canonical full name returned by the repository list.
4. Fetch a known lightweight file such as `README.md` from `main` to verify content access.
5. Only after these checks succeed, read or write project files.
6. After writes, re-fetch the changed file and confirm its new SHA/content before reporting completion.

## Failure handling

- If `get_repo` returns 404 but `list_repositories` shows the repository, treat it as a connector lookup glitch and use the canonical repository object from `list_repositories`.
- If `fetch_file` fails, stop writes and re-run the repository pre-flight.
- Never invent a repository path, branch, file SHA, commit result, or worker state.
- If GitHub cannot be verified, say so clearly and keep project work read-only until the connection is restored.

## Source-of-truth rule

GitHub is the factory-floor source of truth for Leverage code, dashboard state, worker registry, control-plane configuration, and committed research records.
