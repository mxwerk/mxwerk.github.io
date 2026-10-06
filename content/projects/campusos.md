---
title: CampusOs — Full-Stack Student App
description: Full-stack student application bundling grades, calendar and Moodle events, enrollment certificate, mensa plan and university mail in one dashboard. Built with Next.js 16, Supabase, and Feature-Sliced Design. Team of 6.
tags:
  - web
  - fullstack
date: 2026-06-30
---

# CampusOs — Full-Stack Student App

A team project (6 members) from the Projekt module at BHT Berlin. CampusOs is a full-stack student application that aggregates BHT data sources into a single personalised dashboard.

## What it does

- **Dashboard** — personalised student overview aggregating all data sources
- **Grades** — synced from the BHT student portal
- **Calendar and Moodle sync** — calendar entries and Moodle events in one place
- **Enrollment certificate** — retrieved from the portal and available in-app
- **Mensa plan** — current canteen menu pulled and displayed in-app
- **Mail** — the BHT mailbox inside the application (IMAP)

## Technical decisions worth noting

**Scraping as a separate microservice** — the BHT student portal exposes no API for grades, calendar or the enrollment certificate. A small dedicated service (Hono + playwright-core, run in Docker) does the browser automation, so no headless browser runs inside the Next.js app or on serverless hosting.

**Feature-Sliced Design (FSD)** was chosen as the architectural methodology — a strict layer graph that prevents UI components from importing directly from the data layer. Combined with dependency-cruiser to enforce the rules in CI, this kept the codebase navigable as the feature count grew.

**Supabase self-hosted via Docker** instead of the managed cloud offering. The team ran a full Supabase stack (Postgres, Auth, Storage, realtime) in Docker Compose on a development server. This trades managed convenience for full control and offline dev capability.

**next-intl internationalisation** from day one — not bolted on later.

**Testing pyramid:** Vitest + Testing Library for unit/integration, MSW for API mocking, Playwright with Page-Object-Model and `globalSetup/storageState` for E2E session reuse. Coverage thresholds (70 % statements/functions/lines, 60 % branches) run in CI.

## Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router), React 19, Tailwind v4, shadcn/ui (Base UI), TanStack Query |
| Backend / Data | Supabase (self-hosted), Drizzle ORM, PostgreSQL |
| Scraping | Separate microservice: Hono + playwright-core (Docker) |
| Mail | IMAP (imapflow, mailparser), nodemailer |
| Testing | Vitest, Testing Library, Playwright, MSW |
| Architecture guard | dependency-cruiser (FSD layer rules in CI) |
| Internationalisation | next-intl |
