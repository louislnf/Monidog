import curses, time

from monitor import *
from stats import *

class MonitorScreen:
    def __init__(self, screen):
        self.screen = screen
        self.y, self.x = screen.getmaxyx()
        self.init_color_pairs()
        self.MINX = 100
        self.MINY = 20

    def hasMinDimension(self):
        return self.x >= self.MINX and self.y >= self.MINY

    def setup(self):
        self.screen.keypad(1)
        curses.curs_set(0)
        self.init_color_pairs()
    
    def refresh(self):
        self.screen.refresh()

    def getch(self):
        return self.screen.getch()

    def shouldRedraw(self):
        return curses.is_term_resized(self.y, self.x)

    def updateMaxYX(self):
        self.y, self.x = self.screen.getmaxyx()

    def clear(self):
        self.screen.clear()

    def drawStaticStuff(self):
        self.drawHeader()
        self.drawHelp()
        self.drawAddWebsiteInput()
        self.drawWebsiteStatsHeader()
    
    def drawHeader(self):
        title = "WEBSITE MONITOR"
        self.drawBox(0,0,4, self.x-1, 0)
        n = len(title)
        c = self.x//2-n//2
        self.screen.addstr(2, c, title, curses.color_pair(1) | curses.A_BOLD)

    def drawAddWebsiteInput(self):
        self.drawBox(5, 0, 7, self.x-1, 0)
        self.screen.addstr(6, 2, "Add website :", curses.A_UNDERLINE)

    def drawWebsiteStatsHeader(self):
        #name - availability char -
        self.screen.addstr(8, 1, "WEBSITE URL", curses.A_BOLD)
        self.screen.addstr(8, 32, "AVAILABILTY CHART (2min)", curses.A_BOLD)
        self.screen.addstr(8, 70, "AVG TIME", curses.A_BOLD)
        self.screen.addstr(8, 80, "NB SAMPLES", curses.A_BOLD)

    def drawHelp(self):
        for c in range(self.x):
            self.screen.addstr(self.y-2, c, u'\u2500')
        commands = [
            "F1: Add Website | ",
            "F4: Quit"
        ]
        self.screen.move(self.y-1, 1)
        for com in commands:
            self.screen.addstr(com)
    
    def drawUrlInput(self, url):
        for c in range(16, self.x-3):
            self.screen.addstr(6, c, " ")
        self.screen.addstr(6, 16, url)

    def drawBox(self, l1, c1, l2, c2, flags):
        for c in range(c1+1, c2):
            self.screen.addstr(l1, c, u'\u2500', flags)
            self.screen.addstr(l2, c, u'\u2500', flags)
        for l in range(l1+1, l2):
            self.screen.addstr(l, c1, u'\u2502', flags)
            self.screen.addstr(l, c2, u'\u2502', flags)
        self.screen.addstr(l1, c1, u'\u250C', flags)
        self.screen.addstr(l1, c2, u'\u2510', flags)
        self.screen.addstr(l2, c2, u'\u2518', flags)
        self.screen.addstr(l2, c1, u'\u2514', flags)
    
    def init_color_pairs(self):
        #titles
        curses.init_pair(1, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        #OK
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        #warning
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        #KO
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
    
    def drawSparkline(self, l, c, percentValues):
        rectangles = [
            u"\u2581",
            u"\u2582",
            u"\u2583",
            u"\u2584",
            u"\u2585",
            u"\u2586",
            u"\u2587",
            u"\u2588",     
        ]
        nbRect = len(rectangles)
        for i in range(len(percentValues)):
            quantifiedValue = int(round((nbRect-1)*percentValues[i]))
            color = 2
            if percentValues[i] < 0.9 and percentValues[i]>=0.8:
                color = 3
            elif percentValues[i] < 0.8:
                color = 4

            self.screen.addstr(l, c+i, rectangles[quantifiedValue], curses.color_pair(color))

    def drawWebsiteStats(self, i, websiteStats, selected):
        STATS_START_LINE = 9
        l = STATS_START_LINE + i
        flag = curses.A_BOLD if selected else 0
        #drawing the url
        url = websiteStats.getUrl()
        if len(url) > 30:
            url = url[:27]+"..."
        self.screen.addstr(l, 0, url, flag)

        #drawing the availabilities chart
        availabilities = websiteStats.getAvgAvailabilities2min()
        self.drawSparkline(l, 32, availabilities)

        #drawing the average response time
        self.screen.addstr(l, 70, str(round(1000*websiteStats.getAvgResponseTime()))+" ms", flag)

        #drawing the number of checks
        self.screen.addstr(l, 80, str(websiteStats.getNumberOfChecks()), flag)
    
    def getkey(self):
        return self.screen.getch()