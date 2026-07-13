FROM python:3.11.13-slim-bookworm@sha256:86adf8dbadc3d6e82ee5dd2c74bec2e1c2467cdad47886280501df722372d2e1

WORKDIR /poc
COPY requirements-lock.txt .
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-lock.txt

COPY . .
CMD ["python", "benchmark.py"]
