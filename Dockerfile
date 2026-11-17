FROM python:3.12-slim

# Carlito = same letter widths as Calibri (used to measure text so it never overflows).
# LibreOffice + poppler make slide previews in the web app (set WITH_PREVIEW=0 for a smaller image).
ARG WITH_PREVIEW=1
RUN apt-get update && apt-get install -y --no-install-recommends fonts-crosextra-carlito \
    $( [ "$WITH_PREVIEW" = "1" ] && echo "libreoffice-impress poppler-utils" ) \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY slidegen ./slidegen
COPY app ./app

RUN useradd -m appuser && chown -R appuser /app
USER appuser
EXPOSE 7860
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
