FROM python:3.9-alpine
WORKDIR /app
COPY main.py /app
RUN pip install --no-cache-dir flask redis
CMD ["python", "main.py"]
