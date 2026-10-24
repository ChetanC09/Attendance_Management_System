# Refresh this digest deliberately from Docker Official Images and verify with a clean build.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/ams
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock

# Vision extras — installed without hash-lock because they are optional platform
# dependencies compiled for the target Linux ABI. Pinned to the same version
# ranges declared in pyproject.toml [project.optional-dependencies].vision.
# buffalo_sc is the compact InsightFace model (~35 MB total weights, ~150 MB RAM
# at inference) — suitable for 512 MB containers. buffalo_l requires >400 MB RAM.
RUN python -m pip install --no-cache-dir \
    "insightface>=0.7,<1" \
    "onnxruntime>=1.18,<2" \
    "opencv-python-headless>=4.10,<5"

# Pre-download buffalo_sc face analysis model at build time so it is baked into
# the image layer and available immediately without a runtime network request.
RUN python -c "\
from insightface.app import FaceAnalysis; \
fa = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider']); \
fa.prepare(ctx_id=-1, det_size=(320, 320)); \
print('buffalo_sc model ready')"

COPY app ./app
COPY scripts/seed_admin.py ./scripts/seed_admin.py
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000
CMD ["python", "-m", "app.server"]
