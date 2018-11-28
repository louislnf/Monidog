import requests
import threading
import time

from interval import Interval

class WebsiteMonitor:
    def __init__(self, url, checkInterval):
        self.url = url
        self.checkInterval = checkInterval
        self.maxNumberOfChecksSaved = int(round(3600.0/checkInterval))
        self.checksHistory = History(self.maxNumberOfChecksSaved)
        self.lock = threading.RLock()
        self.interval = None

    def check(self):
        success = True
        startTime = time.time()
        try:
            r = requests.head(self.url)
        except requests.exceptions.RequestException:
            success = False
        responseTime = time.time()-startTime
        if success:
            with self.lock:
                self.checksHistory.add(WebsiteCheck(startTime, r.status_code, responseTime, success))
        else:
            with self.lock:
                self.checksHistory.add(WebsiteCheck(startTime, 0, 0.0, success))


    def startMonitoring(self):
        self.startedMonitoringTime = time.time()
        self.interval = Interval(self.checkInterval, self.check)
    
    def stopMonitoring(self):
        print("Stopped monitoring ", self.url)
        self.interval.cancel()
    
    def getChecksHistory(self):
        with self.lock:
            return self.checksHistory.getValues()
    
    def getChecksHistoryForTheLast10Minutes(self):
        currentTime = time.time()
        with self.lock:
            return self.checksHistory.getValuesWithCondition(lambda check: currentTime-check.checktime < 10*60)

class WebsiteCheck:
    def __init__(self, checktime, statusCode, responseTime, success):
        self.checktime = checktime
        self.statusCode = statusCode
        self.responseTime = responseTime
        self.success = success

    def __str__(self):
        return "WebsiteCheck(chekctime: "+str(self.checktime)+", statusCode: "+str(self.statusCode)+", responseTime: "+str(self.responseTime)+")"
    
    def __gt__(self, other):
        return self.checktime > other.checktime

class History:
    def __init__(self, capacity):
        self.capacity = capacity
        self.indexOfLastPushedValue = -1
        self.values = []
    
    def __str__(self):
        return "Queue(capacity: "+str(self.capacity)+", "+str(self.values)+")"
    
    def add(self, value):
        if len(self.values) < self.capacity:
            self.values.append(value)
            self.indexOfLastPushedValue = (self.indexOfLastPushedValue+1)%self.capacity
        else:
            tmp = (self.indexOfLastPushedValue+1)%self.capacity
            self.values[tmp] = value
            self.indexOfLastPushedValue = tmp
    
    def getValues(self):
        return self.values.copy()
    
    def getValuesWithCondition(self, condition):
        selectedValues = []
        for v in self.values:
            if condition(v):
                selectedValues.append(v)
        return selectedValues
    
    def getLastPushedValue(self):
        if len(self.values) > 0:
            return self.values[self.indexOfLastPushedValue]
        else:
            return None
