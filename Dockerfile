# Dockerfile
# <--- ¡Cambiado a 3.8.16!
FROM python:3.8.16-slim

# Establecer la carpeta de trabajo dentro del contenedor
WORKDIR /app

# Copiar el archivo de requerimientos e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de tu código
COPY . .

# Comando por defecto (será sobrescrito en docker-compose)
CMD ["echo", "Ready to run service."]