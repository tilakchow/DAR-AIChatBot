# DAR — DarGlobal AI Property Assistant
## Product Requirements Document (PRD)

**Issue:** DAR-6  
**Status:** In Progress  
**Author:** Tilak  
**Date:** 18 November 2026  
**Depends on:** DAR-5 (plan approved)

---

> [!IMPORTANT]
> This document follows the honesty rule from the project plan: every number is a **target**. No measurement exists yet. Any figure marked **Pending: DAR-\<n\>** will be filled once the referenced issue is Done.

---

## 1. Problem Statement

DarGlobal's HR team requires a live AI chatbot demonstration as part of the Junior AI Engineer — Applied AI technical assignment. The chatbot must answer questions about DarGlobal's property projects and Wasalt's property listings, using only publicly available data from those two websites. The reply, with a working URL, is due by **Friday, 20 November 2026**.

## 2. Users

| User | Context | Primary Need |
|------|---------|-------------|
| DarGlobal HR reviewer | Evaluating the assignment submission from a browser | Ask questions about DarGlobal projects and Wasalt listings; see cited, grounded answers |
| Prospective property buyer | Discovering properties in Dubai, Saudi Arabia and other markets | Find relevant listings, compare prices and areas, be directed to the live website for contact details |
| Developer / evaluator | Reviewing code quality, architecture and documentation | Clone and run the project locally; inspect the API; understand design decisions |

## 3. Goals

The six deliverables from the assignment email, in the order they must be achieved:

1. **Scrape** publicly available data from DarGlobal (`darglobal.co.uk`) and Wasalt (`wasalt.sa`).
2. **Build** an AI chatbot that answers questions from that data.
3. **Use a free model** available on OpenRouter — no paid API calls.
4. **Containerise** the application with Docker.
5. **Deploy** the solution (not just source code).
6. **Provide a working URL** so reviewers can test the chatbot directly.

## 4. Non-Goals

The following are explicitly out of scope for this assignment:

1. **Real-time listing updates.** The dataset is a static snapshot. Users are directed to the live website for current availability and pricing.
2. **User authentication or personalisation.** There are no accounts, saved searches or personalised recommendations.
3. **Commercial use of Wasalt data.** Wasalt's `llms.txt` prohibits commercial use. This project is a non-commercial technical demonstration only.
4. **Storing or displaying seller personal data.** Agent names, phone numbers and WhatsApp links found in Wasalt listings are dropped at extraction time and are never stored or shown.
5. **Investment or legal advice.** The system prompt explicitly prohibits the chatbot from giving investment or legal recommendations.
6. **Multi-language input routing.** The chatbot detects the user's language and responds in kind (English or Arabic), but it does not translate queries or perform cross-language search beyond what multilingual embeddings provide natively.
7. **Coverage beyond the two target sites.** Only DarGlobal and Wasalt data is indexed. The chatbot declines questions about other portals or general real estate markets.

## 5. Success Metrics

These targets will be measured in M7 (DAR-38). Until then, they are targets only.

| Metric | Target | Measured in |
|--------|--------|-------------|
| Answer accuracy on in-scope eval questions | ≥ 80% | Pending: DAR-38 |
| Correct "I don't know" / decline on out-of-scope and unanswerable questions | 100% | Pending: DAR-38 |
| Prompt-injection test cases blocked | 100% | Pending: DAR-39 |
| Answers citing at least one source link | ≥ 95% | Pending: DAR-38 |
| p95 end-to-end latency | ≤ 10 s | Pending: DAR-38 |
| Running cost | \$0 | Pending: DAR-31 |
| Live URL answers a smoke-test question on submission day | Yes | Pending: DAR-34 |
| Secrets committed to the repo | 0 | Pending: DAR-40 |

## 6. Constraints

These constraints are non-negotiable and come from the assignment email, the websites' crawl rules, or Wasalt's `llms.txt`.

| Constraint | Source | Tracked in |
|-----------|--------|-----------|
| Use a free OpenRouter model only | Assignment email | DAR-22 |
| Respect DarGlobal's `robots.txt` wildcard disallow rules | Recon (section 5 of project plan) | DAR-8 |
| Do not store Wasalt seller names or phone numbers | Wasalt `llms.txt` | DAR-12, DAR-15 |
| Show "Source: Wasalt.sa" attribution on Wasalt-based answers | Wasalt `llms.txt` | DAR-25 |
| Non-commercial use only | Wasalt `llms.txt` | Scope |
| Moderate crawl rate for Wasalt | Wasalt `llms.txt` | DAR-11 |
| Docker container must run as non-root | Security best practice | DAR-27 |
| No secrets in the repository | Security requirement | DAR-29, DAR-40 |
| Public HTTPS URL as the deliverable | Assignment email | DAR-32, DAR-34 |

## 7. User Stories

### Reviewer (primary path)
- **US-01** As a reviewer, I want to type a question about a DarGlobal project and receive an answer with a source link, so that I can verify the information against the original page.
- **US-02** As a reviewer, I want the chatbot to say "I don't know" or decline when I ask something outside the scraped data, so that I can trust it doesn't hallucinate.
- **US-03** As a reviewer, I want to test the chatbot from a public URL without installing anything, so that I can evaluate it quickly.

### Property seeker
- **US-04** As a property buyer, I want to ask "What villas are for sale in Riyadh under SAR 3 million?" and get a list with prices and areas, so that I can shortlist properties.
- **US-05** As an Arabic speaker, I want to ask questions in Arabic and read answers in Arabic, so that the tool is usable without switching language.

### Developer
- **US-06** As a developer, I want to clone the repo and run `docker compose up` to get the chatbot running locally, so that I can inspect and extend the code.
- **US-07** As a developer, I want to see the OpenAPI spec at `/openapi.yaml`, so that I can call the API from other tools.

## 8. Out-of-scope User Stories

The following were considered and rejected:

- Saving chat history or user sessions (requires authentication; out of scope).
- Scraping individual Wasalt listing pages (too many requests; use category pages with embedded JSONLD instead).
- Providing a mobile app (the assignment asks for a URL, not a native app).

## 9. Acceptance Criteria

This PRD is considered Done when:

- [ ] PRD lists target users (reviewers, prospective buyers) and at least three non-goals — ✓ see sections 2 and 4
- [ ] Success metrics match the table in the project plan — ✓ see section 5

> [!NOTE]
> Both checklist items above are met by this document. DAR-6 moves to **Done** once DAR-5 (plan approval) is closed.

---

*Traces to: DAR-6. Next: DAR-7 (SRS).*
