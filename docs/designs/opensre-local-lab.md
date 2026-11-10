# OpenSRE Local Evaluation Lab

*   **Author:** kiran kumar
*   **Status:** Proposed
*   **Date:** 2026-11-10

--------------------------------------------------------------------------------

## Overview

This lab lets one engineer try OpenSRE (github.com/Tracer-Cloud/opensre, public
alpha, pinned to commit `1f817d29`) on a laptop, against failures that look like
real production and CI problems. OpenSRE is an AI agent with two jobs: it
diagnoses failed CI runs, and it investigates incidents by reading logs,
metrics, traces, deploy history and database state. The lab supplies all of
those signals from a small, realistic system that runs in OrbStack Kubernetes on
a 16 GiB Mac, with code and CI hosted in one public GitHub repo.

The lab has five parts:

1.  **Sample system.** A few small services that use PostgreSQL, Redis and
    MongoDB. ArgoCD deploys them from the GitHub repo. Loki, Mimir, Tempo and
    Grafana collect their logs, metrics and traces.
2.  **Failure catalogue.** A numbered list of common real-world failures. Each
    one can be switched on and off, raises a named Grafana alert (or a failed
    CI run), and states the diagnosis a competent engineer would reach.
3.  **Runbook knowledge base.** One Markdown runbook per failure type, in the
    same repo, linked to alerts by an exact-match manifest. OpenSRE must load
    and follow these, not fall back to generic advice.
4.  **Alert webhook server.** The only custom code that touches OpenSRE. A
    small web server on the Mac receives Grafana alert webhooks, builds a
    fixed-format prompt from the alert (name, service, labels), and runs OpenSRE
    with it, through the `opensre` command or OpenSRE's Python SDK. It records
    every run. It adds no tools, logic or knowledge to OpenSRE.
5.  **OpenSRE itself**, signed out, configured only through its own settings:
    its runbook source, its integrations, and an NVIDIA Build model chosen by
    testing.

## The Problem

To judge whether OpenSRE is useful, it has to be tried against failures whose
cause is already known, on a system that produces the same evidence a real one
would. OpenSRE's own demos use canned data or a hosted account. Neither shows
how it behaves on this team's kind of stack (Kubernetes, ArgoCD, Grafana's
observability tools, common databases, GitHub Actions) with this team's own
runbooks.

Four constraints shape the problem:

*   **No opensre.com account.** The author will not sign in. The interactive
    shell requires sign-in, so the lab uses only the headless CLI and the Python
    API. OpenSRE's docs disagree on whether its GitHub tools, which the runbook
    feature and CI analysis depend on, work without an account. This is
    unproven and is tested first.
*   **Runbooks must actually be used.** An answer that reads like generic
    internet advice is a failure, even if it happens to be right. The lab must
    be able to show, per run, that OpenSRE loaded the expected runbook.
*   **One laptop.** OrbStack has 12 GiB of memory and 10 CPUs. Every component
    runs as a single small instance with fixed memory limits.
*   **Public repo.** Code, workflows and Actions logs are visible to anyone. No
    secret may enter the repo or a log.

The proposed solution is a lab that is built in phases, with a pass/fail check
at the end of each phase. The first phase spends one to two hours testing, on
the laptop alone, whether signed-out OpenSRE can load runbooks and read GitHub
Actions runs. The cluster is built only after that question is answered.

## Goals

*   **G1. Prove signed-out operation.** OpenSRE runs with no opensre.com
    account, through the headless CLI and the Python API, using an NVIDIA Build
    model. Done when one investigation completes with the account signed out.
*   **G2. Prove runbook use.** For every incident scenario, a run passes only
    if all three hold: OpenSRE's own runbook tool (`load_runbook_guidance`)
    returns `matched`; the answer cites the expected
    runbook ID and its commit-pinned GitHub URL; and the diagnosis names the
    cause stated in the catalogue.
*   **G3. Cover incident investigation.** The catalogue covers the common
    failures this stack can produce: Kubernetes (crash loop, out-of-memory
    kill, image pull error, failing probes, bad config or secret, resource
    limits, bad rollout, ArgoCD drift), databases (slow query, lock contention,
    connection pool exhaustion, disk filling, Redis memory pressure and
    eviction, MongoDB missing index), and services (latency, error spikes,
    timeouts and retry storms, memory leak, cascading failure). The first six
    scenarios must pass before more are added.
*   **G4. Cover CI diagnosis.** For each CI scenario (broken test, flaky test,
    slow test, dependency or image build failure, workflow file mistake,
    failing security scan), OpenSRE states whether the failure is CI-caused or
    code-caused, names the cause, and prints a proposed fix to standard output.
    Runbooks apply to CI as well: CI runbooks hold the team's rules for how to
    sort and fix specific errors (for example, quarantine a flaky test rather
    than retry it). Each CI scenario has a runbook identity
    (`alertname: CIFailure`, `service: <workflow>`, `labels.failure: <id>`),
    and every CI diagnosis prompt carries it, because the CI skill does not
    look up runbooks by itself. GitHub cannot reach the Mac, so CI diagnosis is
    started by hand, through the webhook server or `opensre ask`. The G2 pass rule applies to CI
    runs too.
*   **G5. Automatic triggering.** A firing Grafana alert reaches the webhook
    server and starts one OpenSRE investigation with no manual step. The
    server records the prompt, the runbook lookup result, the answer, the
    model, the duration and the OpenSRE commit for each run.
*   **G6. Repeatable faults.** Every scenario has a written procedure,
    `faults/<id>.md`, with the exact `kubectl`, `git`, `gh` or database
    commands to switch it on, switch it off, and return the system to a known
    healthy state, ending with a health check. There is no lab script: the
    webhook server is the only custom code.
*   **G7. Fit the laptop.** All cluster pods have memory requests and limits.
    Measured steady-state use leaves at least 3 GiB of OrbStack's 12 GiB free.
*   **G8. Keep secrets out of the repo.** The NVIDIA key and the GitHub token
    live only in the local `.env` (gitignored). CI uses only GitHub's built-in
    `GITHUB_TOKEN`. No secret value appears in the repo or in an Actions log.
