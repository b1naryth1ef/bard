FROM python:3.7

RUN apt-get update && apt-get install -y --no-install-recommends python3-lxml

ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

EXPOSE 7675/tcp

ADD . /var/lib/bard
WORKDIR /var/lib/bard
CMD ["python", "manage.py", "serve", "-s"]
