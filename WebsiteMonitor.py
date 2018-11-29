
import requests, time, threading

from History import History
from Interval import Interval


class WebsiteMonitor:
    def __init__(self, url, checkInterval):
        self.url = url
        self.checkInterval = checkInterval
        # calculating the number of checks in an hour to initialize the history
        maxNumberOfChecksSaved = int(round(3600.0/checkInterval))
        self.checksHistory = History(maxNumberOfChecksSaved)
        # the history may be used by other threads, thus we protect it with a lock
        self.historyLock = threading.Lock()
        # interval keeps track of the Interval instance that execute self.check every self.checkInterval
        self.interval = None
        # keeps track of when the monitor was launched
        self.startedMonitoringTime = time.time()

    def check(self):
        # HTTP HEAD request to the url of the monitored website
        # measurez
        success = True
        checkTime = time.time()
        try:
            r = requests.head(self.url)
        except requests.exceptions.RequestException:
            success = False
        responseTime = time.time()-checkTime

        with self.historyLock:
            self.checksHistory.add((
                -1 if not(success) else r.status_code,
                checkTime,
                -1.0 if not(success) else responseTime,
            ))
    
    def startMonitoring(self):
        self.startedMonitoringTime = time.time()
        self.interval = Interval(self.checkInterval, self.check)
    
    def stopMonitoring(self):
        if self.interval != None:
            self.interval.cancel()
            self.interval = None
    
    #####
    # THREAD SAFE GETTER WITH CONDITION
    #####
    
    def getCheckHistoryForThePast(self, seconds):
        t = time.time()
        with self.historyLock:
            # check[1] = timestamp of the check
            return self.checksHistory.getValuesUntilCondition(lambda check: t-check[1] > seconds)