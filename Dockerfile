FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY nutri_app/ nutri_app/
COPY .env .env

CMD ["python", "-m", "nutri_app"]
