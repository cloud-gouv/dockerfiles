FROM python:3.12-slim

# readOnlyRootFilesystem dans la chart : pas de .pyc à écrire.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/vm_power ./vm_power

USER 65534:65534

ENTRYPOINT ["python", "-m", "vm_power"]
