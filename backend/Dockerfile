FROM python:3.12-slim

WORKDIR /app
# Copy the rest of your application
COPY main.py .
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
