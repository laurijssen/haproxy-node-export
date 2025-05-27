FROM python:alpine

WORKDIR /app
COPY main.py .

RUN pip install --no-cache-dir kubernetes requests

CMD ["python", "main.py"]
