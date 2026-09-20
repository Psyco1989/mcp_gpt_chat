FROM python:3.12-slim

LABEL \
    io.hass.version="1.0.4" \
    io.hass.type="app" \
    io.hass.arch="aarch64|amd64"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY run.sh .
COPY www ./www

RUN chmod +x /app/run.sh

EXPOSE 8099

CMD ["/app/run.sh"]
