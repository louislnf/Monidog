FROM python:3

ADD src/Monidog.py /
ADD src/History.py /
ADD src/Interval.py /
ADD src/WebsiteMonitor.py /
ADD src/WebsiteStatsCalculator.py /
ADD src/ScreenDrawer.py /
ADD urls.txt /

RUN pip install requests

CMD [ "python", "./Monidog.py"]
