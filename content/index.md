---
title: Maximilian — Portfolio
---

# Hi, I'm Maximilian

Media Informatics student at BHT Berlin (6th semester), looking for a software engineering internship.

I run my own development system, and every change in it has to pass checks I built. One of them compares what AI agents *claim* against real git changes and test runs — I measured its recall: 78 % (7 of 9) against 33 % for a plain pattern-matching baseline.

That is how I approach software in general: understand the root, then derive the rest.

---

## Projects

### Self-hosted agent platform

#### [[projects/claude-setup|Engineering AI-Assisted Development]]
A personal SDLC system around Claude Code: spec-driven workflow, deterministic quality gates, 96 ADRs — and an autonomous issue-to-pull-request chain with separate bot identities, confirmation floors, and merge decisions measured in shadow mode before they get authority.

#### [[projects/agent-warden|agent-warden]]
Checks what coding agents *claim* against real evidence, using two tiers of self-hosted LLMs. Measures its own judge (78 % recall vs. 33 % for a regex baseline) instead of trusting it.

#### [[projects/agent-cockpit|agent-cockpit]]
Web console to browse, launch and live-track the agents: React, Express 5, SQLite, 468 passing unit tests, accessibility and visual-regression gates.

### Other projects

#### [[projects/agent-workorders|agent-workorders]]
Java 25 / Spring Boot 4.1 backend with DDD modules guarded by ArchUnit, an outbox for at-least-once dispatch, Keycloak, and a strict quality gate — built on a deployment blueprint I extracted from an earlier project.

#### [[projects/campusos|CampusOs]]
Full-stack student app: Next.js 16, Supabase (self-hosted), Feature-Sliced Design, Playwright E2E. Built in a team of six.

#### [[projects/devops-portal|Studierendenportal — DevOps Evolution]]
Took an existing student portal through two architectural phases (Turborepo monorepo → polyrepo with OpenAPI contracts). GitLab CI/CD, Docker, Kubernetes (local kind cluster, HPA), Playwright, SemVer releases.

---

## Stack

TypeScript · Python · Java · React · Next.js 16 · Spring Boot 4 · PostgreSQL · Keycloak · Docker · Kubernetes · GitLab CI/CD · Forgejo Actions · Ollama · Playwright

---

## Background

Eleven years of part-time work alongside school and university, without a break — delivery, stadium catering, security, logistics, and four years behind a bar. Two short IT internships at Bosch pointed me toward software.

---

## Contact

- LinkedIn: [linkedin.com/in/maximilian-s-068285438](https://www.linkedin.com/in/maximilian-s-068285438/)
