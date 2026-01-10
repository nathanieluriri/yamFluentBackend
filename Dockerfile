FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7864

CMD ["gunicorn", "-w", "20", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:7864", "--timeout", "120", "--graceful-timeout", "30", "main:app"]
