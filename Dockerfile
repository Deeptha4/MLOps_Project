FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --default-timeout=100 --retries 10 -r requirements.txt

COPY train.py app.py serve.py ./
COPY data ./data
RUN python train.py \
    && useradd --uid 10001 --create-home appuser \
    && chown -R appuser /app
USER 10001

EXPOSE 8501 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8501/_stcore/health')"

CMD ["python", "serve.py"]
