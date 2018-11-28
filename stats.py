
from monitor import *
import math, time, threading

class WebsiteStats:

    def __init__(self, websiteMonitor):
        self.websiteMonitor = websiteMonitor
        self.lock = threading.RLock()
        self.reset()
    
    def reset(self):
        self.timestamp = time.time()
        self.avgAvailability = 0.0
        self.avgAvailabilitiesSamples2min = [0]*30
        self.avgAvailabilities2min = [0.0]*30
        self.avgResponseTime = 0.0
        self.minResponseTime = math.inf
        self.maxResponseTime = 0.0
        self.responseCodes = {}
        self.checks = []

    def computeStats(self):
        with self.lock:
            self.reset()
            self.checks = self.websiteMonitor.getChecksHistory()
            if len(self.checks) != 0:
                nbSuccess = 0
                for c in self.checks:
                    if c.success:
                        nbSuccess += 1
                        # counting response codes
                        if c.statusCode in self.responseCodes:
                            self.responseCodes[c.statusCode] += 1
                        else:
                            self.responseCodes[c.statusCode] = 1
                        # min
                        if c.responseTime < self.minResponseTime:
                            self.minResponseTime = c.responseTime
                        # max
                        if c.responseTime > self.maxResponseTime:
                            self.maxResponseTime = c.responseTime
                        # avg
                        self.avgResponseTime += c.responseTime
                        # availability
                        self.avgAvailability += 1

                    k = math.floor(len(self.avgAvailabilities2min)*(1-(self.timestamp-c.checktime)/3600))
                    if k in range(len(self.avgAvailabilities2min)):
                        #update avergage value
                        # avg(n+1) = (n*avg(n)+newValue)/(n+1)
                        self.avgAvailabilitiesSamples2min[k] += 1
                        if c.success:
                            tmp = (self.avgAvailabilitiesSamples2min[k]-1)*self.avgAvailabilities2min[k]+1
                            self.avgAvailabilities2min[k] = tmp/self.avgAvailabilitiesSamples2min[k]
                        
                self.avgResponseTime = self.avgResponseTime/len(self.checks)
                self.avgAvailability = self.avgAvailability/len(self.checks)
    
    def getUrl(self):
        with self.lock:
            return self.websiteMonitor.url
    
    def getAvgAvailabilty(self):
        with self.lock:
            return self.avgAvailability

    def getAvgResponseTime(self):
        with self.lock:
            return self.avgResponseTime
    
    def getMinResponseTime(self):
        with self.lock:
            return self.minResponseTime
    
    def getMaxResponseTime(self):
        with self.lock:
            return self.maxResponseTime
    
    def getAvgAvailabilities2min(self):
        with self.lock:
            return self.avgAvailabilities2min.copy()
    
    def getNumberOfChecks(self):
        with self.lock:
            return len(self.checks)

    