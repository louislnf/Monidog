
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
        self.modifyWebsitesList = threading.RLock()
        # adding lock for alert history
        self.alertHistoryLock = threading.RLock()

        # gui related attributes
        self.guiRefreshingInterval = None
        self.screenDrawer = None
        # the screen drawer is used from different thread to update the gui, so it needs a lock
        self.guiLock = threading.RLock()

        # inputs related attributes
        # editing mode
        self.inputsEditingMode = False
        # url
        self.urlBeingWritten = ""
        # check interval
        self.currentInterval = 10.0
        # a lock for these inputs info
        self.inputsInfoLock = threading.RLock()
    
    # thread safe getters and setters for inputs info
    def getInputsInfo(self):
        with self.inputsInfoLock:
            return (self.inputsEditingMode, self.urlBeingWritten, self.currentInterval)
    
    def setInputsInfo(self, newInputsInfo):
        with self.inputsInfoLock:
            self.inputsEditingMode, self.urlBeingWritten, self.currentInterval = newInputsInfo
    
    def addWebsiteToMonitor(self, url, checkInterval):
        if not(url in self.websiteMonitors):
            with self.modifyWebsitesList:
                self.websiteMonitors[url] = WebsiteMonitor(url, checkInterval)
                self.websiteStatsCalculators[url] = WebsiteStatsCalculator(self.websiteMonitors[url])
                self.downDetector[url] = False
                #launching the parallel tasks
                # - website monitoring
                self.websiteMonitors[url].startMonitoring()
                # - stats refreshing
                self.websiteStatsRefresh1HourIntervals[url] = Interval(2.0, self.websiteStatsCalculators[url].calculateStatsForTheLast2min)
                self.websiteStatsRefresh2MinIntervals[url] = Interval(10.0, self.websiteStatsCalculators[url].calculateStatsForTheLastHour)

    def removeWebsiteMonitor(self, url):
        if url in self.websiteMonitors:
            with self.modifyWebsitesList:
                # stopping the monitoring task for this website
                self.websiteMonitors[url].stopMonitoring()
                # stopping the stats refreshing intervals for this website
                self.websiteStatsRefresh1HourIntervals[url].cancel()
                self.websiteStatsRefresh2MinIntervals[url].cancel()
                #removing the website from the different dictionnaries
                self.websiteStatsRefresh1HourIntervals.pop(url)
                self.websiteStatsRefresh2MinIntervals.pop(url)
                self.websiteMonitors.pop(url)
    
    def removeAllWebsiteMonitors(self):
        with self.modifyWebsitesList:
            keys = list(self.websiteMonitors.keys())
            for url in keys:
                self.removeWebsiteMonitor(url)
    
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
                elif avgAvailability > 80 and self.downDetector[url]:
                    #server is back up
                    self.downDetector[url] = False
                    with self.alertHistoryLock:
                        self.alertHistory.append((time.time(), False, url))
    
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
            self.screenDrawer.drawBox(0 , 0, MAX_Y+1, MAX_X, "Monidog")
            # drawing the inputs
            self.__drawInputs(1, 1, 3, MAX_X-1)

            # drawing the stats box
            self.screenDrawer.drawBox(4, 1, MAX_Y-11, MAX_X-1, "Stats")
            # drawing the stats table headers line
            self.__drawWebsiteStatsHeader(5, 2, MAX_Y-5, MAX_X-2)
            # drawing the stats for each websites
            numberOfStatsLinesDisplayable = MAX_Y-11-6
            statsLineDisplayed = 0
            with self.modifyWebsitesList:
                for url in self.websiteStatsCalculators:
                    if statsLineDisplayed == numberOfStatsLinesDisplayable:
                        break
                    stats = self.websiteStatsCalculators[url].getStatsForTheLast2min()
                    line = 6+statsLineDisplayed
                    self.__drawWebsiteStats(line, 2, line, MAX_X-2, url, stats, False)
                    statsLineDisplayed += 1
            
            # drawing the alerts
            self.__drawAlerts(MAX_Y-10, 1, MAX_Y-4, MAX_X-1)

            #draw the help at the bottom
            self.__drawHelp(MAX_Y-3, 1, MAX_Y+1, MAX_X-1)

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
        self.screenDrawer.drawText(y1, x1+1, "URL", curses.A_BOLD, 30)
        self.screenDrawer.drawText(y1, x2-55, "AVAILABILITY", curses.A_BOLD, 12)
        self.screenDrawer.drawText(y1, x2-40, "AVG TIME", curses.A_BOLD, 10)
        self.screenDrawer.drawText(y1, x2-30, "MIN TIME", curses.A_BOLD, 10)
        self.screenDrawer.drawText(y1, x2-20, "MAX TIME", curses.A_BOLD, 10)
        self.screenDrawer.drawText(y1, x2-10, "NB CHECKS", curses.A_BOLD, 10)

    def __drawWebsiteStats(self, y1, x1, y2, x2, url, stats, selected):
        (timestamp, avgAvailability, avgResponseTime, minResponseTime, maxResponseTime, statusCodeDict, numberOfChecks) = stats
        flag = curses.color_pair(2) if selected else 0
        #url
        self.screenDrawer.drawText(y1, x1+1, url, flag, 30)
        #availability
        self.screenDrawer.drawText(y1, x2-55, "{0}%".format(self.__optionalStatToString(avgAvailability)), flag, 12)
        #avg time
        self.screenDrawer.drawText(y1, x2-40, "{0} ms".format(self.__optionalStatToString(avgResponseTime)), flag, 10)
        #min time
        self.screenDrawer.drawText(y1, x2-30, "{0} ms".format(self.__optionalStatToString(minResponseTime)), flag, 10)
        #max time
        self.screenDrawer.drawText(y1, x2-20, "{0} ms".format(self.__optionalStatToString(maxResponseTime)), flag, 10)
        #n checks
        self.screenDrawer.drawText(y1, x2-10, "{0}".format(numberOfChecks), flag, 10)

    def __optionalStatToString(self, s):
        if s < 0:
            return "--"
        else:
            return "{0}".format(round(s))
    
    def __drawAlerts(self, y1, x1, y2, x2):
        #drawing the alert box
        self.screenDrawer.drawBox(y1, x1, y2, x2, "Alerts")
        with self.alertHistoryLock:
            for i in range(min(5, len(self.alertHistory))):
                (timestamp, wentDown, url) = alert = self.alertHistory[-1-i]
                niceDate = time.strftime("%D %H:%M", time.localtime(timestamp))
                if wentDown:
                    text = "{0} : {1} went down.".format(niceDate, url)
                    flag = curses.color_pair(3)
                else:
                    text = "{0} : {1} went back up.".format(niceDate, url)
                    flag = curses.color_pair(4)
                self.screenDrawer.drawText(y2-1-i, x1+1, text, flag, x2-x1-2)

    def __drawHelp(self, y1, x1, y2, x2):
        # drawing the surrounding box
        self.screenDrawer.drawBox(y1, x1, y2, x2, "Help")
        # getting the inputs info
        (editingMode, urlBeingWritten, currentInterval) = self.getInputsInfo()
        if editingMode:
            self.screenDrawer.drawText(y1+1, x1+2, "Type the name the website you want to monitor", 0, x2-x1-3)
            self.screenDrawer.drawText(y1+2, x1+2, "Use UP/DOWN keys to change the interval time", 0, x2-x1-3)
            self.screenDrawer.drawText(y1+3, x1+2, "Press Esc to go stop editing.", 0, x2-x1-3)
        else:
            self.screenDrawer.drawText(y1+1, x1+2, "a : add a website.", 0, x2-x1-3)
            self.screenDrawer.drawText(y1+2, x1+2, "x : remove selected website.", 0, x2-x1-3)
            self.screenDrawer.drawText(y1+3, x1+2, "q : quit.", 0, x2-x1-3)
    
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
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK) #selected color pair
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
                self.setInputsInfo((
                    editingMode, "{0}{1}".format(urlBeingWritten, chr(key)), currentInterval ))
            elif key == 127 and editingMode:
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