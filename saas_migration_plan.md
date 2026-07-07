# Flight Price Tracker → SaaS: Technical Migration Plan (v4)

v2 incorporated API-first architecture, non-Telegram identity, earlier
Redis, BYOK enterprise keys, earlier-but-sequenced observability, and a
signature "Vacation Planner" feature. Postgres migration, originally
listed as a to-do, is now done - it shipped to production during this
project's work.

v3 added a concrete plan for the Vacation Planner's cache (with the
chicken-and-egg problem named explicitly), specifics for the demand
validation experiment, and a North Star metric with an honest note on why
the obvious version of it can't be measured yet.

v4 adds a three-stage evolution for the cache (search-driven ->
popularity-promoted -> data-driven pre-warming) and a one-page risk
register, so the assumptions behind this plan are written down rather
than implicit.

## Starting point

The current system is architected for exactly one user. A single Telegram
bot polls with one hardcoded `CHAT_ID`, one set of provider API keys, one
Twilio WhatsApp Sandbox number, and one in-process APScheduler running
hourly checks. Every phase below exists to remove one of those
"exactly one" assumptions.

The good news: the core domain logic (provider abstraction, notification
rule engine, analytics, provider health tracking) is already
tenant-agnostic in *shape* - it operates on a `Flight` object and doesn't
care who owns it. The rework is almost entirely in the data model, auth,
API, and infrastructure layers, not the business logic itself.

## Phase 0: Provider strategy - decide before writing code

The highest-risk area, and it constrains everything downstream, so it
comes first as a decision rather than code.

Google Flights via `fast_flights`/Playwright scraping is workable for one
personal user checking hourly. At commercial scale it risks IP bans and
sits in a legal gray zone once you're charging money for access to scraped
data - Google's terms don't authorize commercial resale of scraped
results. Treat it as a supplementary/free-tier source at most, not the
backbone.

Duffel is built for exactly this use case (legitimate GDS-backed search)
but bills per search at volume - that cost needs to flow into pricing
tiers, not be absorbed silently. Skyscanner's free RapidAPI tier (20
requests/month) is already unusable for one user's hourly checks, let
alone many. Amadeus's self-serve tier was already decommissioned during
earlier work on this project.

Practical path: launch with Duffel as the primary paid-tier source, keep
Google Flights scraping as a rate-limited free-tier supplement with
aggressive caching, and treat provider cost-per-check as a first-class
input to plan pricing - especially once the Vacation Planner feature
(below) multiplies the number of searches per user action.

## Phase 1: Postgres - already done

Originally planned as a later step; moved up and completed already. The
production database on Railway is Postgres, with `user_id`/foreign-key
columns straightforward to add now via normal migrations, before any
customers exist. No remaining work here.

## Phase 2: Multi-tenancy in the data model

Add a `users` table and a `user_id` foreign key on `flights`,
`price_history`, and anywhere else that currently has no owner concept.
`provider_health` stays global. Also add lightweight `organizations` /
`workspaces` tables now, even if every user gets a solo org to start -
retrofitting a workspace concept later (needed for the BYOK enterprise
feature and for any future team/shared-billing use case) is much more
painful than including an empty layer from day one.

Every query in `app/database/database.py` that currently does
`SELECT ... FROM flights` needs a `WHERE user_id = ?` added - mechanical
but touches nearly every function in that module.

## Phase 3: REST API layer

Build this immediately after the data model, before rewiring the bot or
building any website. The API becomes the single entry point to business
logic; Telegram, a future website, and a future mobile app all become
clients of it rather than each having their own copy of the logic:

```
Telegram / Website / Mobile App
            |
        REST API
            |
      Business Logic
```

The existing service layer (`TrackingService`, `NotificationRules`,
`AnalyticsService`, `ProviderManager`) already has close to the right
shape for this - it's largely a matter of putting a FastAPI (or similar)
layer in front of it and having the Telegram bot call the API instead of
the service layer directly.

## Phase 4: Authentication

Telegram should not be the permanent identity system - it's a good
notification channel, not a good identity provider (no email recovery,
no natural way to log into a future website with it as primary auth).

```
User → Google Login / GitHub Login / Email Login → Optional Telegram Connection
```

Use a managed auth provider (Clerk, Auth0, Supabase Auth) rather than
rolling OAuth by hand. "Connect Telegram" becomes a one-time deep-link/code
verification flow that links a Telegram chat id to an already-authenticated
account, not the account itself.

## Phase 5: Multi-user bot on top of the API

With the API and auth in place, rewire the bot: first message from an
unrecognized Telegram id triggers a "link your account" flow (existing
user connects, new user gets a signup link) instead of the bot creating
identity itself. Every command becomes an API call scoped to the linked
user. Switch from long-polling to a webhook once there's real traffic.

## Phase 6: Redis + job infrastructure

