FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Utilisateur non-root dedie : l'API n'a aucune raison de tourner en root dans le conteneur.
RUN groupadd -r appuser && useradd -r -g appuser -s /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
