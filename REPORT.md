# DevOps CI/CD Implementation Report: ACEest Fitness & Gym

**Student Name:** Gyanendra Sinha  
**BITS Student ID:** `2025TM93008`  
**Course:** Introduction to DEVOPS (Merged — CSIZG514/SEZG514) — Assignment 2  
**Execution Environment:** Rocky Linux 9.5 Lab VM (2 vCPUs, 7.4 GiB RAM)

## Submission Artifacts & Live Endpoints

- **Public GitHub Repository:** <https://github.com/2025tm93008GyanendraSinha/aceest-fitness-devops-a2>
- **Public Docker Hub Registry:** <https://hub.docker.com/r/gyanendrasinha8301/aceest-fitness>
- **Jenkins CI/CD Pipeline:** <http://localhost:8080/job/ACEest-A2-Pipeline/>
- **SonarQube Quality Dashboard:** <http://localhost:9000/dashboard?id=aceest-fitness-a2>
- **Kubernetes Cluster Endpoints (Minikube + NGINX Ingress):**
  - **Rolling Update:** <http://rolling.aceest.local>
  - **Blue-Green Deployment:** <http://bluegreen.aceest.local>
  - **Canary Release (70/30):** <http://canary.aceest.local>
  - **A/B Testing (`X-User-Group: beta`):** <http://abtest.aceest.local>
  - **Shadow Deployment (Traffic Mirroring):** <http://shadow.aceest.local>

---

## 1. CI/CD Architecture Overview

The **ACEest Fitness & Gym** platform was engineered to demonstrate a production-aligned, test-driven Continuous Integration and Continuous Delivery (CI/CD) workflow, evolving incrementally from `v1.0` through `v2.1`.

### 1.1 End-to-End Pipeline Flow

```text
[Developer Commit / Git Tag]
        │  (GitHub: feature/*, bugfix/*, infra/* -> main)
        ▼
[Jenkins Server (Poll SCM: H/2 * * * *)]
        ├── Stage 1: Checkout & Dynamic APP_VERSION Detection
        ├── Stage 2: Parameterized Non-Root Docker Image Build
        ├── Stage 3: In-Container Flake8 Lint & Pytest + Coverage XML
        ├── Stage 4: SonarQube Static Analysis & Quality Gate Enforcement
        ├── Stage 5: Versioned Build Artifact Packaging (.tar.gz + Reports)
        ├── Stage 6: Automated Push to Docker Hub (vX.Y, build-N, latest)
        └── Stage 7: Automated Kubernetes Deployment & Rollout Verification
                            │
                            ├── Rollout Healthy  ──► Live Traffic via NGINX Ingress
                            └── Rollout Failure  ──► Automatic `kubectl rollout undo`
```

### 1.2 Architectural Layers

#### Modular Multi-Version Application & Version Control

Reusing the Assignment 1 Flask/SQLite foundation, `ACEest_Fitness.py` was refactored to expose `/health`, `/version` (returning the active version and Kubernetes pod hostname), `/clients`, `/workouts`, and `/stats`. Every release (`v1.0.0`, `v2.0.0`, `v2.0.1`, and `v2.1.0`) was developed on dedicated feature or bugfix branches, merged using `--no-ff` to preserve branch topology, archived under `versions/`, and marked with annotated Git tags.

#### Containerization & Registry Versioning

A non-root `python:3.9-slim` Dockerfile accepts `APP_VERSION` as a build argument, configures `HEALTHCHECK`, and isolates application dependencies. All release versions (`v1.0`, `v2.0`, `v2.0.1`, `v2.1`, build-stamped tags, and `latest`) are version-controlled in the public Docker Hub repository `gyanendrasinha8301/aceest-fitness`.

#### Quality Assurance & Static Analysis

Every Jenkins build executes Flake8 and the 11-case Pytest suite inside the newly built container image, extracting `junit.xml` and `coverage.xml`. The containerized `sonar-scanner-cli` then submits source code and coverage to SonarQube Community Build with `sonar.qualitygate.wait=true`, blocking artifact promotion if quality thresholds fail.

#### Kubernetes Orchestration & Progressive Delivery

A Minikube cluster configured with the NGINX Ingress Controller hosts all five progressive delivery strategies concurrently inside the `aceest-fitness` namespace:

1. **Rolling Update (`rolling.aceest.local`):** Zero-downtime replacement using `maxSurge: 1` and `maxUnavailable: 0`, verified with `kubectl rollout undo` rollback.
2. **Blue-Green (`bluegreen.aceest.local`):** Parallel blue (`v1.0`) and green (`v2.1`) Deployments switched instantaneously through Kubernetes Service selector patching.
3. **Canary Release (`canary.aceest.local`):** NGINX Ingress `canary-weight: "30"` routes 70% of traffic to `v1.0` and 30% to `v2.1`, with instant rollback by setting the weight to `"0"`.
4. **A/B Testing (`abtest.aceest.local`):** Deterministic header-based routing (`X-User-Group: beta`) directs standard traffic to `v1.0` and beta users to `v2.1`.
5. **Shadow Deployment (`shadow.aceest.local`):** Asynchronous traffic mirroring (`mirror-target`) duplicates live production requests to `v2.1` in the background while returning `v1.0` responses to users.

