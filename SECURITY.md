# Security Policy

## Reporting Security Issues
If you discover a potential security vulnerability or credential leak in this project, please report it directly to the repository maintainer:
- Primary Contact: Tilak (Project Lead)
- Response Target: Within 24 hours

## Security Controls Implemented
1. Zero secrets in version control: All API keys must be provided via environment variables.
2. Prompt injection defense: Regex filters reject adversarial prompts before reaching LLMs.
3. Untrusted context delimiters: Scraped content is isolated from instruction context.
4. Privacy compliance: No personal names, phone numbers, or contact details are retained from scraped property portals.