*   **G9. Choose a model by evidence.** Two to three NVIDIA Build models with
    tool calling are tried on the same scenarios. The one kept has the best mix
    of correct, runbook-backed answers and speed, and the comparison is
    recorded. The model is set only through OpenSRE's own setting
    `NVIDIA_MODEL`, which uses one model for all roles (reasoning,
    classification, tool calling) and replaces the Llama 3.1 defaults.

## Non-Goals

*   Signing in to opensre.com, or using OpenSRE's test-mode bypass of the
    sign-in gate.
*   OpenSRE pushing branches, opening pull requests, or changing the cluster.
    CI fixes are printed, not applied. No second coding agent is installed.
*   Scoring tables, benchmarks, or rankings. Each run is pass or fail.
*   Running more than one fault at a time.
*   Kafka, Temporal, ClickHouse, MariaDB, Pyroscope, GitLab, self-hosted
    GitHub runners, Argo Workflows, Tekton, and the hosted OpenSRE gateway.
*   High availability, multiple replicas, or production-scale data. Components
    are single instances.
*   Storing the NVIDIA key or a personal access token as an Actions secret.
*   Changing OpenSRE's own source code, or adding custom tools, MCP servers,
    plugins or logic to it. The webhook server is the only custom service, and
    it only passes alerts to OpenSRE.

## Open Questions

*   **Q1. Do OpenSRE's GitHub tools work signed out?** The author expects yes,
    and `cicd-overview.mdx` agrees: a provider key plus a GitHub token is
    enough. `integration-github.mdx` disagrees: local tokens "do not authorize
    agent GitHub tools". Phase 0 confirms it. There is no fallback: the author
    rejected custom tools. If Phase 0 fails, the lab stops there and the
    result is reported, because without GitHub access OpenSRE can load neither
    runbooks nor CI runs.
*   **Q2. Which way does the webhook server call OpenSRE?** It can run the
    `opensre --json ask` command, or call OpenSRE's Python SDK
    (`start_embedded_session`). The command is known to work signed out; the
    SDK has no sign-in check in the docs but is untested. Phase 0 tries both,
    and the server uses whichever works signed out, preferring the command if
    both do because it needs no OpenSRE internals.
*   **Q3. Does CI analysis work without a coding agent?** The author expects
    yes: read-only CI diagnosis is OpenSRE's core use case, and only the repair
    skill lists a coding agent. Phase 0 confirms it.

## Critical User Journeys (CUJs)

### CUJ 1: Incident investigated automatically with a runbook

*   **Given**: The lab is healthy, the webhook server is running on the Mac,
    and the lab repo is registered as OpenSRE's runbook source.
*   **When**: The engineer follows the "on" steps in
    `faults/db-slow-query.md`. Within a few
    minutes the Grafana alert `PostgresSlowQuery` with `service=orders` fires
    and Grafana posts it to the webhook server.
*   **Then**: The webhook server starts one OpenSRE investigation. The run record
    shows the runbook lookup returned `matched` for `pg-slow-query`; the answer
    cites the runbook's commit-pinned URL, separates runbook guidance from
    observed evidence, and names the missing index and the query. The run is
    marked pass. The "reset" steps return the system to healthy and the alert
    resolves.

### CUJ 2: Generic answer is caught

*   **Given**: A scenario's alert labels do not exactly match any manifest
    entry (for example a typo in `service`).
*   **When**: The alert fires and OpenSRE investigates.
*   **Then**: The runbook lookup returns `not_found`. Even if the diagnosis is
    right, the run is marked fail, and the record says the runbook was not
    used. The labels are checked by hand against `.opensre/runbooks.yaml`
    when a scenario is added (see Scenario identity).

### CUJ 3: Failed CI run diagnosed

*   **Given**: The sample repo is on GitHub with Actions enabled.
*   **When**: The engineer pushes the `scenario/ci-flaky-test` branch, the
    workflow fails, and the engineer asks the webhook server (or runs `opensre ask`)
    to diagnose the latest failed run.
*   **Then**: OpenSRE loads the `ci-flaky-test` runbook (lookup `matched`),
    reads the run and its logs, states that the failure is a flaky test
    (code-caused, timing-dependent), names the test, and prints a proposed
    patch that follows the runbook's rule for flaky tests. The answer cites the
    runbook's commit-pinned URL. Nothing is pushed.

### CUJ 4: Phase 0 decides whether the lab goes ahead

*   **Given**: OpenSRE is installed at commit `1f817d29` on the Mac, signed out,
    with `NVIDIA_API_KEY`, `NVIDIA_MODEL` and a fine-grained GitHub token in the
    environment. No cluster exists.
*   **When**: The engineer registers OpenSRE's demo runbook source and asks it
    to investigate `CheckoutHighLatency` through `opensre --json ask` and
    through the Python SDK, then asks it to analyse a failed Actions run.
*   **Then**: If the answers show `matched`, a commit-pinned URL, and the CI run
    was read, the lab goes ahead and the working call path is recorded for the
    webhook server. If not, the lab stops at Phase 0 and the failure is
    written up; no custom tools are built.

## Technical Plan (Architecture)

### Layout

The folder `opensre-test` becomes the root of one public GitHub repo,
`kirankumar-grootan/opensre-lab`. The design notes (`.egm/`,
`concepts_brief.md`, `design_draft.md`) stay local and are listed in
`.gitignore`, together with `.env` and the `runs/` folder of run records.
Everything OpenSRE, ArgoCD or GitHub Actions reads lives in the repo.

