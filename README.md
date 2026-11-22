# ACEest Fitness & Gym — End-to-End DevOps CI/CD Pipeline (Assignment 2)

**Author:** Gyanendra Sinha (BITS ID: `2025TM93008`)  
**Course:** Introduction to DEVOPS (Merged — CSIZG514/SEZG514) — Assignment 2  
**GitHub Repository:** <https://github.com/2025tm93008GyanendraSinha/aceest-fitness-devops-a2>  
**Docker Hub Repository:** <https://hub.docker.com/r/gyanendrasinha8301/aceest-fitness>

---

## 1. Project Overview

This repository implements a fully automated Continuous Integration and Continuous Delivery (CI/CD) pipeline for the **ACEest Fitness & Gym** Flask web application. Building upon the Assignment 1 codebase, this solution evolves the application across multiple tagged releases (`v1.0` -> `v2.0` -> `v2.0.1` -> `v2.1`), enforces automated quality gates via **Pytest**, **Flake8**, and **SonarQube**, publishes immutable multi-version container images to **Docker Hub**, and deploys all five progressive delivery strategies (**Rolling Update**, **Blue-Green**, **Canary Release**, **A/B Testing**, and **Shadow Deployment**) with verified rollback mechanisms on **Kubernetes (Minikube + NGINX Ingress Controller)**.

---

## 2. Technology Stack

- **Application & Runtime:** Python 3.9, Flask, SQLite, Jinja2 Templates
- **Version Control:** Git & GitHub (feature/bugfix/infra branching + semantic tags `v1.0.0`, `v2.0.0`, `v2.0.1`, `v2.1.0`)
- **Testing & Linting:** Pytest, `pytest-cov`, Flake8 (executed inside built containers)
- **Static Code Analysis:** SonarQube Community Build + `sonar-scanner-cli` (Quality Gate enforced)
- **Containerization & Registry:** Docker (non-root `python:3.9-slim` image) & Docker Hub (`gyanendrasinha8301/aceest-fitness`)
- **CI/CD Orchestration:** Jenkins Declarative Pipeline (`Jenkinsfile`) with Poll SCM (`H/2 * * * *`)
- **Deployment & Orchestration:** Kubernetes (Minikube) + NGINX Ingress Controller

---

## 3. Repository Structure

```text
aceest-fitness-devops-a2/
├── ACEest_Fitness.py                # Active Flask application (v2.1)
├── versions/                        # Archived incremental application versions
│   ├── ACEest_Fitness_v1_0.py
│   ├── ACEest_Fitness_v2_0.py
│   ├── ACEest_Fitness_v2_0_1.py
│   └── ACEest_Fitness_v2_1.py
├── templates/index.html             # Version-aware web UI dashboard
├── tests/test_app.py                # 11-case automated Pytest suite
├── Dockerfile                       # Parameterized, non-root container build
├── sonar-project.properties         # SonarQube project & coverage config
├── Jenkinsfile                      # 7-stage end-to-end CI/CD pipeline
├── k8s/                             # Kubernetes manifests for all 5 strategies
│   ├── 00-namespace.yaml
│   ├── 01-smoke-test.yaml
│   ├── 02-rolling-update.yaml
│   ├── 03-blue-green.yaml
│   ├── 04-canary.yaml
│   ├── 05-ab-testing.yaml
│   └── 06-shadow.yaml
└── reports/                         # Exported Pytest, Coverage, SonarQube & Final Report
    ├── coverage.xml
    ├── junit.xml
    ├── sonarqube_quality_gate.json
    ├── sonarqube_metrics.json
    └── Assignment_2_CI_CD_Report.md
```

---

## 4. Application Version History

| **Release Tag** | **Docker Hub Tag** | **Key Changes** | **Test Suite** |
|---|---|---|---|
| `v1.0.0` | `v1.0` | Baseline Flask app, client management, `/health`, `/version`, navy-blue UI | 7 tests |
| `v2.0.0` | `v2.0` | Added `/workouts` module and emerald-teal `v2.0` UI banner | 9 tests |
| `v2.0.1` | `v2.0.1` | Bugfix enforcing positive integer validation on `duration_mins` | 10 tests |
| `v2.1.0` | `v2.1`, `latest` | Added `/stats` summary endpoint; automated Jenkins Poll SCM & K8s CD | 11 tests |

---

## 5. Local Setup & Manual Testing

```bash
git clone https://github.com/2025tm93008GyanendraSinha/aceest-fitness-devops-a2.git
cd aceest-fitness-devops-a2
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt

# Run unit tests with coverage and linting
flake8 ACEest_Fitness.py tests/test_app.py --max-line-length=88
python3 -m pytest -v --cov=ACEest_Fitness --cov-report=term-missing tests/

# Run locally on http://127.0.0.1:5000
python3 ACEest_Fitness.py
```

---

## 6. Automated Jenkins CI/CD Pipeline (`Jenkinsfile`)

Triggered automatically via **Poll SCM (`H/2 * * * *`)** on every commit to `main`:

1. **Checkout & Version Detection:** Pulls source code and parses `APP_VERSION` dynamically.
2. **Build Versioned Docker Image:** Builds `vX.Y`, `vX.Y-build-<N>`, and `latest` tags.
3. **In-Container Lint & Pytest Validation:** Runs `flake8` and `pytest --cov` *inside* the built image and extracts `junit.xml` and `coverage.xml`.
4. **SonarQube Analysis & Quality Gate:** Runs `sonar-scanner-cli` with `sonar.qualitygate.wait=true` and exports Quality Gate & metrics JSON reports.
5. **Package Versioned Build Artifacts:** Archives versioned `.tar.gz` bundles and test/SonarQube reports in Jenkins.
6. **Push Versioned Images to Docker Hub:** Authenticates via Jenkins Credentials and publishes all tags to `gyanendrasinha8301/aceest-fitness`.
7. **Deploy to Kubernetes & Verify Rollout (CD):** Applies Kubernetes manifests, updates `aceest-rolling` to the new build tag, verifies `kubectl rollout status`, and triggers an automatic `kubectl rollout undo` if the rollout fails.

---

## 7. Kubernetes Deployment Strategies & Endpoints

All five strategies run simultaneously inside namespace `aceest-fitness` on Minikube behind the NGINX Ingress Controller:

| **Strategy** | **Cluster Endpoint URL** | **Verification Command** | **Rollback Mechanism** |
|---|---|---|---|
| **Rolling Update** | `http://rolling.aceest.local` | `curl http://rolling.aceest.local/version` | `kubectl rollout undo deployment/aceest-rolling -n aceest-fitness` |
| **Blue-Green** | `http://bluegreen.aceest.local` | `curl http://bluegreen.aceest.local/version` | Patch `aceest-bluegreen-svc` selector back to `slot: blue` |
| **Canary (70/30)** | `http://canary.aceest.local` | 20x loop on `http://canary.aceest.local/version` | Annotate `canary-weight="0"` on `aceest-canary-split-ing` |
| **A/B Testing** | `http://abtest.aceest.local` | Default vs. `-H "X-User-Group: beta"` | Remove/disable `aceest-ab-beta-ing` Ingress rule |
| **Shadow** | `http://shadow.aceest.local` | Check `v1.0` response + `aceest-shadow-v2` pod logs | Remove `mirror-target` annotation on `aceest-shadow-ing` |