Redis earns its place immediately once Celery (or RQ) enters the picture,
since a task queue needs a broker anyway - so this isn't an extra piece of
infrastructure, it's one piece doing several jobs at once:

- Celery/RQ broker for scheduled provider checks (replacing the
  single-process APScheduler, which doesn't scale to many users' checks
  running concurrently without one slow call delaying everyone else's).
- Per-user and per-provider rate limiting, so one user or one bug can't
  exhaust the shared Duffel/Skyscanner quota.
- Provider locks, so the existing provider health/circuit-breaker logic
  coordinates across multiple worker processes instead of one.
- Session storage, once the API/auth layer needs it.
- A notification queue, decoupling "an alert needs to go out" from "send
  it right now inline" - useful once WhatsApp template sends or email
  sends have their own latency/retry semantics.

## Phase 7: Observability

Sequence this by what there's actually something to observe:

Sentry (error tracking) from day one of the API - cheap, immediately
useful, no infrastructure prerequisite.

Prometheus/Grafana/OpenTelemetry once Redis/Celery/multiple workers exist
(Phase 6) - standing up dashboards before there's multi-service
infrastructure to monitor means dashboards with nothing interesting on
them. Once there are queues, workers, and rate limits, this stack is what
tells you whether they're healthy.

## Phase 8: Notification channels at scale

Telegram scales as-is once Phase 5 is done.

WhatsApp does not scale as-is. The Twilio Sandbox used today only works
for one pre-verified test number. Production WhatsApp for multiple users
requires an approved WhatsApp Business Account (via Meta) and
pre-approved message templates, since price alerts are business-initiated
messages outside any 24-hour session window. This is a real approval
process (days, not minutes) - worth starting in parallel with the
engineering phases above rather than after, since it's wall-clock time,
not engineering time.

Email is worth adding here too - cheapest channel to scale, and the
fallback most SaaS users expect.

## Phase 9: Billing

Stripe Checkout, not integrated until everything above is working:

```
Stripe Checkout → Webhook → Upgrade User
```

Kept deliberately simple - the webhook flips a plan flag on the user/org
record, and plan enforcement hooks into the row limits and rate limits
already built in Phases 2 and 6. A natural starting tier structure:

Free: 1-2 routes, hourly checks, Google Flights only, Telegram alerts.

Paid: more routes, Duffel-backed pricing, faster checks, WhatsApp/email
alerts, charts and analytics (already built), and the Vacation Planner
(below).

## Later / enterprise: bring-your-own API keys

```
Organization → Workspace → Provider Credentials
```

Some enterprise customers may want to use their own Duffel/Amadeus
contract instead of the platform's. Real feature, real premium tier - but
it requires encrypted secret storage (a proper vault, not another env
var) and per-customer provider client instances, so it's deliberately a
"later" feature built once the workspace concept from Phase 2 already
exists to hang it on.

## Signature feature: Vacation Planner

The differentiator worth building once the platform exists, and probably
the best idea in this whole plan:

```
Budget: 2000 SAR
Flexible: ±5 days
Duration: 10 days
Month: September
        ↓
   Bot searches
        ↓
Top 20 cheapest combinations
```

Not "RUH → LIS on these exact dates" but "find me the best vacation under
my budget." The codebase already has the building blocks (flexible dates,
flexible/multi airports, multi-city trip type) - this is the combinatorial
extension of all three at once.

The catch: ranking "top 20 combinations" means searching a grid of dates
x durations x possibly destinations, which multiplies provider calls fast,
and Duffel bills per search. This only works economically with aggressive
caching/batching of the grid search, and belongs behind the paid tier
rather than free - worth prototyping the actual search-cost math before
promising it as a headline feature.

The better version doesn't search everything live: build a daily cached
price index for popular routes, answer most planning queries from that
cache, and only run live searches for the small set of top candidates
the cache surfaces. That's a large reduction in provider cost per
planning query.

That cache isn't new infrastructure to build from scratch - it's what
`price_history` and the existing `analytics_service.py` (median,
volatility, expected price) already produce, but only for routes someone
is already tracking. The real design question is how the cache gets
populated for routes *nobody* has tracked yet, since surfacing options a
user didn't think to search is the whole point of the feature. Two ways
to resolve it: index popular routes speculatively ahead of demand
(reintroduces the Cartesian-cost problem, just paid by the platform
instead of a customer), or build it crowdsourced - only backfill a route
into the shared index once enough distinct users have shown interest in
it, accepting thin coverage on day one. Crowdsourced is the safer
starting point; speculative indexing before there's any usage signal is
guessing at what's popular.

That crowdsourced approach evolves in three stages rather than being one
fixed decision:

Stage 1: cache only the routes users actually search - zero speculative
cost, thin coverage by construction.

Stage 2: once a route gets searched by enough distinct users, promote it
into a shared cache other users' planning queries can also read from -
popularity becomes the signal, not a guess.

