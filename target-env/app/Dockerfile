FROM python:3.11-slim

# Empêche Python de bufferiser stdout/stderr dans le conteneur -- sinon
# les print() peuvent rester coincés dans un tampon et ne jamais
# apparaître dans `docker compose logs` tant que le process ne s'arrête
# pas. Un classique piège Docker + Python.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]
