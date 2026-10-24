# Refresh this digest deliberately from Docker Official Images and verify with a clean build.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/ams
COPY requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes -r requirements.lock

# Vision extras — need build-essential to compile insightface's Cython extension.
# libgl1 is required by opencv at import time on headless systems.
# Packages are purged after the wheel build to keep the final image lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgl1 \
    && python -m pip install --no-cache-dir \
        "insightface>=0.7,<1" \
        "onnxruntime>=1.18,<2" \
        "opencv-python-headless>=4.10,<5" \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Pre-download buffalo_sc face analysis model at build time so it is baked into
# the image layer and available immediately without a runtime network request.
RUN python -c "\
from insightface.app import FaceAnalysis; \
fa = FaceAnalysis(name='buffalo_sc', providers=['CPUExecutionProvider']); \
fa.prepare(ctx_id=-1, det_size=(320, 320)); \
print('buffalo_sc model ready')"

COPY app ./app
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m scripts.seed_production_demo && exec python -m app.server"]
