---
title: Consent is a timestamp
description: Consent is three nullable timestamps on the user row, and withdrawing data-processing consent erases the stored address in the same operation.
draft: false
cites:
  - path: docs/adr/009-consent-is-a-timestamp-and-withdrawal-erases-the-address.md
    lines: 12-29, 33-54, 60-82, 86-114, 118-132
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/Consent.java
    lines: 8-12, 24-45
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/User.java
    lines: 80-83, 135-142, 144-163, 165-198, 212-241
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/ConsentRequiredException.java
    lines: 7-20
  - path: src/main/java/dev/…/agentworkorders/modules/user/domain/Address.java
    lines: 31-38, 52-68
  - path: src/main/java/dev/…/agentworkorders/modules/user/application/RecordConsent.java
    lines: 12-20, 57-76
  - path: src/main/java/dev/…/agentworkorders/modules/user/application/ConsentDecision.java
    lines: 15-22
  - path: src/main/java/dev/…/agentworkorders/modules/user/application/ChangeAddress.java
    lines: 16-18, 54-59
  - path: src/main/java/dev/…/agentworkorders/modules/user/application/ForgetAddress.java
    lines: 11-13, 45-49
  - path: src/main/java/dev/…/agentworkorders/modules/user/web/UserController.java
    lines: 86-92, 101-107, 122-126, 138-141
  - path: src/main/java/dev/…/agentworkorders/modules/user/web/ConsentRequest.java
    lines: 8-11, 19-23
  - path: src/main/java/dev/…/agentworkorders/modules/user/infrastructure/UserEntity.java
    lines: 51-52, 73-76
  - path: src/main/resources/db/migration/V4__add_user_consent.sql
    lines: 3-10, 16-26
  - path: src/test/java/dev/…/agentworkorders/modules/user/domain/UserTest.java
    lines: 295-338
  - path: src/test/java/dev/…/agentworkorders/modules/user/application/RecordConsentTest.java
    lines: 23, 60-107
  - path: src/test/java/dev/…/agentworkorders/modules/user/application/ForgetAddressTest.java
    lines: 60-69
  - path: src/test/java/dev/…/agentworkorders/modules/user/application/ChangeAddressTest.java
    lines: 90-98
  - path: src/test/java/dev/…/agentworkorders/modules/user/infrastructure/JpaUserRepositoryIntegrationTest.java
    lines: 129-141, 230-254
  - path: src/test/java/dev/…/agentworkorders/modules/user/web/UserEndpointIntegrationTest.java
    lines: 96-104, 123-133
verified_at: 262e98e
---

# Consent is a timestamp

> **TL;DR** — A user's consent is stored as three nullable timestamps on the
> `users` row: data processing, marketing, and terms acceptance. `NULL` means
> the permission is not in force. An address can only be stored while
> data-processing consent is in force, and withdrawing that consent sets the
> address to null in the same aggregate method. A check constraint restates
> the rule in the database, so a write that bypasses the aggregate is refused
> too. [[wiki/agent-workorders/index|↑ Wiki]]

## The problem

The `Address` value object, its columns and a `changeAddress` method existed
with no caller. ADR 009 gives the reason: an address is personal data, the
project charter ties storing it to a consent record, and that record had not
been modelled. Building the endpoint that accepts an address meant building
the consent in the same change.

Three questions were open and each changes the schema, the aggregate and the
HTTP surface: what shape consent takes, what happens to a stored address when
consent is withdrawn, and whether consent and address share an endpoint. They
were decided together because the second answer is only enforceable in the
database given a particular first answer.

## The decision

- **Three timestamps, one value object.** The migration adds
  `data_processing_consent_at`, `marketing_consent_at` and `terms_accepted_at`
  to `users`, all nullable. The domain wraps them in the `Consent` record;
  `allowsDataProcessing()` is `dataProcessingAt != null`.
- **A grant stamps the instant; a re-grant moves it.**
  `grantDataProcessingConsent` builds a new `Consent` with `now` in that
  position whether or not one was already there.
