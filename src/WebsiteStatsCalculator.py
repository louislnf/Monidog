
import threading, math, time

class WebsiteStatsCalculator:

    def __init__(self, websiteMonitor):
        self.websiteMonitor = websiteMonitor
        self.statsLock = threading.Lock()
        # stats are represented by tuples
        # (timestamp, avgAvailability, avgResponseTime, minResponseTime, maxResponseTime, statusCodeDict, numberOfChecks)
        self.statsLast2min = (-1.0, -1.0, -1.0, -1.0, -1.0, {}, 0)
        self.statsLastHour = (-1.0, -1.0, -1.0, -1.0, -1.0, {}, 0)
        # we need locks for both stats as we may access and modify them from different threads
        self.statsLast2minLock = threading.Lock()
        self.statsLastHourLock = threading.Lock()

    ######
    # THREAD SAFE GETTERS/SETTERS
    ######
    def getStatsForTheLast2min(self):
        with self.statsLast2minLock:
            return self.statsLast2min

    def setStatsForTheLast2min(self, stats):
        with self.statsLast2minLock:
            self.statsLast2min = stats

    def getStatsForTheLastHour(self):
        with self.statsLastHourLock:
            return self.statsLastHour

    def setStatsForTheLastHour(self, stats):
        with self.statsLastHourLock:
            self.statsLastHour = stats

    ######
    # CALCULATION METHODS
    ######

    def calculateStatsForTheLast2min(self):
        # 2 min = 120 seconds
        stats = self.calculateStatsForTheLast(120)
        #updating the attribute
        self.setStatsForTheLast2min(stats)
        
    
    def calculateStatsForTheLastHour(self):
        # 1 hour = 3600 seconds
        stats = self.calculateStatsForTheLast(3600)
        #updating the attribute 
        self.setStatsForTheLastHour(stats)

    def calculateStatsForTheLast(self, seconds):
        checks = self.websiteMonitor.getCheckHistoryForThePast(seconds)
        calculationTimestamp = time.time()
        statusCodeDict = {}
        avgAvailability = 0.0
        avgResponseTime = 0.0
        minResponseTime = math.inf
        maxResponseTime = 0.0
        numberOfChecks = 0
        numberOfChecksWhereAvailable = 0
        for check in checks:
            (statusCode, checkTime, responseTime) = check
            numberOfChecks += 1
            #updating the statusCodeDict
            if not(statusCode in statusCodeDict):
                statusCodeDict[statusCode] = 1
            else:
                statusCodeDict[statusCode] += 1
            # checking the availability of the site on that "check"
            # - statusCode = -1 -> the request raised an exception
            # - statusCode = 500 -> server internal error
            if not(statusCode == -1 or statusCode == 500):
                numberOfChecksWhereAvailable += 1
                avgResponseTime += responseTime
                # updating the minRequestTime
                if responseTime < minResponseTime:
                    minResponseTime =  responseTime
                if responseTime > maxResponseTime:
                    maxResponseTime = responseTime
        
        # if we were able to calculate stats on at least one "check"
        if numberOfChecks != 0:
            # we calculate the average availability
            avgAvailability = numberOfChecksWhereAvailable / numberOfChecks
            avgAvailability = round(100*avgAvailability) #converting to percent
        else:
            avgAvailability = -1.0
        
        # if we were able to calculate response times stats
        if numberOfChecksWhereAvailable != 0:
            avgResponseTime = avgResponseTime / numberOfChecksWhereAvailable
            avgResponseTime = round(1000*avgResponseTime) #converting to ms
            minResponseTime = round(1000*minResponseTime) #converting to ms
            maxResponseTime = round(1000*maxResponseTime) #converting to ms
        else:
            # we set the stats to -1
            avgResponseTime = -1.0
            minResponseTime = -1.0
            maxResponseTime = -1.0        
        
        # return a tuple representing the stats
        return (
                calculationTimestamp,
                avgAvailability,
                avgResponseTime,
                minResponseTime,
                maxResponseTime,
                statusCodeDict,
                numberOfChecks
            )


                
                    
                




