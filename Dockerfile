FROM python:3.9

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN mkdir /web_app_v2
WORKDIR /web_app_v2


RUN apt-get -y update && apt-get install -y firefox-esr
RUN pip3 install --upgrade pip wheel setuptools

COPY requirements.txt .
RUN pip3 install -r requirements.txt

RUN pip3 install scrapy==2.11

COPY ./amazon ./amazon
COPY startup.sh .

CMD ["bash", "./startup.sh"]
