---
title: The user module
description: A user is the identity provider's subject claim plus a profile and an optional address that this application owns, created the first time a token for that subject arrives.
draft: false
cites:
  - path: docs/charter.md
    lines: 24-25, 61, 67-82
  - path: docs/adr/001-web-rather-than-interface-as-the-layer-name.md
    lines: 11-23
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/User.java
    lines: 6-46, 63-66, 95-110, 120-163, 249-253, 349-369
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/KeycloakSubject.java
    lines: 3-26
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/UserId.java
    lines: 6-36
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/UserStatus.java
    lines: 3-16
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/Address.java
    lines: 6-68, 92-98
  - path: src/main/java/dev/…/agentworkorders/modules/user/application/ProvisionUser.java
    lines: 9-29, 45-66
  - path: src/main/java/dev/…/agentworkorders/modules/user/application/UserRepository.java
    lines: 7-34
  - path: src/main/java/dev/…/agentworkorders/modules/user/application/ChangeAddress.java
    lines: 9-24, 54-59
  - path: src/main/java/dev/…/agentworkorders/modules/user/application/ForgetAddress.java
    lines: 8-19, 45-49
  - path: src/main/java/dev/…/agentworkorders/modules/user/infrastructure/JpaUserRepository.java
    lines: 23-54
  - path: src/main/java/dev/…/agentworkorders/modules/user/infrastructure/UserEntity.java
    lines: 17-59, 102-120
  - path: src/main/java/dev/…/agentworkorders/modules/user/infrastructure/UserModuleConfiguration.java
    lines: 12-42
  - path: src/main/java/dev/…/agentworkorders/modules/user/web/UserController.java
    lines: 36-38, 56-167
  - path: src/main/java/dev/…/agentworkorders/modules/user/web/UserResponse.java
    lines: 10-25
  - path: src/main/java/dev/…/agentworkorders/config/SecurityConfiguration.java
    lines: 20-34, 82-131, 146-171, 188-194
  - path: src/main/resources/application.properties
    lines: 12-35
  - path: src/main/resources/db/migration/V1__create_users.sql
    lines: 10-51
  - path: src/main/java/dev/…/agentworkorders/modules/workorder/web/WorkOrderController.java
    lines: 42-48, 226-236
  - path: src/test/java/dev/…/agentworkorders/modules/user/application/ProvisionUserTest.java
    lines: 46-64
  - path: src/test/java/dev/…/agentworkorders/modules/user/web/UserEndpointIntegrationTest.java
    lines: 46-52, 60-63, 83-103, 219-224
  - path: src/test/java/dev/…/agentworkorders/modules/user/infrastructure/JpaUserRepositoryIntegrationTest.java
    lines: 189-198
  - path: src/test/java/dev/…/agentworkorders/config/WriteRouteGuardIntegrationTest.java
    lines: 71-91
  - path: src/test/java/dev/…/agentworkorders/architecture/ArchitectureFitness.java
    lines: 161-178
verified_at: 262e98e
---

# The user module

> **TL;DR** — The identity provider (Keycloak) owns login, password, email and roles. This
> application stores one fact about that identity, the token's `sub` claim, and next to it the data
> it owns itself: a display name, an optional postal address, consent timestamps and a status. There
> is no registration endpoint; the first authenticated request from an unknown subject creates the
> row. Every user route is `/me`, resolved from the token, so a caller can only reach their own
> record.
> [[wiki/agent-workorders/index|↑ Wiki]]

## What it is

The charter splits the facts in two: the identity provider owns the auth identity, the application
`User` owns profile and domain data and refers to the identity through the `sub` claim, and no auth
field is duplicated into the application database.

The code follows that split. `KeycloakSubject` wraps the raw `sub` string and is described in its
own Javadoc as the only auth fact the application stores. It stays a string, not a UUID, because
`sub` is opaque by specification. `UserId` is a separate, application-generated UUID, created in the
domain before the aggregate is ever persisted.

The aggregate `User` holds:

| Field | Notes |
| --- | --- |
| `id`, `keycloakSubject`, `createdAt` | fixed at registration |
| `displayName` | non-blank, trimmed, at most 120 characters |
| `address` | optional; `null` until the user supplies one |
| `consent` | three timestamps, see [[wiki/agent-workorders/decisions/consent-is-a-timestamp]] |
| `status` | `ACTIVE` or `DEACTIVATED` |
| `updatedAt` | moved by every state change |

