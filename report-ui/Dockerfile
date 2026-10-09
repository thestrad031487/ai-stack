FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN pip install --upgrade fastapi uvicorn "anyio>=4.14.2" \
 && pip uninstall -y setuptools wheel \
 && useradd --system --uid 1000 --no-create-home app
COPY app.py .
USER app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]