```text
Mac (16 GiB)                                   GitHub (public repo)
+-----------------------------------------+    +------------------------------+
| .env  (NVIDIA_API_KEY, GH_TOKEN, ...)   |    | services/  deploy/  runbooks/|
| OpenSRE CLI, signed out, pinned commit  |<-->| .opensre/runbooks.yaml       |
|   - runbook source = this repo          |    | catalogue/scenarios.yaml     |
|   - integrations via env vars           |    | .github/workflows/           |
| webhook server  :8088                   |    +------------------------------+
|   POST /alert   (from Grafana)          |       | Actions (GitHub runners)
|   POST /ci      (by hand)               |       | build -> GHCR -> bump tag
|   runs/<id>.json (run records)          |       v
| faults/<id>.md  (manual procedures)     |    ghcr.io/kirankumar-grootan/...
+-------------------^---------------------+
        webhook     |   kubectl / *.k8s.orb.local / port-forward
+-------------------+-------------------------------------------------------+
| OrbStack Kubernetes (12 GiB)                                               |
|  argocd:   ArgoCD core  -- pulls deploy/ from GitHub, applies it           |
|  observe:  Alloy -> Loki, Mimir, Tempo ; Grafana (alert rules + webhook)   |
|            kube-state-metrics, postgres/redis/mongodb exporters            |
|  data:     PostgreSQL, Redis, MongoDB  (1 instance each, PVCs)             |
|  shop:     storefront, orders, catalog, worker, loadgen                    |
+---------------------------------------------------------------------------+
```

### Components

**Sample system (`shop` namespace).** Four small Python (FastAPI) services
and a traffic generator, chosen because one language keeps instrumentation and
fault code in one style. The services form a small online shop:

*   `storefront`: public HTTP API; calls `orders` and `catalog`.
*   `orders`: creates and lists orders in PostgreSQL; queues work in Redis.
*   `catalog`: product data in MongoDB, cached in Redis.
*   `worker`: takes jobs from a Redis stream and writes results to PostgreSQL.
*   `loadgen`: k6 with a fixed, steady request mix, so every fault has traffic
    to act on.

Each service uses the OpenTelemetry SDK for traces, metrics and logs, sends
them to Alloy, and sets `service.name`, which becomes the `service_name` label
OpenSRE's Grafana queries require. Each service has health and readiness
endpoints and reads a fault ConfigMap every few seconds (see Fault switching).

**Data (`data` namespace).** PostgreSQL, Redis (with `maxmemory` and an
eviction policy) and MongoDB (WiredTiger cache capped at 0.25 GB). Each is a
single instance installed from a Helm chart, with a PersistentVolumeClaim on
OrbStack's `local-path` storage. PostgreSQL has `pg_stat_statements` turned
on so slow queries are visible. Each database has a read-only user for
OpenSRE.

**Observability (`observe` namespace).** Loki, Tempo and Mimir in
single-binary mode, Grafana, Alloy as the one collector (OTLP in, plus
Kubernetes log collection and metric scraping), kube-state-metrics, and the
three database exporters. Retention is 48 hours. Grafana's data sources and
alert rules are loaded from files in the repo, so they are versioned and
reviewed like code.

**Delivery (`argocd` namespace).** ArgoCD in core mode (no Dex, no
notifications, no UI-facing SSO). One root app points at `deploy/` in the repo
and creates one ArgoCD app per namespace (app of apps). Images are public on
GHCR, so the cluster needs no pull secret. Self-heal is on for every app except
the one used by the drift scenario.

**Alert webhook server (Mac).** A small Python web server on port 8088, the
only custom code that touches OpenSRE.

*   `POST /alert` takes Grafana's webhook payload. For each alert with status
    `firing`, it builds a fixed prompt from `alertname`, `service` and the
    other labels, and asks OpenSRE to investigate using the configured
    runbook. Resolved alerts and repeats of an alert already handled (same
    Grafana fingerprint) are ignored.
*   `POST /ci` is called by hand with a GitHub Actions run ID and scenario ID.
    It builds the CI diagnosis prompt with the scenario's runbook identity
    (`alertname: CIFailure`, `service`, `failure`).
*   Investigations run one at a time from an in-memory queue, so two runs never
    compete for the model or the cluster.
*   OpenSRE is called through `opensre --json ask` or the Python SDK, whichever
    Phase 0 shows works signed out.
*   Each run is saved to `runs/<timestamp>-<scenario>.json`: the prompt, the
    full OpenSRE JSON output (including tool calls), the runbook lookup status,
    the cited runbook URL, the model, the OpenSRE commit, and the duration.

Grafana reaches the server at `http://host.orb.internal:8088`, the address
OrbStack gives containers for the Mac.

**OpenSRE (Mac).** Installed from source at commit `1f817d29` with `uv`, run
signed out. All settings come from environment variables in `.env`, never
from saved integration records, because saved records override environment
variables and would make the setup depend on hidden state. The settings are:

| Area | Settings |
| --- | --- |
| Model | `LLM_PROVIDER=nvidia`, `NVIDIA_API_KEY`, `NVIDIA_MODEL` |
| Grafana | `GRAFANA_INSTANCE_URL`, `GRAFANA_READ_TOKEN`, `GRAFANA_LOKI_DATASOURCE_UID`, `GRAFANA_MIMIR_DATASOURCE_UID`, `GRAFANA_TEMPO_DATASOURCE_UID` |
| Kubernetes | `KUBECONFIG`, `KUBECONFIG_CONTEXT=orbstack` |
| ArgoCD | `ARGOCD_BASE_URL` (localhost port-forward), `ARGOCD_AUTH_TOKEN` (read-only account) |
| Databases | `POSTGRESQL_*`, `REDIS_*`, `MONGODB_CONNECTION_STRING` (read-only users) |
| GitHub | `GH_TOKEN` (fine-grained, this repo only) |
| Privacy | `OPENSRE_NO_TELEMETRY=1`, `OPENSRE_PROMPT_LOG_DISABLED=1` |

The runbook source is registered once with
`opensre runbooks add github --repo kirankumar-grootan/opensre-lab --ref main
--manifest .opensre/runbooks.yaml`.

### Scenario identity: one source

`catalogue/scenarios.yaml` is the only place a scenario is defined. Each
entry has an ID, a track (`incident` or `ci`), the alert name, `service`,
labels, the fault type and toggle, the expected diagnosis, and the runbook
file. The Grafana alert rules (`deploy/observe/alert-rules/`) and
`.opensre/runbooks.yaml` are written by hand to match it; nothing is
generated. Because a single typo stops the runbook from loading, adding a
scenario follows a checklist in `catalogue/README.md`: the alert rule's
`alertname`, `service` and labels match the manifest entry exactly; no two
manifest entries are equally specific; `service` equals the service's
`service_name`; the runbook file exists. `opensre runbooks verify` is run after
every change to the manifest. Alert rules carry no `runbook_url` annotation,
so every incident run tests OpenSRE's manifest matching.

