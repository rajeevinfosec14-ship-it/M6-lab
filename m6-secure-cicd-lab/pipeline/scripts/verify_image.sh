#!/usr/bin/env bash
# verify_image.sh IMAGE_TAG — 13 posture assertions a package scanner will never make.
# Each maps to a numbered CONTROL in the Dockerfile. One FAIL ships on purpose (the digest pin).
set -uo pipefail
IMG="${1:-auth-anomaly-api:local}"
fails=0
ok()   { echo "  [ok]   $1"; }
fail() { echo "  [FAIL] $1"; fails=$((fails+1)); }

echo "verify_image.sh — auditing ${IMG}"

# CONTROL 4/6: non-root user
USER_LINE=$(docker inspect --format '{{.Config.User}}' "$IMG" 2>/dev/null)
[ "$USER_LINE" = "10001" ] && ok "image declares a non-root user: 10001" || fail "image does not declare USER 10001 (got '${USER_LINE}')"

RUN_UID=$(docker run --rm --entrypoint id "$IMG" -u 2>/dev/null)
[ "$RUN_UID" = "10001" ] && ok "container runs as uid 10001" || fail "container does not run as uid 10001 (got '${RUN_UID}')"

# CONTROL 5: code and model not writable by the app user
docker run --rm --entrypoint sh "$IMG" -c '[ ! -w /srv/app/main.py ]' && ok "application code is not writable by the app user" || fail "application code is writable"
docker run --rm --entrypoint sh "$IMG" -c '[ ! -w /srv/model/package/model.joblib ]' && ok "model package is not writable by the app user" || fail "model package is writable"
docker run --rm --entrypoint sh "$IMG" -c 'touch /srv/model/package/x 2>/dev/null && echo w || echo ro' | grep -q ro && ok "no new files can be added to the model package" || fail "files can be added to the model package"

# CONTROL 8: verification passes inside the image
docker run --rm --entrypoint python "$IMG" -m model.package_model --verify >/dev/null 2>&1 && ok "model package verifies inside the image" || fail "model package does not verify inside the image"

# CONTROL 1: base image pinned by digest, not tag
if docker history --no-trunc "$IMG" 2>/dev/null | grep -q "@sha256:"; then
  ok "base image is pinned by digest"
else
  fail "base image is pinned by TAG, not digest
         Practical 6.1 Step 4 — pin it with the sha256 digest, then this check passes"
fi

# CONTROL 7: healthcheck probes liveness, not readiness
HC=$(docker inspect --format '{{json .Config.Healthcheck}}' "$IMG" 2>/dev/null)
echo "$HC" | grep -q "/healthz" && echo "$HC" | grep -qv "/readyz" && ok "healthcheck is defined and probes liveness, not readiness" || fail "healthcheck missing or pointed at /readyz"

# CONTROL 2: no .pyc files baked in
docker run --rm --entrypoint sh "$IMG" -c '[ -z "$(find /srv/app -name "*.pyc" 2>/dev/null)" ]' && ok "no .pyc files in the application directory" || fail ".pyc files present in the application directory"

# .dockerignore working: .git and tests excluded
docker run --rm --entrypoint sh "$IMG" -c '[ ! -e /srv/.git ]' && ok "/srv/.git is absent (.dockerignore working)" || fail "/srv/.git leaked into the image"
docker run --rm --entrypoint sh "$IMG" -c '[ ! -e /srv/tests ]' && ok "/srv/tests is absent (.dockerignore working)" || fail "/srv/tests leaked into the image"

# runtime: container becomes ready under the hardened runtime a deployment should add
CID=$(docker run -d --read-only --tmpfs /tmp --cap-drop=ALL --security-opt=no-new-privileges -p 18000:8000 "$IMG" 2>/dev/null)
sleep 6
CODE=$(curl -s -o /dev/null -w '%{http_code}' localhost:18000/readyz 2>/dev/null)
docker rm -f "$CID" >/dev/null 2>&1
[ "$CODE" = "200" ] && ok "the container becomes ready and serves /readyz (read-only, cap-drop=ALL)" || fail "container did not serve /readyz under runtime hardening (got ${CODE})"

echo
if [ "$fails" -eq 0 ]; then
  echo "ALL CHECKS PASSED"
elif [ "$fails" -eq 1 ]; then
  echo "1 check failed — if it is the digest pin, that is expected on a fresh checkout (see Step 4)."
else
  echo "${fails} checks failed."
fi
exit "$fails"
