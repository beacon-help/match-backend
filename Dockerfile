FROM python:3.13-alpine

RUN apk update && apk add bash

WORKDIR /usr/app

COPY requirements.txt .


RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /usr/app
# COPY format-tools/isort.sh ./format-tools/isort.sh

# RUN chmod +x ./format-tools/isort.sh

CMD ["uvicorn", "match.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
