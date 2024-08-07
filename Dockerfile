FROM python:3.10.12

WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y wget && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9288

CMD [ "python", "./app.py" ]