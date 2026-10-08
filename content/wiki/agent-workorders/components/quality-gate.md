---
title: The quality gate
description: One Gradle command, check, fails the build on a static-analysis finding, a coverage shortfall, a broken architecture rule or a failing integration test against a real PostgreSQL, and CI runs that same command.
draft: false
cites:
  - path: build.gradle.kts
    lines: 5-13, 19-23, 45-48, 52-63, 65-111, 113-165
  - path: config/checkstyle/checkstyle.xml
    lines: 6-9, 23, 34-38, 63-65
  - path: config/checkstyle/checkstyle-suppressions.xml
    lines: 7-11
  - path: config/pmd/ruleset.xml
    lines: 8-57
  - path: config/pmd/ruleset-test.xml
    lines: 8-51
  - path: .forgejo/workflows/ci.yml
    lines: 18-21, 36-37, 100-102, 128-129, 193-203, 229-230, 275-289
  - path: .forgejo/ci-image/Dockerfile
    lines: 33-36, 58-66
  - path: src/test/java/dev/…/agentworkorders/architecture/ArchitectureFitness.java
    lines: 19-28, 38-57, 60-68, 75-86, 97-107, 119-181, 192-199, 206-226
  - path: src/test/java/dev/…/agentworkorders/architecture/ModuleWallProbeTest.java
    lines: 12-25, 33-37, 47-97
  - path: src/test/java/dev/…/agentworkorders/TestcontainersConfiguration.java
    lines: 23-30, 79-86, 101-120, 127-134, 147-185
  - path: src/main/java/dev/…/agentworkorders/config/SchedulingConfiguration.java
    lines: 15-27
  - path: src/main/resources/application.properties
    lines: 1-61
  - path: .claude/rulesets.lock.yaml
    lines: 88-98, 106-121
  - path: docs/charter.md
    lines: 61-65, 86-91, 119-120
  - path: docs/adr/001-web-rather-than-interface-as-the-layer-name.md
    lines: 11-23
  - path: docs/adr/002-kotlin-gradle-dsl-over-the-groovy-default.md
    lines: 11-23
  - path: docs/adr/003-java-25-and-spring-boot-4-1.md
    lines: 20-22
verified_at: 262e98e
---

# The quality gate

> **TL;DR** — The build file wires three static analysers, a four-counter coverage rule, the
> architecture rules and the integration tests into Gradle's `check`. The CI workflow's `build` job
> runs `./gradlew check` and nothing narrower. The thresholds live in the build file, so they travel
> with each commit. The integration tests start a PostgreSQL and a Keycloak container; the committed
> application configuration itself names no database.
> [[wiki/agent-workorders/index|↑ Wiki]]

## What it is

`build.gradle.kts` applies the `checkstyle`, `pmd` and `jacoco` plugins and the SpotBugs plugin, on
a Java 25 toolchain. Its own comment states the division of labour: Checkstyle reads text, PMD reads
the syntax tree, SpotBugs reads compiled bytecode, and all three fail the build. `check` is also
made to depend on the coverage verification task, which depends on the coverage report, which
depends on `test`.

The CI workflow describes its `build` job as the same command a developer runs, with nothing split
out into a fast subset.

## How it works

**Static analysis.**

| Tool | Version | Configuration | What makes it fail the build |
| --- | --- | --- | --- |
| Checkstyle | 13.9.0 | Google Java Style checks, line length 100 | severity property set to `error`, `maxWarnings = 0` |
| PMD | 7.26.0 | categories `bestpractices`, `design`, `errorprone`, whole | `isIgnoreFailures = false` |
| SpotBugs | 4.10.3 | effort `MAX`, report level `DEFAULT` | `ignoreFailures = false` |

The Checkstyle severity matters: the Google configuration defaults it to `warning`, which would
report and never fail. One suppression exists: the three missing-Javadoc checks are off for test
sources. PMD has a separate ruleset for tests, wired through `pmdTest`. Each PMD exclusion carries
its reason in a comment; two rules are re-added with a changed bound (`TooManyMethods` at 20 for
production code, `UnitTestContainsTooManyAsserts` at 3 for tests).

**Coverage.** JaCoCo 0.8.15, one rule with four limits:

| Counter | Minimum |
| --- | --- |
| `INSTRUCTION` | 0.85 |
| `BRANCH` | 0.80 |
| `LINE` | 0.85 |
| `METHOD` | 0.85 |

