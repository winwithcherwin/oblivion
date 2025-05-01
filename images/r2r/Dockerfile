FROM python:3.12.3-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN \
	apt-get update -y && apt-get upgrade -y && apt-get install -y \
	libgit2-dev -y && \
	apt-get clean && \
	rm -rf /var/lib/apt/lists/*

RUN \
	pip install --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt && \
	rm -rf /root/.cache

COPY . .

