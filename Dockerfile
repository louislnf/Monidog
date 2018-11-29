FROM python:3

COPY src/ /
COPY requirements.txt /
COPY urls.txt /

RUN pip install -r /requirements.txt

CMD [ "python", "./Monidog.py"]
