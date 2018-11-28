from screen import *
from monitor import *
from stats import *
from interval import *
import curses

class App:
    
    def __init__(self):
        self.websiteMonitors = []
        self.websiteStats = []
        self.writingUrl = False
        self.urlBeingWritten = ""
        self.terminalTooSmall = False
    
    def addWebsiteMonitor(self, url, checkInterval=10.0):
        websiteMonitor = WebsiteMonitor(url, checkInterval)
        websiteMonitor.startMonitoring()
        websiteStat = WebsiteStats(websiteMonitor)
        self.websiteMonitors.append(websiteMonitor)
        self.websiteStats.append(websiteStat)
    
    def setScreen(self, screen):
        self.monitorScreen = screen

    def computeStats(self):
        for s in self.websiteStats:
            s.computeStats()
    
    def drawStats(self):
        for i in range(len(self.websiteStats)):
            self.monitorScreen.drawWebsiteStats(i, self.websiteStats[i], False)
        self.monitorScreen.refresh()
    
    def startStatsRefreshing(self):
        self.statsInterval = Interval(5.0, self.computeStats)
    
    def stopStatsRefreshing(self):
        self.statsInterval.cancel()


    def startGUIRefreshing(self):
        self.guiInterval = Interval(2.0, self.drawStats)

    def stopGUIRefreshing(self):
        self.guiInterval.cancel()
    
    def drawBase(self):
        self.monitorScreen.drawStaticStuff()
        self.monitorScreen.drawUrlInput(self.urlBeingWritten)
    
    def mainloop(self, screen):
        curses.curs_set(0)
        self.monitorScreen = MonitorScreen(screen)

        if self.monitorScreen.hasMinDimension():

            self.monitorScreen.screen.keypad(1)

            self.addWebsiteMonitor("https://www.google.com")
            self.addWebsiteMonitor("http://aertom.fr:1995")
            self.addWebsiteMonitor("http://datadoghq.com")

            self.drawBase()
            self.drawStats()
            self.monitorScreen.refresh()

            self.startStatsRefreshing()
            self.startGUIRefreshing()

            running = True
            
            while running:
                # checking if there is a need to resize
                if self.monitorScreen.shouldRedraw():
                    self.monitorScreen.updateMaxYX()
                    if self.monitorScreen.hasMinDimension():
                        self.monitorScreen.clear()
                        self.drawBase()
                        self.drawStats()
                    else:
                        self.terminalTooSmall = True
                        running = False
                        break
                #handling user input
                key = self.monitorScreen.getkey()
                if key == curses.KEY_F4:
                    running = False
                elif key == curses.KEY_F1:
                    self.writingUrl = not(self.writingUrl)
                elif key >= 20 and key < 127:
                    if self.writingUrl:
                        self.urlBeingWritten += chr(key)
                        self.monitorScreen.drawUrlInput(self.urlBeingWritten)
                elif key == 127:
                    if self.writingUrl:
                        self.urlBeingWritten = self.urlBeingWritten[:-1]
                        self.monitorScreen.drawUrlInput(self.urlBeingWritten)
                elif key == 10:
                    if self.writingUrl:
                        self.addWebsiteMonitor(self.urlBeingWritten)
                        self.writingUrl = False
                        self.urlBeingWritten = ""
                        self.monitorScreen.drawUrlInput(self.urlBeingWritten)
                        self.drawStats()
                        


                #refreshing screen
                self.monitorScreen.refresh()
        
            # stopping the background tasks
            self.stopStatsRefreshing()
            self.stopGUIRefreshing()
            self.stopMonitoring()
        else:
            self.terminalTooSmall = True
        # terminating window
        self.monitorScreen.clear()
        self.monitorScreen.screen.keypad(0)
        curses.curs_set(1)
    
    def stopMonitoring(self):
        for wm in self.websiteMonitors:
            wm.stopMonitoring()
            
app = App()

curses.wrapper(app.mainloop)

if app.terminalTooSmall:
    print("Your terminal window is too small.")
    
        
