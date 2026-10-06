---
title: Studierendenportal — DevOps Evolution
description: Taking a student application portal through two architectural phases — Turborepo monorepo and polyrepo with OpenAPI contracts.
tags:
  - web
  - devops
  - architecture
date: 2026-06-30
---

# Studierendenportal — DevOps Evolution

A project from the Web Engineering 2 (WE2) course at BHT Berlin. The starting point was an existing student applicant portal; the assignment, in the course's own words, was to bring it to production
readiness. <!-- claim-ok: describes the brief, not a claim about the result --> We did this in two distinct architectural phases, which ended up being a useful exercise in evaluating trade-offs between monorepo and polyrepo structures.

## Phase 1 — Turborepo Monorepo

Consolidated the codebase into a **pnpm/Turborepo monorepo** with five packages (frontend, backend, shared types, contracts, test-utils). Benefits: single-repo atomic changes, shared TypeScript types across package boundaries, unified CI pipeline.

## Phase 2 — Polyrepo with OpenAPI Contracts

Migrated to a polyrepo structure with **contract-first API design**: an OpenAPI/Swagger spec became the single source of truth between frontend and backend, replacing the shared-types package with a generated client. This inverted the coupling — each service can evolve independently as long as it satisfies the contract.

Running both phases made the trade-offs concrete rather than theoretical.

## Notable engineering work

**Authentication:** OAuth 2.0 with PKCE via Arctic, JWT session management, Zod input validation throughout. Penetration testing pass before final submission.

**Real-time:** Socket.IO for live updates.

**E2E testing:** Playwright with Page-Object-Model and `globalSetup` for shared test setup. Framework evaluation: Selenium / Cypress / Playwright — Playwright won on DX and reliability.

**CI/CD:** GitLab CI/CD pipelines with Docker Compose environments (dev / prod / spec). gitleaks for secret scanning in every pipeline run.

**Release management:** Semantic versioning (SemVer) with release candidates (RC), CHANGELOG generation, handoff bundles for deployment.

**Kubernetes & load testing:** a local kind cluster with a Horizontal Pod Autoscaler (3–8 replicas at 70 % CPU), JMeter load tests against the ingress, and Prometheus/Grafana monitoring.

**Afterlife:** I later extracted this deployment layer into a reusable, language-agnostic blueprint (digest-pinned images, CD dry-run by default), which a Java/Spring project now builds on — see [[projects/agent-workorders|agent-workorders]].

## Stack

| Area | Technology |
|---|---|
| Frontend | TypeScript, React, Vite |
| Backend | Express.js, Node.js |
| Auth | Arctic (OAuth 2.0 / PKCE), JWT, bcryptjs |
| Realtime | Socket.IO |
| Validation | Zod |
| Monorepo | pnpm, Turborepo |
| API contracts | OpenAPI / Swagger (contract-first) |
| Testing | Playwright (E2E), Vitest, Supertest |
| CI/CD | GitLab CI/CD, Docker Compose, gitleaks |
| Orchestration | Kubernetes (kind), HPA |
| Load & monitoring | JMeter, Prometheus, Grafana |