Stage 3: once there's enough real usage data to know which routes
actually carry volume, pre-warm only the top slice where the economics
clearly work out - a data-driven decision instead of a speculative one,
made only after the data to make it exists.

If a rebrand happens (see below), this is the feature that should justify
it - an "AI" or "intelligence" name only earns its keep if there's real
optimization behind it, not just alert rules with a new label.

## Naming

Worth reconsidering once the platform does more than track prices -
monitoring, analytics, recommendations, automation, notifications is a
different pitch than "price tracker." Not an engineering decision, but if
the name leans on "AI" or "intelligence," build something that actually
earns it (the Vacation Planner is the natural candidate) rather than
relabeling the existing rule-based alerts.

## Suggested order and rough effort

1. Provider/legal decision (Phase 0) - a decision, not code, but blocks
   everything else.
2. ~~Postgres migration~~ - done.
3. Multi-tenancy + workspace schema (Phase 2) - roughly a week.
4. REST API layer (Phase 3) - a week, mostly wrapping the existing
   service layer.
5. Auth via managed provider (Phase 4) - a few days integrating a
   third-party service, not building one.
6. Multi-user bot on the API (Phase 5) - a week.
7. Redis + job queue + rate limiting (Phase 6) - a week.
8. Sentry immediately; Prometheus/Grafana once Phase 6 lands (Phase 7).
9. WhatsApp Business approval (Phase 8) - start in parallel with 3-7,
   it's wall-clock time.
10. Billing (Phase 9) - a few days once tiers have somewhere to attach.
11. Vacation Planner - the first real post-launch feature, once cost
    math is validated.

Total: still roughly 4-6 weeks of focused engineering for a v1 multi-tenant
product, not counting WhatsApp approval wait time or customer acquisition.

## Before any of this: validate demand

The biggest risk to a solo-built SaaS is usually demand, not
architecture. Before building auth, subscriptions, Redis, Celery, or
dashboards, spend a weekend on a landing page instead: screenshots,
pricing, a waitlist signup, and a small distribution experiment (travel
communities, Reddit, LinkedIn, X). If nobody signs up, that's a cheap
lesson learned before 4-6 weeks of engineering. If people do, there's
real confidence the infrastructure work is worth it. Onboarding, pricing
clarity, documentation, and day-to-day reliability are what a SaaS
succeeds or fails on, and they deserve as much attention as the backend
plan does.

## North Star metric

Define this before writing any SaaS code, and make it about customer
value, not revenue or user count. The natural candidate: flights
successfully tracked that resulted in a user booking below their target
price. Every engineering decision should be weighed against whether it
moves this number - if a feature doesn't, it's probably not the highest
priority.

One honest caveat: that metric can't actually be measured today. The bot
alerts; it doesn't touch booking at all, so there's no way to know if an
alert led to a real purchase without either integrating a booking flow
(a large scope addition - payments, PNR, ticketing, refunds) or accepting
a weaker proxy. Two practical options: a self-report "mark as booked"
button on the alert (real but undercounts), or click-through rate from
alert to the airline/OTA link (measurable from day one, but a proxy for
intent rather than proof of a booking). Track the proxy immediately and
treat "confirmed booking" as something to earn once there's enough
traction to justify affiliate links or a real booking integration -
measuring the real metric before it's measurable just produces a number
nobody trusts.

## Risk register

One page, revisited as assumptions change rather than written once and
forgotten:

| Risk | Impact | Mitigation |
|---|---|---|
| Google Flights changes HTML / blocks scraping | High | Duffel as primary paid-tier provider; existing provider abstraction limits blast radius to one provider module |
| Provider costs exceed revenue | High | Per-search cost tracking, paid-tier quotas, crowdsourced cache to cut redundant searches |
| Low user demand | High | Landing page + waitlist validation before any SaaS infrastructure is built |
| WhatsApp Business approval delayed | Medium | Launch on Telegram + email first; don't gate launch on Meta's approval timeline |
| Scheduler overload under multi-tenant load | Medium | Redis/Celery migration (Phase 6), planned before scale actually requires it |
| Provider outage | Medium | Circuit breaker + auto-disable/cooldown already built (original roadmap Phase 1 - `provider_health.py`) |
| Multi-tenant data isolation bug (one user's row-scoping leaks into another's) | High severity, low likelihood | Explicit test coverage on every `user_id`-scoped query as part of Phase 2, not left to manual QA |
| Stripe webhook failures (silent billing/plan-sync bugs) | Medium | Idempotent webhook handling plus a periodic reconciliation job, not a fire-and-forget handler |

## What doesn't need to change

The notification rule engine, analytics service, chart rendering, and
provider health tracking built during the original roadmap are already
written in terms of a single `Flight` object and don't assume a single
global user - they carry over to the SaaS version largely unchanged once
`Flight` objects are scoped to a `user_id`.
