FROM python:3.9-slim
WORKDIR /app
COPY . .
# Añadimos --no-warn-script-location para limpiar la consola
RUN pip install --no-cache-dir --no-warn-script-location -r requirements.txt
CMD ["python", "bot.py"]
