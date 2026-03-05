FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# python-runner is used as a library by the hub/agent; no separate entry point needed.
CMD ["python", "-c", "print('python-runner ready')"]