### Runbooks

One Markdown file per scenario under `runbooks/`, written for this stack, not
copied from generic guides. Every runbook has the same sections:

1.  **Symptoms**: what the alert means and what users see.
2.  **Checks, in order**: which signal to read and what to look for, named in
    terms of OpenSRE's tools (a Loki query, a Mimir metric, a trace, a
    Kubernetes event, a `pg_stat_statements` query, `INFO memory` in Redis).
3.  **Known causes**: the causes seen on this stack and how to tell them apart.
4.  **Rules**: the team's decisions for this error, for example "a flaky test
    is quarantined and a ticket opened, never retried in CI" or "never restart
    PostgreSQL to clear locks; find and end the blocking session".
5.  **Fix**: the remediation, and whether it needs approval.
6.  **Done when**: the signal that shows the problem is gone.

### Fault switching

Each scenario's `faults/<id>.md` lists the commands by hand. The sample
services contain the fault behaviour itself (for example a slow code path or
a leaking cache), because they are the system under test; switching it on is
always a standard command. Three kinds of switch:

| Kind | Used for | Commands in the procedure |
| --- | --- | --- |
| Runtime flag | latency, errors, timeouts, retry storm, memory leak, slow query, lock, pool exhaustion | `kubectl patch configmap shop-faults` to set or clear the flag; services read it within seconds. ArgoCD ignores this ConfigMap. |
| Git change | image pull error, bad rollout, bad config or secret, resource limits, missing index (migration) | `git revert`-able commit on `main` from the prepared change in `faults/<id>.patch`, then `argocd app sync` |
| Direct change | ArgoCD drift, Redis eviction, disk filling | `kubectl edit` on the drift app (self-heal off), `redis-cli` to load data, or a one-off Job that fills a 1 GiB PVC used only by this fault |

The shared reset procedure, `faults/reset.md`, clears all flags, resets
`main` to the `baseline` tag, syncs ArgoCD, re-seeds the databases from
`seed/`, and checks that every service is healthy and every alert has
resolved. Only one fault is on at a time; each procedure starts by checking
that no flag is set and no alert is firing.

### CI pipeline

*   `deliver.yml` runs on pushes to `main` that touch `services/`: tests,
    builds images, pushes them to GHCR, writes the new image tag into
    `deploy/`, and commits with `[skip ci]`. It uses only the built-in
    `GITHUB_TOKEN` (`contents: write`, `packages: write`).
*   `checks.yml` runs on pull requests and `scenario/ci-*` branches: lint,
    unit tests, image build, dependency install, and a Trivy security scan.
    CI scenarios break one of these steps on their own branch, so `main` and
    delivery are never broken by a scenario.
*   No workflow uses `pull_request_target`, prints environment variables, or
    turns on step debug logging. `main` is protected; push protection and
    secret scanning are on.

### Data flows

**Incident:** "on" steps in `faults/<id>.md` -> fault visible in metrics, logs or traces ->
Grafana alert rule fires -> Grafana posts to `host.orb.internal:8088/alert` ->
webhook server queues one run -> OpenSRE loads the runbook from GitHub by
exact match, then reads Grafana, Kubernetes, ArgoCD and the databases ->
answer and tool calls saved in `runs/` -> engineer compares with the
catalogue's expected diagnosis -> `faults/reset.md`.

**CI:** each CI scenario is a long-lived branch `scenario/ci-<id>` with one
deliberate break -> `gh workflow run checks.yml --ref scenario/ci-<id>` ->
`checks.yml` fails on a GitHub runner -> engineer calls `POST /ci` with the
run ID -> OpenSRE loads the CI runbook, reads the run and its logs through
GitHub, and prints the cause and a proposed fix -> saved in `runs/`. Nothing
needs resetting; the branch stays for the next run.

### Memory budget

Limits per pod. Phase 2 measures real use and must leave 3 GiB free.

| Component | Limit |
| --- | --- |
| OrbStack and kube-system | about 1 GiB |
| Loki | 512 MiB |
| Mimir (monolithic) | 1 GiB |
| Tempo | 512 MiB |
| Grafana | 256 MiB |
| Alloy | 256 MiB |
| kube-state-metrics + 3 exporters | 256 MiB |
| PostgreSQL | 512 MiB |
| Redis | 256 MiB |
| MongoDB | 768 MiB |
| ArgoCD core | 1 GiB |
| 4 services + loadgen | 1 GiB |
| **Total** | **about 7.3 GiB of 12 GiB** |

### Phases

| Phase | Builds | Pass check |
| --- | --- | --- |
| 0 | OpenSRE on the Mac only, signed out | Demo runbook `matched` with commit URL via CLI and SDK; a failed Actions run on a scratch repo is read and diagnosed |
| 1 | Model choice | 2-3 NVIDIA models via `NVIDIA_MODEL` on Phase 0 prompts; chosen model calls the runbook tool every time |
| 2 | Repo, cluster, data, observability, one service | Steady-state memory leaves 3 GiB free; all signals visible in Grafana with `service_name` |
| 3 | All services, webhook server, fault procedures, first 6 scenarios | All 6 pass the G2 rule end to end |
| 4 | Rest of the catalogue, ArgoCD drift, CI track | Each new scenario passes G2 |

If Phase 0 fails, the lab stops and the result is written up.

## Alternatives Considered

### Alternative A: Sign in to opensre.com

*   **Pros**: Opens the interactive shell, the hosted model, the GitHub
    connection made in the web app, and the documented runbook and CI paths.
    Removes the Phase 0 risk.
*   **Cons**: Ties the test to a hosted account and sends investigation data
    through OpenSRE's service.
*   **Reason for Rejection**: Rejected by author: the lab must show OpenSRE
    working self-hosted, on the author's own model key, with no account.

### Alternative B: Custom runbook and GitHub tools as a fallback

*   **Pros**: If signed-out GitHub access fails, the webhook server could
    register its own runbook loader (same manifest, same exact matching) and
    GitHub Actions log reader through OpenSRE's external tool hook
    (`register_external_tool_package`). OpenSRE would still make a real,
    visible tool call, so the lab could continue past Phase 0.
