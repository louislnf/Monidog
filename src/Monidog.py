
from WebsiteMonitor import WebsiteMonitor
from WebsiteStatsCalculator import WebsiteStatsCalculator
from Interval import Interval
from ScreenDrawer import ScreenDrawer

import curses, threading, time

class Monidog:

    def __init__(self):
        # monitoring related attributes
        self.websiteMonitors = {}
        self.websiteStatsCalculators = {}
        self.websiteStatsRefresh2MinIntervals = {}
        self.websiteStatsRefresh1HourIntervals = {}
        self.downDetector = {}
        self.alertHistory = []
        self.checkingForAlertsInterval = None
        # adding lock to prevent modifying the websites list as the ui is drawing stats
        self.modifyWebsitesList = threading.Lock()
        # adding lock for alert history
        self.alertHistoryLock = threading.Lock()

        # gui related attributes
        self.guiRefreshingInterval = None
        self.screenDrawer = None
        # the screen drawer is used from different thread to update the gui, so it needs a lock
        self.guiLock = threading.Lock()
        # boolean to know if we are in the last 2min stats view or the last hour stats view
        self.last2Min = True
        self.last2MinLock = threading.Lock()
        # url selection attributes
        self.urls = []
        self.selectedUrlIndex = None
        self.selectedUrlIndexLock = threading.Lock()
        # scroll mechanism for stats view
        self.firstUrlDisplayedIndex = 0
        self.firstUrlDisplayedIndexLock = threading.Lock()
        # scroll mechanism for alerts view
        self.lastAlertDisplayedIndex = None
        self.lastAlertDisplayedIndexLock = threading.Lock()
        
        # inputs related attributes
        # editing mode
        self.inputsEditingMode = False
        # url
        self.urlBeingWritten = ""
        # check interval
        self.currentInterval = 10.0
        # a lock for these inputs info
        self.inputsInfoLock = threading.Lock()
    
    # thread safe getters and setters for inputs info
    def getInputsInfo(self):
        with self.inputsInfoLock:
            return (self.inputsEditingMode, self.urlBeingWritten, self.currentInterval)
    
    def setInputsInfo(self, newInputsInfo):
        with self.inputsInfoLock:
            self.inputsEditingMode, self.urlBeingWritten, self.currentInterval = newInputsInfo
    
    # thread safe getters and setters for selectedUrlIndex
    def getSelectedUrlIndex(self):
        with self.selectedUrlIndexLock:
            return self.selectedUrlIndex
    
    def setSelectedUrlIndex(self, newIndex):
        with self.selectedUrlIndexLock:
            self.selectedUrlIndex = newIndex
    
    # thread safe getter and setter for firstUrlDisplayedIndex
    def getFirstUrlDisplayedIndex(self):
        with self.firstUrlDisplayedIndexLock:
            return self.firstUrlDisplayedIndex
    
    def setFirstUrlDisplayedIndex(self, newIndex):
        with self.firstUrlDisplayedIndexLock:
            self.firstUrlDisplayedIndex = newIndex

    # thread safe getter and setter for lastAlertDisplayedIndex
    def getLastAlertDisplayedIndex(self):
        with self.lastAlertDisplayedIndexLock:
            return self.lastAlertDisplayedIndex
    def setLastAlertDisplayedIndex(self, newIndex):
        with self.lastAlertDisplayedIndexLock:
            self.lastAlertDisplayedIndex = newIndex
    
    def addWebsiteToMonitor(self, url, checkInterval):
        with self.modifyWebsitesList:
            if not(url in self.urls):
                self.websiteMonitors[url] = WebsiteMonitor(url, checkInterval)
                self.websiteStatsCalculators[url] = WebsiteStatsCalculator(self.websiteMonitors[url])
                self.downDetector[url] = False
                self.urls.append(url)
                if self.getSelectedUrlIndex() == None:
                    self.setSelectedUrlIndex(0)
                #launching the parallel tasks
                # - website monitoring
                self.websiteMonitors[url].startMonitoring()
                # - stats refreshing
                self.websiteStatsRefresh1HourIntervals[url] = Interval(60.0, self.websiteStatsCalculators[url].calculateStatsForTheLastHour)
                self.websiteStatsRefresh2MinIntervals[url] = Interval(10.0, self.websiteStatsCalculators[url].calculateStatsForTheLast2min)

    def removeWebsiteMonitor(self, index, removeFromUrlList):
        with self.modifyWebsitesList:
            if index in range(len(self.urls)):
                url = self.urls[index]
                if removeFromUrlList:
                    self.urls.pop(index)
                # stopping the monitoring task for this website
                self.websiteMonitors[url].stopMonitoring()
                # stopping the stats refreshing intervals for this website
                self.websiteStatsRefresh1HourIntervals[url].cancel()
                self.websiteStatsRefresh2MinIntervals[url].cancel()
                #removing the website from the different dictionnaries
                self.websiteStatsRefresh1HourIntervals.pop(url)
                self.websiteStatsRefresh2MinIntervals.pop(url)
                self.websiteMonitors.pop(url)
                self.downDetector.pop(url)
    
    def removeAllWebsiteMonitors(self):
        with self.modifyWebsitesList:
            nbUrls = len(self.urls)
        for i in range(nbUrls):
            self.removeWebsiteMonitor(i, False)
    
    def checkForAlerts(self):
        with self.modifyWebsitesList:
            for url in self.websiteMonitors:
                stats = self.websiteStatsCalculators[url].getStatsForTheLast2min()
                avgAvailability = stats[1]
                if avgAvailability >= 0 and avgAvailability <= 80 and not(self.downDetector[url]):
                    #server just got down
                    self.downDetector[url] = True
                    with self.alertHistoryLock:
                        self.alertHistory.append((time.time(), True, url))
                        last = self.getLastAlertDisplayedIndex()
                        self.setLastAlertDisplayedIndex(0 if last == None else last+1)
                elif avgAvailability > 80 and self.downDetector[url]:
                    #server is back up
                    self.downDetector[url] = False
                    with self.alertHistoryLock:
                        self.alertHistory.append((time.time(), False, url))
                        last = self.getLastAlertDisplayedIndex()
                        self.setLastAlertDisplayedIndex(0 if last == None else last+1)
    
    def startCheckingForAlerts(self):
        if self.checkingForAlertsInterval == None:
            self.checkingForAlertsInterval = Interval(5.0, self.checkForAlerts)
    
    def stopCheckingForAlerts(self):
        if self.checkingForAlertsInterval != None:
            self.checkingForAlertsInterval.cancel()
            self.checkingForAlertsInterval = None

    def startGuiRefresh(self):
        if self.guiRefreshingInterval == None:
            self.guiRefreshingInterval = Interval(2.0, self.draw)

    def stopGuiRefresh(self):
        if self.guiRefreshingInterval != None:
            self.guiRefreshingInterval.cancel()
            self.guiRefreshingInterval = None

    def draw(self):
        with self.guiLock:
            # getting MAX_Y & MAX_X for screen
            MAX_Y, MAX_X = self.screenDrawer.getMaxYX()
            MAX_Y, MAX_X = MAX_Y-1, MAX_X-2
            # clearing screen
            self.screenDrawer.clear()
            # drawing the main box
            self.screenDrawer.drawBox(0 , 0, MAX_Y, MAX_X, "Monidog")
            # drawing the inputs
            self.__drawInputs(1, 1, 3, MAX_X-1)

            # drawing the stats box
            with self.last2MinLock:
                last2Min = self.last2Min
            title = "Stats (last 2 min)" if last2Min else "Stats (last hour)"
            self.screenDrawer.drawBox(4, 1, MAX_Y-13, MAX_X-1, title)
            # drawing the stats table headers line
            self.__drawWebsiteStatsHeader(5, 2, MAX_Y-5, MAX_X-2)
            # drawing the stats for each websites
            numberOfStatsLinesDisplayable = MAX_Y-13-6
            statsLineDisplayed = 0
            with self.modifyWebsitesList:
                first = self.getFirstUrlDisplayedIndex()
                last = first+numberOfStatsLinesDisplayable
                selectedUrlIndex = self.getSelectedUrlIndex()
                if selectedUrlIndex != None and selectedUrlIndex < first:
                    first, last = selectedUrlIndex, selectedUrlIndex+numberOfStatsLinesDisplayable
                elif selectedUrlIndex != None and selectedUrlIndex >= last:
                    first, last = selectedUrlIndex+1-numberOfStatsLinesDisplayable, selectedUrlIndex+1
                self.setFirstUrlDisplayedIndex(max(first, 0))
                for i in range(max(first, 0),min(last, len(self.urls))):
                    url = self.urls[i]
                    stats = self.websiteStatsCalculators[url].getStatsForTheLast2min() if last2Min else self.websiteStatsCalculators[url].getStatsForTheLastHour()
                    line = 6+statsLineDisplayed
                    self.__drawWebsiteStats(line, 2, line, MAX_X-2, url, stats, i == selectedUrlIndex)
                    statsLineDisplayed += 1
            
            # drawing the alerts
            self.__drawAlerts(MAX_Y-12, 1, MAX_Y-6, MAX_X-1)

            #draw the help at the bottom
            self.__drawHelp(MAX_Y-5, 1, MAX_Y-1, MAX_X-1)

            #refreshing the screen
            self.screenDrawer.refresh()
    
    def __drawInputs(self, y1, x1, y2, x2):
        # getting the inputs info thread safely
        inputsEditingMode, urlBeingWritten, currentInterval = self.getInputsInfo()
        #drawing url input
        xEndUrlInput = x2-13
        self.screenDrawer.drawBox(y1, x1, y2, xEndUrlInput, "Add website")
        self.screenDrawer.drawText(y1+1, x1+2, "URL :", curses.A_UNDERLINE)
        xBeginUrl = x1+8
        # checking if the url fits in the box, if it doesnt we only show the end of it
        maxDisplayedUrlSize = xEndUrlInput-xBeginUrl-2
        urlToDisplay = urlBeingWritten
        if len(urlBeingWritten) > maxDisplayedUrlSize:
            urlToDisplay = "...{0}".format(urlBeingWritten[-maxDisplayedUrlSize+3:])
        self.screenDrawer.drawText(y1+1, x1+8, urlToDisplay)
        if inputsEditingMode:
            # adding a blinking char at the end of the url
            self.screenDrawer.draw(y1+1, xBeginUrl+len(urlToDisplay), "_", curses.A_BLINK)
        self.screenDrawer.drawBox(y1, xEndUrlInput+1, y2, x2, "Interval")
        self.screenDrawer.drawText(y1+1, x2-6, "{0:4.0f}s".format(currentInterval))

    def __drawWebsiteStatsHeader(self, y1, x1, y2, x2): 
        self.screenDrawer.drawText(y1, x1+1, "URL", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+41, "AVAILABILITY", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+55, "AVG TIME", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+65, "MIN TIME", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+75, "MAX TIME", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+86, "200", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+92, "301", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+98, "404", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+104, "500", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+110, "other", curses.A_BOLD)
        self.screenDrawer.drawText(y1, x1+116, "total", curses.A_BOLD)

    def __drawWebsiteStats(self, y1, x1, y2, x2, url, stats, selected):
        (timestamp, avgAvailability, avgResponseTime, minResponseTime, maxResponseTime, statusCodeDict, numberOfChecks) = stats
        flag = curses.color_pair(2) if selected else 0
        if selected:
            for x in range(x1, x2+1):
                self.screenDrawer.draw(y1, x, " ", flag)
        #url
        self.screenDrawer.drawText(y1, x1+1, url, flag, 30)
        #availability
        self.screenDrawer.drawText(y1, x1+41, "{0}%".format(self.__optionalStatToString(avgAvailability)), flag, 12)
        #avg time
        self.screenDrawer.drawText(y1, x1+55, "{0} ms".format(self.__optionalStatToString(avgResponseTime)), flag, 8)
        #min time
        self.screenDrawer.drawText(y1, x1+65, "{0} ms".format(self.__optionalStatToString(minResponseTime)), flag, 8)
        #max time
        self.screenDrawer.drawText(y1, x1+75, "{0} ms".format(self.__optionalStatToString(maxResponseTime)), flag, 8)
        # code 200
        nbCode200 = 0 if not(200 in statusCodeDict) else statusCodeDict[200]
        self.screenDrawer.drawText(y1, x1+86, "{0}".format(nbCode200), flag, 4)
        # code 301
        nbCode301 = 0 if not(301 in statusCodeDict) else statusCodeDict[301]
        self.screenDrawer.drawText(y1, x1+92, "{0}".format(nbCode301), flag, 4)
        # code 404
        nbCode404 = 0 if not(404 in statusCodeDict) else statusCodeDict[404]
        self.screenDrawer.drawText(y1, x1+98, "{0}".format(nbCode404), flag, 4)
        # code 500
        nbCode500 = 0 if not(500 in statusCodeDict) else statusCodeDict[500]
        self.screenDrawer.drawText(y1, x1+104, "{0}".format(nbCode500), flag, 4)
        # code others
        nbCodeTotal = sum(statusCodeDict[code] for code in statusCodeDict)
        nbCodeOthers = nbCodeTotal-nbCode200-nbCode301-nbCode404-nbCode500
        self.screenDrawer.drawText(y1, x1+110, "{0}".format(nbCodeOthers), flag, 4)
        self.screenDrawer.drawText(y1, x1+116, "{0}".format(nbCodeTotal), flag, 4)

    def __optionalStatToString(self, s):
        if s < 0:
            return "--"
        else:
            return "{0}".format(round(s))
    
    def __drawAlerts(self, y1, x1, y2, x2):
        #drawing the alert box
        self.screenDrawer.drawBox(y1, x1, y2, x2, "Alerts")
        with self.alertHistoryLock:
            last = self.getLastAlertDisplayedIndex()
            if last != None:
                first = max(0, last-4)
                for i in range(last-first+1):
                    (timestamp, wentDown, url) = self.alertHistory[last-i]
                    niceDate = time.strftime("%D %H:%M", time.localtime(timestamp))
                    if wentDown:
                        text = "#{2}: {0} : {1} went down.".format(niceDate, url, last-i)
                        flag = curses.color_pair(3)
                    else:
                        text = "#{2}: {0} : {1} went back up.".format(niceDate, url, last-i)
                        flag = curses.color_pair(4)
                    self.screenDrawer.drawText(y2-1-i, x1+1, text, flag, x2-x1-2)

    def __drawHelp(self, y1, x1, y2, x2):
        # drawing the surrounding box
        self.screenDrawer.drawBox(y1, x1, y2, x2, "Help")
        # getting the inputs info
        (editingMode, urlBeingWritten, currentInterval) = self.getInputsInfo()
        if editingMode:
            self.screenDrawer.drawText(y1+1, x1+2, "Type the url the website you want to monitor", 0, x2-x1-3)
            self.screenDrawer.drawText(y1+2, x1+2, "Use UP/DOWN keys to change the interval time", 0, x2-x1-3)
            self.screenDrawer.drawText(y1+3, x1+2, "Press Esc to stop editing.", 0, x2-x1-3)
        else:
            self.screenDrawer.drawText(y1+1, x1+2, "a : add a website | x : remove selected website", 0, x2-x1-3)
            self.screenDrawer.drawText(y1+2, x1+2, "UP/DOWN : move selection | j/k : scroll alerts", 0, x2-x1-3)
            self.screenDrawer.drawText(y1+3, x1+2, "q : quit", 0, x2-x1-3)
        self.screenDrawer.drawText(y1+1, x2-20, "F1 : last 2 min")
        self.screenDrawer.drawText(y1+2, x2-20, "F2 : last hour")
        self.screenDrawer.drawText(y1+3, x2-20, "F3 : load urls.txt")
    
    def loadUrlFile(self):
        # attempt to open urls file
        try:
            urlsFile = open("urls.txt", "r")
        except FileNotFoundError:
            urlsFile = None
        # if attempt failed -> return
        if urlsFile == None:
            return
        # parsing the file
        urls = []
        url = urlsFile.readline().replace('\n', '').strip()
        while len(url) > 0:
            urls.append(url)
            url = urlsFile.readline().replace('\n', '').strip()
        # closing file
        urlsFile.close()
        # adding the urls to monitor
        for url in urls:
            self.addWebsiteToMonitor(url, 10.0)  

    def main(self, stdscr):
        #####
        # this is the function called by the curses.wrapper()
        #####

        ##################
        # INITIALIZATION #
        ##################

        # initialize the screen drawer
        self.screenDrawer = ScreenDrawer(stdscr)

        # doing additionnal settings for curses
        curses.curs_set(0) # hiding the cursor
        stdscr.keypad(1) # setting the keypad option
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_WHITE) #selected color pair
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK) # red text for alerts
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK) # green text for alerts

        #starting the alerts detector
        self.startCheckingForAlerts()

        #starting the automatic gui refresh
        self.startGuiRefresh()

        ############
        # MAINLOOP #
        ############

        running = True
        while running:
            # draw the screen
            self.draw()

            # getting the user input
            key = stdscr.getch()
            # getting the screen size to see if it has changed
            scrX, scrY = self.screenDrawer.getMaxYX()

            # checking if term has been resized
            if curses.is_term_resized(scrY, scrX):
                # if the term was resized we update the screen drawer
                self.screenDrawer.updateMaxYX()

            # getting the inputsInfo that may be useful
            editingMode, urlBeingWritten, currentInterval = self.getInputsInfo()

            # processing the user input
            if key == 113 and not(editingMode):
                # key is 'q' -> quit
                running = False
            elif key == curses.KEY_F1:
                #key is F1 -> stats for the last 2 minutes view
                with self.last2MinLock:
                    self.last2Min = True
            elif key == curses.KEY_F2:
                #key is F2 -> stats for the last hour
                with self.last2MinLock:
                    self.last2Min = False
            elif key == curses.KEY_F3:
                #key is F3 -> load url file
                self.loadUrlFile()
            elif key == 27 and editingMode:
                # key is Esc -> stop editing
                self.setInputsInfo(( False, urlBeingWritten, currentInterval ))
            elif key == 97 and not(editingMode):
                # key is a -> start editing
                self.setInputsInfo(( True, urlBeingWritten, currentInterval ))
            elif key == curses.KEY_F1:
                # switch to editing mode
                self.setInputsInfo(( True, urlBeingWritten, currentInterval ))
            elif 32 <= key and key <= 126 and editingMode:
                # key is writable ascii char -> we append it to the url being written
                self.setInputsInfo((editingMode, "{0}{1}".format(urlBeingWritten, chr(key)), currentInterval ))
            elif (key == 127 or key == curses.KEY_BACKSPACE) and editingMode:
                # key is backspace -> we remove the last char of the url beign written
                self.setInputsInfo(( editingMode, urlBeingWritten[:-1], currentInterval ))
            elif key == 10 and editingMode:
                # key is return 
                self.addWebsiteToMonitor(urlBeingWritten, currentInterval)
                # clearing the url input and switching back to not editing mode
                self.setInputsInfo(( False, "", currentInterval ))
            elif key == curses.KEY_UP and editingMode and currentInterval < 100:
                # increasing the check interval time
                self.setInputsInfo((editingMode, urlBeingWritten, currentInterval+1.0))
            elif key == curses.KEY_DOWN and editingMode and currentInterval > 5:
                # decreasing the check interval time
                self.setInputsInfo((editingMode, urlBeingWritten, currentInterval-1.0))
            elif key == 120 and not(editingMode):
                # key is 'x' -> delete currently selected url
                selectedUrlIndex = self.getSelectedUrlIndex()
                if selectedUrlIndex != None:
                    with self.modifyWebsitesList:
                        if len(self.urls)-1 == 0:
                            self.setSelectedUrlIndex(None)
                        elif selectedUrlIndex == len(self.urls)-1:
                            self.setSelectedUrlIndex(selectedUrlIndex-1)
                    self.removeWebsiteMonitor(selectedUrlIndex, True)
            elif key == curses.KEY_UP and not(editingMode):
                #moving selection cursor up if possible
                with self.modifyWebsitesList:
                    selectedUrlIndex = self.getSelectedUrlIndex()
                    if selectedUrlIndex != None and selectedUrlIndex > 0:
                        self.setSelectedUrlIndex(selectedUrlIndex-1)
            elif key == curses.KEY_DOWN and not(editingMode):
                #moving selection cursor down if possible
                with self.modifyWebsitesList:
                    selectedUrlIndex = self.getSelectedUrlIndex()
                    if selectedUrlIndex != None and selectedUrlIndex < len(self.urls)-1:
                        self.setSelectedUrlIndex(selectedUrlIndex+1)
            elif key == 106 and not(editingMode):
                #key is 'j' -> moving scroll alert up if possible
                with self.alertHistoryLock:
                    lastAlertDisplayedIndex = self.getLastAlertDisplayedIndex()
                    if lastAlertDisplayedIndex > 4:
                        self.setLastAlertDisplayedIndex(lastAlertDisplayedIndex-1)
            elif key == 107 and not(editingMode):
                #key is 'k' -> moving scroll alert down if possible
                with self.alertHistoryLock:
                    lastAlertDisplayedIndex = self.getLastAlertDisplayedIndex()
                    if lastAlertDisplayedIndex < len(self.alertHistory)-1:
                        self.setLastAlertDisplayedIndex(lastAlertDisplayedIndex+1)
                    

        #####################
        # DESINITIALIZATION #
        #####################
        self.screenDrawer.clear()
        self.stopCheckingForAlerts()
        self.removeAllWebsiteMonitors()
        self.stopGuiRefresh()
        


if __name__ == '__main__':
    monidog = Monidog()
    curses.wrapper(monidog.main)
    print("Please wait at most 5 seconds for the last pending requests to timeout...")