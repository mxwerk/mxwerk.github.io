---
title: agent-workorders — Java, Spring Boot & Domain-Driven Design
description: A work-order backend in Java 25 / Spring Boot 4.1 with DDD modules, an outbox for at-least-once dispatch, Keycloak, and a strict quality gate — plus the reusable deployment blueprint it builds on.
tags:
  - java
  - backend
  - devops
date: 2026-09-15
---

# agent-workorders — Java, Spring Boot & Domain-Driven Design

> **Note for readers:** a personal learning and portfolio project, private
> repository, **in development** (backend first, frontend planned).

## Why this project

Java/Spring was my thinnest area, so I chose deliberate depth over the course
minimum. The domain — operators, agents, and the work orders that link them — is
small enough to finish and rich enough to need real modelling: a lifecycle, rules
that span aggregates, and delivery to an external worker that can fail.

```
User ──< WorkOrder >── Agent
```

## Architecture

- **DDD modules in layers** (`domain / application / infrastructure / web`). The
  `user` and `project` modules are complete across all four layers; `agent` and
  `workorder` have domain, application and persistence, with their HTTP layer
  still to come.
- **Module boundaries are tested, not just drawn.** Modules reference each other
  only by id, dependencies are directional, and ArchUnit tests fail the build
  when a boundary is crossed.
- **A work-order state machine** with guards, plus explicit rules for invariants
  across aggregates and how they are locked.
- **Dispatch outbox.** Handing a work order to an agent must survive crashes. An
  outbox gives at-least-once delivery; the idempotency contract was designed
  *before* the durability mechanism, and a separate rule defines when a dispatch
  that can never succeed is abandoned (three ADRs and a research note).
- **Identity is not profile data.** Keycloak acts as the OIDC provider; the app
  references identity only through the token's subject. Consent is modelled as a
  timestamp, and withdrawing it erases the address rather than soft-deleting it.

## Quality gate

- Checkstyle (zero warnings), PMD and SpotBugs, JaCoCo coverage thresholds of
  85 / 80 / 85 / 85 % (instruction / branch / line / method) — all fail the
  build.
- JUnit 5 with Testcontainers against a real PostgreSQL; CI runs the *full*
  `./gradlew check`, no fast subset.
- **A root-caused CI failure.** Integration tests failed only in CI. The cause:
  Java's URI parser rejects an underscore in a Docker-in-Docker hostname that
  curl and the Docker CLI happily accept. The fix came with a fail-fast
  pre-check job, so that class of runner problem now fails in seconds with a
  clear message.
- Pull requests with a written branch report even in a one-person repo; **13
  ADRs**.

## The deployment blueprint behind it

Before starting, I extracted the deployment layer of an earlier project
([[projects/devops-portal|Studierendenportal]]) into a reusable, language-agnostic
blueprint. Every file was classified as portable, pattern-only or discard.
agent-workorders is its first consumer and the test of whether it really is
stack-agnostic (from Node/MongoDB to Java/PostgreSQL).

- **Build once, promote by digest** — enforced in two independent places (a CI
  guard and a compose guard), not just a convention.
- **CD dry-run by default** — the whole deploy chain runs green without a server
  or secrets; only an explicit switch arms the live apply.
- Compose for two environments, Kubernetes manifests with an HPA whose silent
  failure modes are documented in the manifest itself, a local kind cluster
  with monitoring, JMeter load tests, and CI rewritten for Forgejo Actions
  (not ported line by line).

The blueprint is validated with server-side dry runs and config checks. It is a
template, not a running deployment.

## Stack

| Area | Technology |
|---|---|
| Language & framework | Java 25, Spring Boot 4.1, Gradle (Kotlin DSL) |
| Persistence | PostgreSQL, Spring Data JPA (Hibernate), Flyway |
| Security | Keycloak (OIDC resource server) |
| Quality | Checkstyle, PMD, SpotBugs, JaCoCo, ArchUnit, JUnit 5, Testcontainers |
| Delivery | Forgejo Actions, Docker Compose, Kubernetes manifests (blueprint) |
