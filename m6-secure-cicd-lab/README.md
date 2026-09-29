# Module 6 — Secure CI/CD Pipeline (hands-on repo)

**Enterprise AI Development Lifecycle · Level 2 — Building Secure AI Systems**

This is the **hands-on, do-it-on-GitHub** half of Module 6. The runnable model-security core
(packaging, tamper detection, verification-as-refusal, the contract, and the local gates) is in the
Colab notebook `Module_6_Practical_6.1_Package_Verify_Serve.ipynb`. Here you take those same gates,
run them in **GitHub Actions**, and then do the one step a notebook cannot demonstrate: **protect the
branch** so a failing gate actually blocks a merge.

> The one idea: *a security control that reports is not a security control that prevents.* The pipeline
> below runs, reports, and turns red on failure — and until you check one box in the repository
> settings, it stops nothing at all. That box is the exact analogue of `MODEL_VERIFY=1` in the notebook.

---

## For the instructor — publish this once

1. Create a new **public** GitHub repo (e.g. `m6-secure-cicd-lab`).
2. From this folder: `git init && git add . && git commit -m "Module 6 secure CI/CD lab" && git branch -M main`
3. `git remote add origin https://github.com/<you>/m6-secure-cicd-lab.git && git push -u origin main`
4. Confirm the **Actions** tab shows the `security-pipeline` workflow running green.
5. Share the repo URL with trainees and tell them to **Fork** it.

## For the trainee — the exercise

### 0. Fork and enable Actions
- Click **Fork** (top-right). In your fork, open the **Actions** tab and click **"I understand my
  workflows, enable them"**. The pipeline runs on your next push and on every pull request.

### 1. Read the six gates
Open `.github/workflows/security-pipeline.yml`. Six jobs answer six questions, and a seventh —
`security-gates` — does nothing except fail if any of the six failed. That aggregate is what branch
protection points at.

| Gate | Job | Asks |
|---|---|---|
| 1 | `tests` | does the endpoint accept and reject exactly what the contract promises? |
| 2 | `sast` | ruff + bandit — any dangerous patterns in the code? |
| 3 | `secrets` | any hardcoded credentials? |
| 4 | `deps` | are dependencies pinned, and does the dependency review pass? |
| 5 | `image` | build the container and scan it; fail on a fixable CRITICAL |
| — | `security-gates` | the aggregate branch protection requires |

### 2. Run four gates locally first (fast feedback)
```bash
cd serving
python -m pytest tests/ -q                              # Gate 1
ruff check . && bandit -r app model -c pyproject.toml -q   # Gate 2
bash ../pipeline/scripts/secret_backstop.sh ..          # Gate 3
python3 ../pipeline/scripts/check_pins.py requirements.txt   # Gate 4
```

### 3. Break each gate on purpose, and watch it go red
*A gate that has only ever passed is a gate you have not tested.*

| Gate | How to break it | What you should see |
|---|---|---|
| 1 tests | change a bound in `app/contract.py` | a named test fails, naming the field |
| 2 SAST | add `subprocess.run(cmd, shell=True)` to `app/main.py` | ruff `S602` / bandit `B602` |
| 3 secrets | add `AWS_KEY = "AKIAIOSFODNN7EXAMPLE"` | `[FINDING] AWS access key id`, exit 1 |
| 4 deps | change a pin to `fastapi>=0.100` | `not an exact pin`, exit 1 |
| 5 image | point `FROM` at an older base | Trivy reports CRITICALs, the job fails |

### 4. Turn the reports into gates — protect `main`
**Settings → Branches → Add branch protection rule** for `main`:
- [x] Require a pull request before merging
- [x] Require status checks to pass before merging → add **`security-gates`**
- [x] Require branches to be up to date before merging
- [x] **Do not allow bypassing the above settings**  ← *including administrators*

> The last box is the one people skip. Leaving it unchecked means the person most likely to be rushed
> at 6pm on a Friday is exactly the person who can bypass every gate you just built. **Screenshot this
> page** — it is the only evidence that the pipeline is a gate rather than a report.

### 5. Prove it end to end
Open a pull request that deliberately fails a gate (add the fake AWS key from step 3). Confirm the
**merge button is actually disabled**. A red check beside an enabled merge button is not a gate — do
not take the settings page's word for it; make the pull request.

**Deliverable:** the PR number, which gate went red, and whether merge was blocked, plus the branch-protection screenshot.

---

## Two decisions inside Gate 5 worth defending

- **The scan runs twice.** A single gating pass produces no report when it fails — which is exactly when
  you want the report. Two passes cost one extra scan and guarantee the evidence artifact exists; the
  `if: always()` upload is the other half of the same idea.
- **`ignore-unfixed: true` is a policy decision, not a default.** It tells Trivy to skip vulnerabilities
  with no available fix, so the gate stays actionable. It is also a real reduction in coverage: a
  CRITICAL with no fix is still exploitable. The honest position has three parts — keep the flag so the
  gate stays actionable, keep the **full** report (the first, non-gating scan) so unfixed findings are
  recorded, and review that list on a schedule rather than never.

## The container read-through — `serving/Dockerfile`

Docker cannot run in Colab, so read the container here. The `Dockerfile` has **eight numbered CONTROL
comments**; `pipeline/scripts/verify_image.sh` runs **thirteen assertions** against the built image,
every one of them something an image scanner will never tell you (does it run as root? is the code
writable? does the package verify at startup?).

**The digest check fails on a fresh checkout — deliberately.** The shipped `Dockerfile` pins the base
image by **tag**, and `verify_image.sh` reports that as `[FAIL]`. Fixing it is the exercise:
```bash
docker pull python:3.11-slim
docker inspect --format='{{index .RepoDigests 0}}' python:3.11-slim
# put python:3.11-slim@sha256:<digest> into the FROM line, rebuild, and the check passes
```
A digest written in by someone else would be specific to their moment and architecture, would fail on
your machine, and would teach you nothing.

If you have Docker locally:
```bash
cd serving
docker build -t auth-anomaly-api:local .
bash ../pipeline/scripts/verify_image.sh auth-anomaly-api:local
# then confirm the API still works under the strongest runtime controls:
docker run --rm -p 8000:8000 --read-only --tmpfs /tmp --cap-drop=ALL --security-opt=no-new-privileges auth-anomaly-api:local
```

## What this pipeline still does NOT do

Naming these is not an apology — *passing one check never proves the release is safe.*

| Missing | Why it is out of scope here |
|---|---|
| Image signing (cosign) | needs a registry and a signing key |
| Registry promotion by digest | this lab never pushes an image |
| Policy-as-code admission control | needs a cluster (OPA/Gatekeeper or Kyverno) |
| SLSA provenance attestation | builds on signing |
| Hash-verified dependencies | `--require-hashes` files are platform-specific |

---
*InfosecTrain · Enterprise AI Development Lifecycle · Module 6 · GitHub hands-on*
