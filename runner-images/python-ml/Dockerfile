# Sandbox image for Python bundle submissions.
# Allowlisted scientific stack only; no compilers, no network at runtime.
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 TORCH_HOME=/tmp HOME=/tmp MPLCONFIGDIR=/tmp

RUN pip install --no-cache-dir "numpy>=2,<3" "scipy>=1.13" "scikit-learn>=1.5" \
 && pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
 && find /usr/local/lib/python3.12 -name "__pycache__" -type d -prune -exec rm -rf {} + \
 && useradd --uid 1000 --no-create-home --shell /usr/sbin/nologin runner \
 && mkdir -p /bundle /inputs /opt/runner && chmod 555 /bundle /inputs

COPY run_submission.py /opt/runner/run_submission.py
RUN chmod 444 /opt/runner/run_submission.py

USER 1000:1000
WORKDIR /tmp
ENTRYPOINT ["python", "-I", "/opt/runner/run_submission.py"]
