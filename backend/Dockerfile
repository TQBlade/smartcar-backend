# ============================================================
#  Dockerfile - Backend SmartCar (Flask)
# ============================================================

# Imagen base de Python
FROM python:3.11

# Crear el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiar archivos del proyecto al contenedor
COPY . /app

# Instalar dependencias necesarias
RUN pip install --no-cache-dir flask flask-cors psycopg2-binary jwt reportlab openpyxl

# Exponer el puerto de Flask
EXPOSE 5000

# Comando por defecto para ejecutar el servidor
CMD ["python", "server.py"]
