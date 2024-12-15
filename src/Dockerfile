FROM python:alpine
WORKDIR /app
RUN apk update
RUN apk add vim curl
RUN pip install -U pip
ADD requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install slthcore==0.4.3