*   **Cons**: Depends on alpha internals; adds code that tests the lab's tools
    rather than OpenSRE's.
*   **Reason for Rejection**: Rejected by author: no custom logic beyond the
    webhook server. If Phase 0 fails, the lab stops.

### Alternative C: MCP server serving the runbooks

*   **Pros**: Uses OpenSRE's supported MCP client; no change to OpenSRE.
*   **Cons**: Another process to run; still custom code.
*   **Reason for Rejection**: Rejected by author: same rule as Alternative B.

### Alternative D: Attaching the runbook to the prompt (`opensre ask -i`)

*   **Pros**: Works signed out with no GitHub access.
*   **Cons**: OpenSRE treats attachments as untrusted context, not guidance,
    and the answer has no commit-pinned runbook citation, so runbook use
    cannot be shown.
*   **Reason for Rejection**: Fails goal G2. Rejected by author during
    brainstorming ("without it, it's dumb").

### Alternative E: Alertmanager poller writing `alert.json`

*   **Pros**: About 20 lines; no inbound connection from the cluster to the Mac.
*   **Cons**: Polling delay; one more custom script.
*   **Reason for Rejection**: Rejected by author in favour of a Grafana
    webhook to the webhook server, which reacts at once and is the one allowed
    custom service.

### Alternative F: OpenSRE's own scheduler (`opensre cron`)

*   **Pros**: Configuration only. A recurring prompt could check firing alerts
    through OpenSRE's Alertmanager integration.
*   **Cons**: Untested signed out; results need a delivery target (Slack,
    Telegram) because the shell inbox needs sign-in; minutes of delay; model
    cost on every run even when nothing is firing; OpenSRE would have to
    find the alert labels itself, so exact runbook matching is less reliable.
*   **Reason for Rejection**: Rejected by author in favour of the webhook
    server.

### Alternative G: Running `opensre ask` by hand for every alert

*   **Pros**: No custom code at all.
*   **Cons**: Drops automatic triggering (G5); each run depends on the engineer
    typing the exact alert name and labels.
*   **Reason for Rejection**: Rejected by author: the webhook server is
    allowed for this purpose. Manual `opensre ask` stays available for CI
    runs and debugging.

### Alternative H: A lab script for faults and manifest generation

*   **Pros**: One command per fault and reset; alert labels and the runbook
    manifest generated from `scenarios.yaml` and checked in CI, so they cannot
    drift apart.
*   **Cons**: Custom code outside OpenSRE.
*   **Reason for Rejection**: Rejected by author: the only exemption is the
    webhook server. Written procedures and a checklist replace it.

### Alternative I: GitLab in the cluster, or Argo Workflows/Tekton for CI

*   **Pros**: Everything local; no public repo.
*   **Cons**: GitLab needs about 5-7 GiB, more than half of OrbStack's memory.
    OpenSRE has no Argo Workflows or Tekton integration, and its CI skills are
    written for GitHub, so CI failures there would be invisible to it.
*   **Reason for Rejection**: Rejected by author: GitHub and GitHub Actions on
    a public repo.

### Alternative J: Self-hosted GitHub runner on the Mac

*   **Pros**: CI could deploy straight to the cluster.
*   **Cons**: On a public repo, anyone's fork can run code on the runner, which
    is the author's laptop.
*   **Reason for Rejection**: Not chosen for security. GitHub-hosted runners
    plus ArgoCD pulling from the repo give the same delivery with no inbound
    access.

### Alternative K: The full original stack

*   **Pros**: Covers Kafka, Temporal, ClickHouse, MariaDB and profiling
    failures.
*   **Cons**: Does not fit in 12 GiB as single instances with production
    structure; Pyroscope has no OpenSRE integration.
*   **Reason for Rejection**: Rejected by author: kept light with Loki, Mimir,
    Tempo, Grafana, PostgreSQL, Redis, MongoDB and ArgoCD.

### Alternative L: Prometheus instead of Mimir

*   **Pros**: Lighter; OpenSRE's Grafana tools read Prometheus-style metrics.
*   **Cons**: Differs from the stack the author named.
*   **Reason for Rejection**: Not chosen: Mimir in single-binary mode fits the
    budget with a 1 GiB limit. Prometheus stays the fallback if Phase 2
    measures too little headroom.

### Alternative M: OpenSRE's default models, or one model per role

*   **Pros**: Defaults need no setting; per-role models can put a small, fast
    model on simple steps.
*   **Cons**: The default tool-calling model (Llama 3.1 8B) is the step most
    likely to miss the runbook call. Per-role tuning multiplies the test runs.
*   **Reason for Rejection**: Rejected by author: one model for all roles via
    `NVIDIA_MODEL`, chosen by testing.

### Alternative N: OpenSRE pushing CI fixes through a coding agent

*   **Pros**: Tests OpenSRE's full repair flow.
*   **Cons**: Needs a second, separately authenticated coding agent and write
    access to the repo.
*   **Reason for Rejection**: Rejected by author: CI fixes are printed to
    standard output, not pushed.

### Alternative O: NVIDIA key and token as GitHub Actions secrets

*   **Pros**: The author accepted it, planning to revoke keys afterwards.
*   **Cons**: Not needed: OpenSRE runs on the Mac, not in Actions, so the keys
    only add exposure.
*   **Reason for Rejection**: Not chosen: keys stay in the local `.env`; CI
    uses only GitHub's built-in `GITHUB_TOKEN`.

### Alternative P: All ~30 scenarios before the first test

*   **Pros**: Full coverage from the start.
*   **Cons**: About 150 pieces of work (fault, alert, manifest entry, runbook,
    diagnosis per scenario) before knowing whether OpenSRE answers well on
    NVIDIA models.
*   **Reason for Rejection**: Deferred: six scenarios first, one per tool path,
    then the rest in Phase 4.

--------------------------------------------------------------------------------

## Non-Functional Requirements

*   **Security & Privacy**: The repo is public. Secrets live only in the local
    `.env` (gitignored) and in Kubernetes Secrets created by hand from
    `SETUP.md`; no secret value is written to a repo file, Helm values file or
    Actions log. OpenSRE gets read-only accounts for every database, Grafana
    (Viewer token) and ArgoCD (read-only account). The GitHub token is
    fine-grained, limited to this repo, with read access to contents and
    Actions. OpenSRE's telemetry and prompt logging are turned off. Run
    records in `runs/` stay local because they contain cluster details.
