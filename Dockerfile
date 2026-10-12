FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HDIP_PROJECT_ROOT=/app

WORKDIR /app
COPY pyproject.toml README.md LICENSE constraints-runtime.txt ./
COPY src ./src
RUN python -m pip install -c constraints-runtime.txt .

COPY dashboard ./dashboard
COPY .streamlit ./.streamlit
COPY data ./data
COPY data_contracts ./data_contracts
COPY scripts ./scripts

# Exercise the installed package and bundle freshly validated reporting outputs.
RUN python -m healthcare_di.pipeline

RUN useradd --create-home --user-group --uid 10001 dashboard
USER dashboard

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health', timeout=3)"

CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
