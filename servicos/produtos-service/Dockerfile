FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY adaptadores ./adaptadores
COPY servidor.py .

RUN useradd --uid 1000 --create-home appuser
USER appuser

ENV PYTHONUNBUFFERED=1 PORT=8102
EXPOSE 8102
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8102/health', timeout=2)"
CMD ["python", "servidor.py"]
