FROM python:3.12-slim

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/scale_workers.py .

USER 65534:65534

ENTRYPOINT ["python", "scale_workers.py"]
