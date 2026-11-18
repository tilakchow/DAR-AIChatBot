# Contributing to DAR

Contributions to the DAR AI Property Assistant are welcome.

## Development Workflow
1. Fork or branch from `master`.
2. Ensure all changes adhere to the RFC 2119 requirements in `docs/01-requirements/SRS.md`.
3. Verify that all unit and integration tests pass:
   ```bash
   pytest
   ```
4. Verify that no secrets or `.env` files are tracked:
   ```bash
   git status
   ```
5. Submit a pull request detailing the changes and traceability to DAR issue IDs.
