# Learner PWA delivery

## Purpose

Give learners one chronological Inbox for course and account updates and preserve private, consented iPhone delivery.

## ADDED Requirements

### Requirement: Unified notification list
The Inbox SHALL open as a dedicated full-screen view with course and account notices together. It SHALL keep Back usable during data loading.

#### Scenario: Partial feed failure
- **WHEN** one notice feed is temporarily unavailable
- **THEN** verified notices from the other feed can still be read and the learner can return.

### Requirement: Consented installed delivery
Web Push SHALL use the existing installed-device subscription, current ownership and active delivery policies. Lock-screen payloads SHALL avoid sensitive account or payment details.

#### Scenario: Reviewed payment and course or account update
- **WHEN** a supported notice is issued for a learner with a valid opted-in installation
- **THEN** the configured worker can deliver a generic notification that opens the authenticated Inbox.

#### Scenario: Account access restricted
- **WHEN** an authorized administrator restricts an account with an active opted-in PWA installation
- **THEN** the installation can receive a recent, generic access update
- **AND** restricted accounts remain unable to open protected pages or receive ordinary account and course messages.