- **No address without consent.** `User.changeAddress` throws
  `ConsentRequiredException` when data-processing consent is not in force.
  `ChangeAddress` carries no check of its own and relies on the aggregate.
- **Withdrawal erases the address.** `withdrawDataProcessingConsent` clears
  the timestamp and sets `address` to null in one method.
- **The database enforces it independently.** The constraint
  `users_address_requires_consent` requires `address_line1 IS NULL OR
  data_processing_consent_at IS NOT NULL`. `User.reconstitute` deliberately
  does not re-check the rule on load.
- **Marketing and terms have no structural effect.** Withdrawing marketing
  consent changes nothing else. Terms acceptance has no withdraw method;
  `ConsentDecision.acceptTerms` set to false leaves an earlier acceptance
  standing.
- **A consent request states the whole state.** `RecordConsent.update` grants
  what the decision sets to true and withdraws what it sets to false.
  `ConsentRequest` documents that an omitted field reads as false.
- **Separate endpoints.** `UserController` maps `PUT /me/consent` and
  `PUT /me/address` under `/api/users`. Each returns the full user.
  `ConsentRequiredException` is mapped to `409`.

| Option | Why not |
| --- | --- |
| An append-only `consent_events` table | A check constraint cannot span tables, so the address rule would need a trigger or a mirrored column; every load would aggregate the latest event per kind. |
| Booleans plus one `consent_updated_at` | Two permissions changed at different times would share one timestamp, which is the fact that has to be provable. |
| Refuse withdrawal while an address is stored | Blocks a right the user does not need permission to exercise. |
| Leave the address after withdrawal | The rule would hold only at the moment of writing. |
| One profile endpoint carrying both | Under PUT semantics a request that omits the address deletes it, so a marketing opt-out could erase personal data. |

## What it costs

- **No withdrawal history.** "Never given" and "given and later withdrawn" are
  the same stored state. The model cannot show that consent was in force
  during a past window. ADR 009 notes the events table could be added later
  beside the columns.
- **Two round trips to store a first address.** A client must grant consent
  first and gets a `409` if it does not.
- **A consent request changes a different resource.** The address disappears
  as a side effect; only the full-user response makes that visible.
- **Every consent request restamps what it keeps.** Because each request
  states the whole state and a grant always writes `now`, a request that only
  switches marketing off still moves `data_processing_consent_at` forward. The
  stored instant is the latest request that kept the permission, not the first
  grant. `RecordConsentTest.isIdempotent` compares two calls under a fixed
  clock, so it does not exercise that.

What the tests show: `UserTest` asserts the refusal without consent, that a
re-grant moves the instant, and that withdrawal clears both the address and
the timestamp. `RecordConsentTest` asserts that an omitted permission is
withdrawn, that withdrawal through the use case removes the stored address,
and that an earlier terms acceptance survives a request that sets it to false.
`JpaUserRepositoryIntegrationTest` asserts that a save after withdrawal nulls
the address columns and that a direct `INSERT` of an address without consent
raises a data-integrity violation. `UserEndpointIntegrationTest` asserts the
`409` and that the response to a withdrawal carries a null address.

## Later changes

- **A third endpoint exists.** ADR 009's decision section names two endpoints.
  The code also maps `DELETE /me/address` to `ForgetAddress`, which sets the
  address to null and leaves consent untouched; `ForgetAddressTest` asserts
  the consent stays in force. The ADR's notes section mentions this route
  (issue #45) and states the one-way rule behind it: withdrawal erases the
  address, removing the address is not a withdrawal.
- **One assertion message predates that route.** `ChangeAddressTest` still
  explains its null-address refusal with "clearing an address is withdrawing
  consent", which the delete route has since made untrue. The assertion
  itself, that a null address is refused, still matches the code.
- **Address length bounds moved into the value object** in the same change
  (ADR 009 notes). `Address` declares them as constants and checks them in its
  constructor.
- The rest of the module, including how a user comes to exist on first
  request, is on [[wiki/agent-workorders/components/user-module]].
