FROM python:3.12.3

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

WORKDIR /app

RUN apt-get update -y
RUN apt-get install -y

COPY oblivion/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