*   **Performance & Cost**: One investigation at a time. Each run's duration
    and token use are recorded. Grafana's repeat interval is set to 4 hours so
    a firing alert does not start repeated runs, and the webhook server also
    ignores repeats of a fingerprint it has handled.
*   **Rollout & Rollback**: Every fault has an "off" procedure, and
    `faults/reset.md` returns the whole system to the `baseline` tag. The lab
    can be removed with `kubectl delete namespace` for its four namespaces plus
    `argocd`, and the GitHub repo deleted when the test ends. The author
    revokes the NVIDIA key and GitHub token at the end.

--------------------------------------------------------------------------------

### Additional Resources

*   OpenSRE source at commit `1f817d29`; local copies of the files used in
    `.egm/opensre-source/` (README, runbook-guided investigations, headless
    CLI, Python API, GitHub and Grafana integration docs, CI skills, account
    gate).
*   `concepts_brief.md`: Goldfish brainstorm review, 5 Blockers, 9 Major,
    7 Nits.

### Future Improvements

*   **Applying fixes**: let OpenSRE push CI fixes once a coding agent that runs
    on NVIDIA models is available.
*   **Generated wiring**: if hand-matched labels cause repeated `not_found`
    runs, reconsider generating alert labels and the manifest from
    `scenarios.yaml`.
*   **More of the original stack**: Kafka, Temporal, ClickHouse or MariaDB
    scenarios on a machine with more memory.

--------------------------------------------------------------------------------

## Detailed Implementation Plan

All paths are relative to the repo root `opensre-test/`. Versions of
container images and Helm charts are pinned to the newest stable release on
the day they are added, and recorded in the file that uses them. The first
six scenarios are: `k8s-oom-kill`, `pg-slow-query`, `redis-eviction`,
`orders-latency`, `argocd-drift`, `ci-broken-test`.

### Target Files to Create/Modify

#### 1. `.gitignore` (Create)

*   **Type / Scope**: Repo configuration.
*   **Proposed Changes**: Ignores `.env`, `runs/`, `.egm/`,
    `concepts_brief.md`, `design_draft.md`, Python caches and virtual
    environments. Stops secrets and local notes from being pushed.

#### 2. `.env.example` (Create)

*   **Type / Scope**: Configuration template.
*   **Proposed Changes**: Every variable from the OpenSRE settings table in
    the Technical Plan, plus `WEBHOOK_PORT=8088` and `OPENSRE_CALL=cli|sdk`,
    with empty values and a one-line comment each. The real `.env` is copied
    from it. The existing bare NVIDIA key in `.env` is rewritten as
    `NVIDIA_API_KEY=...`.

#### 3. `README.md` (Create)

*   **Type / Scope**: Documentation.
*   **Proposed Changes**: What the lab is, the architecture diagram, the
    phases, links to `SETUP.md`, `catalogue/`, `faults/`, `runbooks/` and
    `webhook/`, and a notice that the repo is a test lab with deliberate
    faults.

#### 4. `SETUP.md` (Create)

*   **Type / Scope**: Manual procedure.
*   **Proposed Changes**: Step-by-step commands, in order:
    1.  Phase 0: install OpenSRE from source at `1f817d29` with `uv`; load
        `.env`; run `opensre integrations verify github`; register the demo
        runbook source; run the Phase 0 prompts through the CLI and the SDK;
        analyse a failed Actions run; record results in `docs/phase0.md`.
    2.  Phase 1: try 2-3 NVIDIA Build models through `NVIDIA_MODEL`; record
        results in `docs/model-choice.md`.
    3.  Phase 2: create the repo with `gh repo create
        kirankumar-grootan/opensre-lab --public`; turn on branch protection,
        push protection and secret scanning with `gh api`; create namespaces;
        create Secrets with `kubectl create secret` (database passwords,
        read-only users, Grafana admin, ArgoCD read-only account); install
        ArgoCD from its Helm chart with `deploy/argocd/values.yaml`; apply
        `deploy/argocd/root.yaml`; create the Grafana Viewer token and ArgoCD
        token and add them to `.env`; register the runbook source with
        `opensre runbooks add github`.
    4.  Phase 3: start the webhook server; run the six scenarios.
    *   Each step ends with the check that proves it worked.

#### 5. `catalogue/scenarios.yaml` (Create)

*   **Type / Scope**: Data, the single source of scenario identity.
*   **Proposed Changes**: One entry per scenario:

    ```yaml
    - id: pg-slow-query
      track: incident            # incident | ci
      phase: 3                   # 3 = first six, 4 = later
      alertname: PostgresSlowQuery
      service: orders
      labels: {severity: critical, scenario: pg-slow-query}
      switch: git                # runtime | git | direct | branch
      procedure: faults/pg-slow-query.md
      runbook: runbooks/pg-slow-query.md
      expected_diagnosis: >-
        Orders list query does a sequential scan on orders.customer_id after
        the index was dropped by migration 0042; p95 latency rose above 2s.
      evidence: [pg_stat_statements top query, orders p95 in Mimir, slow spans in Tempo]
    ```

    It lists all scenarios from goals G3 and G4. Phase 3 holds the first six;
    the rest are marked `phase: 4`.

#### 6. `catalogue/README.md` (Create)

*   **Type / Scope**: Documentation and checklist.
*   **Proposed Changes**: Field meanings, and the checklist for adding a
    scenario: alert rule labels match the manifest entry exactly; no two
    manifest entries are equally specific; `service` equals the service's
    `service_name`; runbook file and fault procedure exist;
    `opensre runbooks verify lab-runbooks` passes.

#### 7. `.opensre/runbooks.yaml` (Create)

*   **Type / Scope**: OpenSRE runbook manifest (strict YAML, version 1).
*   **Proposed Changes**: One entry per scenario, written by hand from
    `scenarios.yaml`: `id`, `title`, `document: runbooks/<id>.md`, and `match`
    with `alertname`, `service` and `labels`. CI scenarios use
    `alertname: CIFailure`, `service: <workflow job>` and
    `labels: {failure: <id>}`.

