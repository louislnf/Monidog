
class History:
    def __init__(self, capacity):
        self.capacity = capacity
        self.indexOfLastPushedValue = -1
        self.values = []
    
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
    
    def getValuesUntilCondition(self, condition):
        # returns an empty list if the history is empty
        if self.indexOfLastPushedValue == -1:
            return []
        #returns the values in the history until the condition is broken
        selectedValues = []
        i = self.indexOfLastPushedValue
        looped = False
        while not(condition(self.values[i])) and not(looped):
            selectedValues.append(self.values[i])
            i = (i-1) % len(self.values)
            looped = self.indexOfLastPushedValue == i
        
        return selectedValues
    
    def getLastPushedValue(self):
        if len(self.values) > 0:
            return self.values[self.indexOfLastPushedValue]
        else:
            return None

if __name__ == '__main__':
    h = History(10)
    for i in range(15):
        h.add(i)
    print(h.getValues)
    print(h.getValuesUntilCondition(lambda x: x<7))