
import curses

class ScreenDrawer:

    def __init__(self, screen):
        # screen to draw on
        self.screen = screen
        
        # screen dimensions
        self.y, self.x = self.screen.getmaxyx()
    
    def fitsInScreen(self, y, x):
        return y >= 0 and x >= 0 and y < self.y and x < self.x-1

    def updateMaxYX(self):
        self.y, self.x = self.screen.getmaxyx()
    
    def getMaxYX(self):
        return self.y, self.x
    
    def refresh(self):
        self.screen.refresh()

    def clear(self):
        self.screen.clear()

    def draw(self, y, x, c, flag=0):
        if self.fitsInScreen(y, x):
            self.screen.addstr(y, x, c, flag) 

    def drawBox(self, y1, x1, y2, x2, boxname=""):
        for y in range(y1, y2+1):
            self.draw(y, x1, u'\u2502')
            self.draw(y, x2, u'\u2502')
        for x in range(x1, x2+1):
            self.draw(y1, x, u'\u2500')
            self.draw(y2, x, u'\u2500')
        self.draw(y1, x1, u'\u250C')
        self.draw(y1, x2, u'\u2510')
        self.draw(y2, x1, u'\u2514')
        self.draw(y2, x2, u'\u2518')
        if len(boxname) > 0:
            maxSize = x2 - x1 - 2
            self.drawText(y1, x1+1, " {0} ".format(boxname), curses.A_BOLD, maxSize)
    
    def drawText(self, y, x, text, flag=0, maxSize=0):
        if maxSize == 0 or maxSize > len(text):
            maxSize = len(text)
        if len(text) > maxSize:
            text = "{0}...".format(text[:maxSize-3])
        for i in range(maxSize):
            self.draw(y, x+i, text[i], flag)
        