#### 8. `runbooks/README.md` and `runbooks/<id>.md` (Create)

*   **Type / Scope**: Runbook knowledge base.
*   **Proposed Changes**: `README.md` defines the six-section format from the
    Technical Plan. One runbook per scenario (six in Phase 3), each written
    for this stack: the checks name the exact Loki query, Mimir metric, Tempo
    search, Kubernetes resource or database query to read; the Rules section
    holds the team's decisions (for example, `ci-broken-test`: "fix the code
    or the test, never skip or delete the test; a failing test on `main` blocks
    delivery"). No runbook contains commands with real credentials.

#### 9. `faults/README.md`, `faults/reset.md`, `faults/<id>.md` (Create)

*   **Type / Scope**: Manual procedures.
*   **Proposed Changes**: `README.md` explains the three switch kinds and the
    one-fault-at-a-time rule. `reset.md`: clear every key in the
    `shop-faults` ConfigMap; `git reset` `main` to the `baseline` tag and push;
    `argocd app sync` every app; re-run the seed Jobs; wait until all pods are
    ready and Grafana shows no firing alerts. Each `<id>.md` has four parts:
    pre-check (no fault active), "on" commands, what to expect and how long,
    "off" commands.

    The first six:

    | ID | Switch | On |
    | --- | --- | --- |
    | `k8s-oom-kill` | runtime | `kubectl patch configmap shop-faults` sets `catalog.leak_mb_per_req=2`; catalog's memory grows until its 256 MiB limit kills it |
    | `pg-slow-query` | git | apply `faults/pg-slow-query.patch` (adds migration that drops `orders_customer_id_idx`), push, `argocd app sync shop` |
    | `redis-eviction` | direct | `kubectl exec` into Redis and load 300 MB of keys with `redis-cli --pipe` from `faults/redis-fill.txt`; catalog cache keys are evicted and MongoDB load rises |
    | `orders-latency` | runtime | sets `orders.extra_latency_ms=1500`; storefront p95 and timeouts rise |
    | `argocd-drift` | direct | `kubectl scale deployment worker --replicas=0` in the `drift` app (self-heal off); ArgoCD shows OutOfSync, jobs queue up in Redis |
    | `ci-broken-test` | branch | `gh workflow run checks.yml --ref scenario/ci-broken-test` |

#### 10. `faults/pg-slow-query.patch`, `faults/redis-fill.txt` (Create)

*   **Type / Scope**: Fault data.
*   **Proposed Changes**: The prepared git change and the Redis load data used
    by the procedures above. Later git-switched faults add their own `.patch`.

#### 11. `services/shoplib/` (Create)

*   **Type / Scope**: Shared Python package for the sample services.
*   **Proposed Changes**: `telemetry.py` sets up OpenTelemetry traces, metrics
    and JSON logs with `service.name`, exporting OTLP to
    `alloy.observe:4317`. `faults.py` reads the mounted `shop-faults`
    ConfigMap file every 5 seconds and exposes the current flags
    (`extra_latency_ms`, `error_rate`, `leak_mb_per_req`, `timeout_ms`,
    `retry_storm`, `hold_lock_seconds`, `pool_size`). `pyproject.toml`.

#### 12. `services/{storefront,orders,catalog,worker}/` (Create)

*   **Type / Scope**: Python services (FastAPI; `worker` is a plain process).
*   **Proposed Changes**: Each has `app/main.py`, `tests/`, `pyproject.toml`
    and `Dockerfile` (multi-stage, non-root, Python slim base).
    *   `storefront`: `GET /products`, `POST /checkout`, `GET /orders/{id}`;
        calls `catalog` and `orders` over HTTP with a timeout and retries
        taken from the fault flags.
    *   `orders`: `POST /orders`, `GET /orders?customer_id=`; PostgreSQL
        through a connection pool; pushes a job to Redis stream
        `orders:jobs`; migrations in `migrations/` run on start.
    *   `catalog`: `GET /products`; MongoDB with a Redis read-through cache;
        the leak flag keeps request data in a module-level list.
    *   `worker`: reads `orders:jobs`, writes invoices to PostgreSQL;
        `hold_lock_seconds` makes it hold a row lock.
    *   Every service: `/healthz`, `/readyz`, and fault flags applied in one
        middleware or loop step.

#### 13. `loadgen/script.js` (Create)

*   **Type / Scope**: k6 traffic script.
*   **Proposed Changes**: Steady 10 requests per second mix: 60% browse
    products, 30% list orders, 10% checkout. Runs forever in the cluster.

#### 14. `seed/postgres.sql`, `seed/mongo.js` (Create)

*   **Type / Scope**: Seed data.
*   **Proposed Changes**: Schema plus about 200k orders and 5k products, so
    a missing index is visible. Loaded by seed Jobs in `deploy/data/`.

#### 15. `deploy/argocd/values.yaml`, `deploy/argocd/root.yaml`, `deploy/argocd/apps/*.yaml` (Create)

*   **Type / Scope**: ArgoCD install values and Applications.
*   **Proposed Changes**: Values for ArgoCD with Dex, notifications and
    ApplicationSet controller off, a read-only local account `opensre`, and
    memory limits. `root.yaml` is the app of apps pointing at
    `deploy/argocd/apps/`. Apps: `observe`, `data`, `shop`, `drift` (worker
    only, self-heal off), each multi-source (Helm chart plus values from this
    repo, or plain manifests). `shop` ignores differences on the
    `shop-faults` ConfigMap data.

#### 16. `deploy/observe/` (Create)

