FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
ENV SITEWATCH_DB=/data/sitewatch.db
VOLUME /data
EXPOSE 8000
# One worker only: the background checker runs inside the web process.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
