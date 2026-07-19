# Releasing

This checklist describes how to prepare and publish a new tmux-flash-copy release. The repository does not currently publish a Python package to PyPI; releases are distributed through Git tags and GitHub.

## Table of contents

- [Prepare the release](#prepare-the-release)
- [Update the version](#update-the-version)
- [Run the checks](#run-the-checks)
- [Review and commit the release](#review-and-commit-the-release)
- [Tag and publish the release](#tag-and-publish-the-release)
- [Verify the release](#verify-the-release)
- [Related documentation](#related-documentation)

## Prepare the release

1. Confirm that the intended release changes have been merged and the release branch is up to date.
2. Choose the next version according to semantic versioning.
3. Review the changes since the previous tag and prepare the release notes.

Set the previous tag and new version once for use throughout the release:

```bash
export PREVIOUS_TAG=v1.3.1
export VERSION=1.4.0
```

Review the changes included in the release:

```bash
git log --oneline "${PREVIOUS_TAG}..HEAD"
git diff --stat "${PREVIOUS_TAG}..HEAD"
```

## Update the version

Use `uv version` so the project metadata and lockfile stay synchronized:

```bash
uv version "${VERSION}"
uv lock
```

Confirm that both `pyproject.toml` and the `tmux-flash-copy` package entry in `uv.lock` contain the new version:

```bash
uv version
uv lock --check
git diff -- pyproject.toml uv.lock
```

## Run the checks

Run the same checks as CI:

```bash
uv run ty check --output-format=github
uv run ruff check --output-format=github
uv run ruff format --check
uv run pytest --cov=src --cov-report=term-missing --cov-report=xml
```

## Review and commit the release

Review the complete release diff before committing it:

```bash
git status --short
git diff --check
git diff
```

Commit the version change and any release documentation using the repository's normal contribution workflow. Merge the release changes into `main` before creating the tag.

## Tag and publish the release

Create an annotated tag from the release commit, using a `v` prefix to match the existing tags:

```bash
git tag -a "v${VERSION}" -m "Release v${VERSION}"
git push origin "v${VERSION}"
```

Create the matching GitHub release and include the prepared release notes. With the GitHub CLI, generated notes can be used as a starting point:

```bash
gh release create "v${VERSION}" --title "v${VERSION}" --generate-notes --draft
```

Review the generated notes and add any necessary context, upgrade guidance, or known limitations before publishing the draft release.

## Verify the release

1. Confirm that the new tag and GitHub release point to the intended commit.
2. Update the plugin through TPM or install it in a clean tmux environment.
3. Reload the tmux configuration and confirm that the default binding launches tmux-flash-copy.
4. Perform a basic word copy and range-selection smoke test.

## Related documentation

- [README](../README.md)
- [Configuration](CONFIGURATION.md)
- [Clipboard implementation](CLIPBOARD.md)
- [Debugging guide](DEBUGGING.md)
- [Testing guide](TESTING.md)
- [Semantic Versioning](https://semver.org/)
- [uv package versioning](https://docs.astral.sh/uv/guides/package/#updating-your-version)
