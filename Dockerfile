# Stage 1: Tailwind CSS build
FROM node:20-alpine AS tailwind-builder

WORKDIR /build

COPY package*.json ./
RUN npm install

COPY static/css/tailwind.css ./static/css/
COPY tailwind.config.js ./
COPY templates/ ./templates/

RUN npx tailwindcss -i ./static/css/tailwind.css -o ./static/css/tailwind.output.css --minify

# Stage 2: Python Flask app
FROM python:3.11-slim

RUN useradd -m baruser
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py . 
COPY templates/ ./templates/
COPY database/ ./database/
COPY database_images/ ./database_images/

# 🔧 Create target folder and copy CSS output
RUN mkdir -p ./static/css ./static/Media
COPY --from=tailwind-builder /build/static/css/tailwind.output.css ./static/css/tailwind.output.css
COPY static/Media/johnsbahrlandscape.mp4 ./static/Media/johnsbahrlandscape.mp4
COPY secrets.json ./secrets.json


USER baruser
EXPOSE 5000

CMD ["python", "app.py"]


julie@newktennis.com
information@newktennis.com