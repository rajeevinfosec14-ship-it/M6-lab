# CONTROL 1: base image pinned by DIGEST (a mutable tag means the image you scanned is not the one you deployed).
#            SHIPPED PINNED BY TAG ON PURPOSE — verify_image.sh reports this as FAIL. Fixing it is Practical 6.1 Step 4:
#              docker pull python:3.11-slim
#              docker inspect --format='{{index .RepoDigests 0}}' python:3.11-slim
#            then replace the line below with  FROM python:3.11-slim@sha256:<digest>
FROM python:3.11-slim

# CONTROL 2: no .pyc, unbuffered logs (running filesystem matches what was scanned; logs are not lost on kill).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MODEL_VERIFY=1

WORKDIR /srv

# CONTROL 3: dependencies installed BEFORE the code is copied (a code change cannot silently alter which packages
#            were installed, and the layer cache stays honest).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# CONTROL 4: a dedicated non-root user with a fixed uid.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser

# Copy the application and the pre-built, verified model package.
COPY app ./app
COPY model ./model

# CONTROL 5: code and model are owned by root and NOT writable by the app user (a compromised process cannot
#            rewrite its own model or source).
RUN chown -R root:root /srv && chmod -R a-w /srv

# CONTROL 6: drop from root — the container runs as uid 10001, so a container escape does not happen as root.
USER 10001

# CONTROL 7: HEALTHCHECK probes LIVENESS (/healthz), never readiness. Pointing it at /readyz would make a model
#            fault restart the container in a loop and destroy the logs that explain the fault.
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz').status==200 else 1)"

EXPOSE 8000
# CONTROL 8: verification runs at startup, inside the container (a package swapped into a running deployment is
#            refused at /readyz). MODEL_VERIFY=1 is baked in above; do not override it to 0 in production.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