*   **Type / Scope**: Observability Helm values and manifests.
*   **Proposed Changes**:
    *   `loki-values.yaml` (single-binary, filesystem storage, 48h retention).
    *   `tempo-values.yaml` (single binary, 48h retention).
    *   `mimir/` (plain StatefulSet running Mimir with `-target=all`,
        filesystem storage, 1 GiB limit, its config in a ConfigMap).
    *   `alloy-values.yaml` (OTLP receiver, pod log collection, scraping of
        kube-state-metrics, exporters and services, remote write to Mimir).
    *   `kube-state-metrics-values.yaml`, `exporters-values.yaml` (postgres,
        redis, mongodb exporters).
    *   `grafana-values.yaml` with provisioning files:
        `grafana/datasources.yaml` (fixed UIDs `loki`, `mimir`, `tempo`, so
        the `GRAFANA_*_DATASOURCE_UID` settings are known in advance),
        `grafana/contact-points.yaml` (webhook to
        `http://host.orb.internal:8088/alert`),
        `grafana/policies.yaml` (all alerts to the webhook, repeat 4h),
        `grafana/alert-rules/<id>.yaml` (one rule per incident scenario, with
        exactly the labels in `scenarios.yaml`).

#### 17. `deploy/data/` (Create)

*   **Type / Scope**: Plain manifests (StatefulSet, Service, PVC).
*   **Proposed Changes**: PostgreSQL (official image, `pg_stat_statements`,
    512 MiB), Redis (official image, `maxmemory 200mb`,
    `allkeys-lru`, 256 MiB), MongoDB (official image,
    `--wiredTigerCacheSizeGB 0.25`, 768 MiB), each reading passwords from the
    Secrets made in `SETUP.md`; seed Jobs; init scripts creating the
    read-only users; a separate 1 GiB PVC reserved for the later disk-filling
    fault. Services are `LoadBalancer` so OpenSRE on the Mac reaches them at
    OrbStack's `*.k8s.orb.local` addresses.

#### 18. `deploy/shop/` (Create)

*   **Type / Scope**: Manifests for the services, loadgen and fault ConfigMap.
*   **Proposed Changes**: One Deployment and Service per service with
    requests, limits (catalog 256 MiB), probes and image tags written by
    `deliver.yml`; the `shop-faults` ConfigMap mounted into every service; the
    loadgen Deployment; a ResourceQuota on the namespace.

#### 19. `.github/workflows/deliver.yml` (Create)

*   **Type / Scope**: GitHub Actions.
*   **Proposed Changes**: On push to `main` under `services/`: run tests;
    build and push each changed service image to
    `ghcr.io/kirankumar-grootan/opensre-lab/<service>:<sha>`; update the tag
    in `deploy/shop/`; commit with `[skip ci]`. Permissions
    `contents: write`, `packages: write`. The GHCR packages are set to public
    once, by hand, in `SETUP.md`.

#### 20. `.github/workflows/checks.yml` (Create)

*   **Type / Scope**: GitHub Actions.
*   **Proposed Changes**: On pull requests, `workflow_dispatch` and pushes to
    `scenario/ci-*`: lint (ruff), unit tests (pytest), dependency install,
    image build (no push), Trivy scan failing on critical findings. Read-only
    permissions. Job names are the CI scenarios' `service` values.

#### 21. Branch `scenario/ci-broken-test` (Create)

*   **Type / Scope**: Git branch.
*   **Proposed Changes**: Off `main`, one commit that changes the orders total
    calculation so `test_order_total_includes_tax` fails. Later CI scenarios
    each get their own branch.

#### 22. `webhook/server.py`, `webhook/pyproject.toml`, `webhook/README.md` (Create)

*   **Type / Scope**: The one custom service.
*   **Proposed Changes**:

    ```text
    POST /alert  (Grafana webhook JSON)
      for alert in payload.alerts where alert.status == "firing":
        if alert.fingerprint handled in last 4h: skip
        prompt = "Investigate alert {alertname} for service {service} with
                  labels {labels}. Load the configured runbook first and
                  follow it; verify each step with live data."
        queue.put(run(prompt, scenario=labels.scenario))
      return 202

    POST /ci  {run_id, scenario}
      look up alertname/service/labels for scenario in catalogue/scenarios.yaml
      prompt = "Diagnose GitHub Actions run {run_id} in
                kirankumar-grootan/opensre-lab. Load the runbook for alert
                CIFailure, service {service}, labels {failure: scenario} first.
                Say if the cause is CI or code, name it, and print a proposed
                fix. Do not push."
      queue.put(run(prompt, scenario))

    worker: one run at a time
      if OPENSRE_CALL == "cli": opensre --json ask "<prompt>"
      else: start_embedded_session().chat(prompt)
      save runs/<timestamp>-<scenario>.json with prompt, raw output,
      runbook status, cited URL, model, OpenSRE commit, duration
    ```

    It reads `catalogue/scenarios.yaml` only to fill in CI labels. It adds no
    tools to OpenSRE and does not judge answers. `README.md` covers starting
    it with `uv run` and checking it with a test `curl`.

#### 23. `docs/phase0.md`, `docs/model-choice.md`, `docs/results.md` (Create)

*   **Type / Scope**: Result records.
*   **Proposed Changes**: Phase 0 outcome per check; the model comparison
    table (model, correct, runbook matched, duration, tokens); one line per
    scenario run (pass or fail and why), with the run file name.

#### 24. `docs/designs/opensre-local-lab.md` (Create)

*   **Type / Scope**: This design, final version.

### Verification Plan

*   **Phase 0**: `opensre integrations verify github` passes signed out; the
    demo prompt returns `load_runbook_guidance` status `matched` with a
    commit-pinned URL through both the CLI and the SDK; a failed Actions run
    is read and diagnosed. Any failure stops the lab.
*   **Build**: `checks.yml` green on `main`; `deliver.yml` pushes images and
    ArgoCD shows every app Synced and Healthy.
*   **Unit tests**: `pytest` in each service; ruff clean.
*   **Telemetry**: for each service, Grafana shows logs (Loki), metrics
    (Mimir) and traces (Tempo) filtered by `service_name`.
*   **Memory**: `kubectl top pods -A` at steady state; OrbStack memory leaves
    at least 3 GiB free.
*   **Webhook**: a test `curl` of a sample Grafana payload creates one run
    file; the same payload sent twice creates one.
*   **Runbooks**: `opensre runbooks verify lab-runbooks` passes after every
    manifest change.
*   **End to end**: each of the six scenarios run from its procedure; the run
    file shows `matched`, the commit-pinned runbook URL, and a diagnosis that
    matches `expected_diagnosis`; `faults/reset.md` brings every alert back
    to resolved.

--------------------------------------------------------------------------------

*Drafted with EGM*