---

## 2. Challenges Faced and Mitigation Strategies

| # | Challenge Encountered | Root Cause | Mitigation Strategy Applied |
|---|---|---|---|
| 1 | **Memory Contention on Lab VM (7.4 GiB RAM, 2 vCPUs)** | Running native Jenkins, SonarQube (Elasticsearch + JVM), Docker builds, and Minikube simultaneously risked out-of-memory (OOM) termination. | Tuned SonarQube JVM heaps (`-Xms256m -Xmx512m`), capped Minikube (`--cpus=2 --memory=2200mb`), assigned tight pod limits (`48Mi` request / `128Mi` limit), and stopped SonarQube during pure cluster provisioning while preserving its state in Docker volumes. |
| 2 | **Jenkins Daemon & SELinux Permission Blocks** | The default `jenkins` service user lacked Docker socket access, and Rocky Linux 9.5 SELinux blocked read-only volume mounts into the SonarScanner container. | Added `jenkins` to the `docker` group and restarted the service; used `--security-opt label=disable` with `:ro` workspace mounts and `/tmp/.scannerwork` for SonarScanner; and exported a flattened kubeconfig (`chmod 600`) to `/var/lib/jenkins/.kube/config`. |
| 3 | **False Code Duplication in SonarQube** | Storing archived application versions (`versions/ACEest_Fitness_v*.py`) alongside the active file triggered high duplication metrics. | Configured `sonar.exclusions=venv/**,versions/**,k8s/**,reports/**` in `sonar-project.properties` and remapped container coverage paths (`/app` → `/usr/src`) via `sed` so SonarQube accurately evaluated active source files and test coverage. |
| 4 | **Implementing A/B & Shadow Routing Without a Heavy Service Mesh** | Standard Kubernetes Services do not support HTTP header routing or traffic mirroring, while Istio exceeded the VM's 2-vCPU/RAM budget. | Enabled Minikube's lightweight NGINX Ingress Controller and leveraged native annotations (`canary-weight`, `canary-by-header`, `mirror-target`), achieving all five strategies within approximately 2.2 GiB of cluster memory. |
| 5 | **Distinguishing Active Versions Across Traffic Splits** | Visually proving which pod served responses during Canary, Blue-Green, and Shadow tests required unambiguous runtime telemetry. | Embedded color-coded UI themes (navy blue for `v1.0`, emerald teal for `v2.0+`), a `/version` JSON endpoint returning `APP_VERSION` and pod hostname, and `PYTHONUNBUFFERED=1` for real-time mirrored log inspection. |

---

## 3. Key Automation Outcomes

### 3.1 Zero-Touch End-to-End CI/CD

Pushing a commit to `main` automatically triggers Jenkins through Poll SCM (`H/2 * * * *`), executing all seven stages—build, in-container testing, SonarQube quality gating, artifact archiving, Docker Hub publishing, and Kubernetes deployment—without manual intervention.

### 3.2 Verified Code Quality & Reliability

Automated unit testing grew from 7 tests (`v1.0`) to 11 passing tests (`v2.1`), executed directly inside production container images. This is paired with clean Flake8 linting and a **Passed** SonarQube Quality Gate (0 bugs, 0 vulnerabilities), exported in:

- `reports/sonarqube_quality_gate.json`
- `reports/sonarqube_metrics.json`

### 3.3 Full Traceability Across Versions

Every release is traceable across Git tags (`v1.0.0`–`v2.1.0`), Jenkins-fingerprinted build artifacts (`dist/aceest-fitness-<ver>-build-<N>.tar.gz`), and immutable Docker Hub image tags (`gyanendrasinha8301/aceest-fitness:<tag>`).

### 3.4 Zero-Downtime Delivery & Rapid Recovery

All five Kubernetes deployment strategies operate concurrently behind NGINX Ingress with validated rollback mechanisms. These include automated `kubectl rollout undo` directly inside Jenkins on rollout failure, instantaneous Blue-Green selector switchback, and a weight-`0` Canary cutoff.

---

## 4. Verification Evidence Index (Attach Lab Snapshots Here)

Use the following evidence index to organize screenshots and other lab proof for submission.

| Phase | Evidence to Attach |
|---|---|
| **Phases 1–2** | Lab VM audit, local `v1.0` run, Git branching/tag graph (`v1.0.0`–`v2.1.0`), and GitHub repository view. |
| **Phase 3** | Multi-version Docker builds, in-container Pytest passes, and Docker Hub Tags page (`v1.0`, `v2.0`, `v2.0.1`, `v2.1`, `latest`). |
| **Phase 4** | SonarQube **QUALITY GATE STATUS: PASSED** CLI log and Web UI dashboard metrics. |
| **Phase 5** | Jenkins credentials, Poll SCM-triggered build ("Started by an SCM change"), archived `.tar.gz` artifacts, and green Stage View. |
| **Phases 6–7** | Minikube + NGINX Ingress status; Rolling Update + rollback; Blue-Green cutover + rollback; Canary 70/30 + weight-`0` rollback; A/B header routing; Shadow mirrored pod logs; full `kubectl get all` output; Ingress topology; and seven-stage Jenkins CI/CD completion. |

---

**End of Report**