`Address` is a record of `line1`, `line2`, `postalCode`, `city`, `region` and `countryCode`. Four
components are required; `line2` and `region` are normalised to `null` when blank. The country code
is upper-cased and checked against the JDK's own ISO-3166 list. The length bounds repeat the column
widths of the migration, so an over-long value is refused by the value object instead of by the
database driver.

## How it works

**Provisioning on first sight.** `ProvisionUser.provision(subject, displayName)` looks the subject
up through the `UserRepository` port and returns the existing user untouched; only when none exists
does it call `User.register` with a fresh `UserId` and the injected clock, and save. The unit test
covers both halves: a second call for the same subject writes nothing, and a different display name
on a later call does not replace the stored one.

**Three callers.** `UserController` calls it from `GET /api/users/me`. `ChangeAddress` and
`ForgetAddress` call it before they touch the address, so a caller who writes first still gets a
record. `WorkOrderController` calls it to learn the requester's `UserId` from the token, which makes
placing a work order a second way a user row comes into existence ([[wiki/agent-workorders/concepts/modules-by-id]] covers
why the work order holds an id and not a `User`).

**Display name.** The controller takes the token's `name` claim and falls back to
`preferred_username` when `name` is absent or blank.

**Routes.** All under `/api/users`:

| Route | Use case | Answers |
| --- | --- | --- |
| `GET /me` | `ProvisionUser` | the caller's user |
| `PUT /me/consent` | `RecordConsent` | the user, after the consent change |
| `PUT /me/address` | `ChangeAddress` | the user, or `409` without consent |
| `DELETE /me/address` | `ForgetAddress` | the user, without an address |

Every write answers with the whole user. A value-object refusal becomes `400`; a missing
data-processing consent becomes `409`, because the body may be well formed and it is the account
state that is wrong. `ChangeAddress` carries no consent check of its own: the aggregate's
`changeAddress` throws when consent is not in force. The integration test drives these routes with a
token issued by a Keycloak container and asserts the `409` and that two calls return the same id.

**Authorization.** `SecurityConfiguration` builds one stateless filter chain. The health endpoint is
open, two `POST` routes outside this module need the `admin` realm role, and everything else,
including all four user routes, needs only a valid token. Issuer, audience and the permitted
signature algorithm (`RS256`) are properties, not code. A converter maps the entries of
`realm_access.roles` to `ROLE_`-prefixed authorities, using type tests so that a malformed claim
yields no roles instead of an error. `WriteRouteGuardIntegrationTest` lists the three user writes
among the routes open to any authenticated caller and gives the reason: `/me` is resolved against
the token's own subject.

**Storage.** `UserEntity` is a separate class from the aggregate, with the address as flat columns.
`V1__create_users.sql` adds two constraints: the subject is unique, and the four required address
columns are all null or all present. The repository integration test shows the unique constraint
refusing a second user for one subject.

## What it costs / limits

- **The concurrent first request is settled by the database only.** `ProvisionUser` reads, then
  writes, with no lock. The migration comment names the unique constraint as what decides a race
  between two first requests. The user module's main sources contain no `catch` block, so the
  losing request is not retried there.
- **Two aggregate methods have no caller.** `User.rename` and `User.deactivate` exist on the
  aggregate, but a grep over `src/main` finds no use case or route that calls either. A display name
  is set once, from the token, and never reconciled afterwards.
- **One extra `SELECT` per insert.** Ids are assigned in the domain, so Spring Data treats every
  save as a merge. `JpaUserRepository` records this as accepted.

## Later changes

- **Layer name.** The charter names the layers `domain, application, infrastructure, interface`.
  `interface` is a reserved word in Java, so the outer layer is `web`; ADR 001 records the choice.
  The module's four packages are `domain`, `application`, `infrastructure` and `web`.
- **Fewer profile fields than the charter lists.** The charter names displayName, phone, locale and
  timezone. The aggregate has `displayName` only, and no phone, locale or timezone field (grep over
  the module). The charter itself says to build the minimal set first.
- **Consent** is its own page: [[wiki/agent-workorders/decisions/consent-is-a-timestamp]].
- The architecture rules that let the work-order web layer name `ProvisionUser` are described in
  [[wiki/agent-workorders/components/quality-gate]].