One class is excluded from the measured set: the application's bootstrap class, whose `main` only
delegates to Spring.

**The architecture test.** `ArchitectureFitness` holds seven ArchUnit rules (7 `@ArchTest` fields,
counted with grep) over the main classes only:

| Rule | Refuses |
| --- | --- |
| `DOMAIN_IS_FRAMEWORK_FREE` | a `domain` class depending on Spring, JPA, validation, Hibernate or Jackson |
| `DOMAIN_DOES_NOT_REACH_OUTWARD` | a `domain` class depending on `application`, `infrastructure` or `web` |
| `DOMAIN_TAKES_ITS_CLOCK_FROM_THE_CALLER` | a `domain` class calling `Instant.now`, `LocalDate.now` or `LocalDateTime.now` |
| `DOMAIN_NAMES_NEIGHBOURS_ONLY_BY_ID` | a `domain` class naming another module's type, unless its simple name ends in `Id` |
| `MODULE_DEPENDENCIES_ARE_DECLARED` | any cross-module dependency that is not on the allowlist written in the rule |
| `MODULE_DEPENDENCIES_ARE_ACYCLIC` | a cycle between modules, `Id` types exempt |
| `LAYERS_POINT_INWARD` | access to `web` or `infrastructure` from any layer; access to `application` from `domain` |

The allowlist is the module graph: work-order to agent, work-order to project, and the work-order
web layer to the user module's application and domain. [[wiki/agent-workorders/concepts/modules-by-id]] and
[[wiki/agent-workorders/components/dispatch-seam]] explain two of those edges. `ModuleWallProbeTest` runs the three module
rules against small probe modules kept in the test source set: each rule once over a legal shape and
at least once over a violating one (the allowlist rule over two), so each of those three rules has
been seen to reject something.

**Integration tests on a real database.** `TestcontainersConfiguration` defines a
`postgres:18-alpine` container annotated `@ServiceConnection` and a Keycloak 26.7.1 container that
imports a realm file. The build copies that file onto the test classpath from the repository's
`deployment/compose/dev/realm` directory. The issuer property is registered at startup from the
container's mapped port, and tests obtain access tokens from the container with a password grant
instead of forging them. Each container may be started up to 3 times. The scheduler is off under the
`test` profile, so no background writer runs beside a test.

**CI.** The workflow runs on pushes to `main` and on pull requests and has four jobs:
`runner-plumbing`, `branch-report` (pull requests only), `ruleset-gate` and `build`. `build` waits
for `runner-plumbing`, checks that its own container reaches the Docker daemon, runs `./gradlew
--no-daemon check`, and uploads `build/reports/` and `build/test-results/` when the job fails. The
job image is a JDK 25 base with `git`, `nodejs`, `python3` and `python3-yaml` added; Gradle comes
from the wrapper. `ruleset-gate` is a separate mechanism, described in
[[wiki/agent-workorders/decisions/ci-judges-committed-artifact]].

## What it costs / limits

- **Four of the seven architecture rules have no can-fail probe.** `ModuleWallProbeTest` references
  the two module-graph rules and the neighbour-by-id rule only; the framework, outward, clock and
  layer rules pass against this tree without a test that shows them rejecting a violation.
- **The database in the tests is provisioned by the tests.** The committed `application.properties`
  contains no datasource setting (grep for `datasource` and `jdbc` finds nothing), so a green
  `check` says the code works against a container the test suite started, not against a configured
  deployment.
- **The generic gate runner's own lint, coverage and architecture gates do not apply here.** The
  lock file records why: the lint gate cannot drive Gradle, the coverage gate expects a file this
  build does not write, and the architecture gate's rules match no Java file. `check` is what
  enforces all three.
- This page reads the build configuration. No run of `check` was made while writing it.

## Later changes

- **Layer name.** The charter's layout ends in `interface`; the layer rule names `web`, per ADR 001.
- **Build language.** The charter defaulted to the Groovy DSL and left it open; ADR 002 chose the
  Kotlin DSL. ADR 002 speaks of four static-analysis tools; the build file configures three.
- **Versions and thresholds.** The charter pins no versions; ADR 003 chose Java 25 and Spring Boot
  4.1, which the build file declares. The charter's 85/80/85/85 is what the build file enforces.
- **Trunk mode.** The charter says CI gates before merge in trunk mode. The workflow also runs on
  pull requests; see [[wiki/agent-workorders/decisions/pull-requests-single-person-repo]].
