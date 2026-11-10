# opensre-lab

A local test lab for trying [OpenSRE](https://github.com/Tracer-Cloud/opensre)
on two jobs: diagnosing failed CI runs and investigating incidents on a small
Kubernetes system (OrbStack), with runbooks it must follow.

This repo contains deliberate faults. Branches named `scenario/*` are broken on
purpose.

Design: [docs/designs/opensre-local-lab.md](docs/designs/opensre-local-lab.md).
Status: Phase 0 (signed-out OpenSRE check), see `docs/phase0.md` once written.
