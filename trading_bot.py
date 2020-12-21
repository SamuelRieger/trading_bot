
import time
import sched
import cryptowatch as cw
from datetime import datetime, timedelta, date
import os
from dotenv import load_dotenv

load_dotenv()
apiKey = os.getenv('API_KEY_PUBLIC')
cw.api_key = apiKey
allStocks = []
class Player():
    def __init__(self, name, allocatedCapital):
        self.name = name
        self.allocatedCapital = allocatedCapital
        self.availableCapital = allocatedCapital
        self.strategies = []
        self.positions = []
        self.completedTrades = []
        self.profit = 0
    def AllocateCapital(self, proposedCapital):
        if self.availableCapital - proposedCapital < 0:
            return -1
        self.availableCapital -= proposedCapital
        return proposedCapital
    def AddStrategie(self, strategie):
        self.strategies.append(strategie)
    def AddPosition(self, position):
        self.positions.append(position)
    def AddCompletedTrade(self, completedTrade):
        self.completedTrades.append(completedTrade)
    def AddProfit(self, profit):
        self.profit += profit
    def CalculateProfit(self):
        self.tempProfit = 0
        for trade in self.completedTrades:
            self.tempProfit += trade.profit
        self.profit = self.tempProfit

class Stock():
    def __init__(self, symbol, market):
        self.symbol = symbol #BTCUSD
        self.market = market #KRAKEN
        self.marketSymbol = f'{market.upper()}:{symbol.upper()}'
        self.Update()
        allStocks.append(self)
    def Update(self):
        #Update stock data using symbol
        stock = cw.markets.get(self.marketSymbol, ohlc=True, periods=["1m"]) 
        #Each candle is a list of [close_timestamp, open, high, low, close, volume, volume_quote]
        high = 0.0
        #Collates the last 360 minutes of stock data (last 6 hours).
        for stockIndex in range(len(stock.of_1m) - 640):
            if stock.of_1m[-(stockIndex + 1)][2] > high:
                high = stock.of_1m[-(stockIndex + 1)][2]
        self.price = stock.of_1m[-1][4]
        self.xTimeHigh = high
        self.lastUpdate = stock.of_1m[-1][0]

def UpdateAllStocks():
    for stock in allStocks:
        stock.Update()

class Position():
   def __init__(self, stock, strategy, quantity, price, stopLoss, tradeType, entryDateTime):
       self.stock = stock
       self.quantity = quantity
       self.price = price
       self.stopLoss = stopLoss
       self.tradeType = tradeType
       self.entryDateTime = entryDateTime

class CompletedTrade():
    def __init__(self, stock, strategy, profit, quantity, entryPrice, entryTradeType, entryDateTime, exitPrice, exitTradeType, exitDateTime):
        self.stock = stock
        self.strategy = strategy
        self.quantity = quantity 
        self.entryPrice = entryPrice
        self.entryTradeType = entryTradeType
        self.entryDateTime = entryDateTime
        self.exitPrice = exitPrice
        self.exitTradeType = exitTradeType
        self.exitDateTime = exitDateTime
        
class Strategy():
    def __init__(self, player, allocatedCapital, stock):
        self.player = player
        self.allocatedCapital = allocatedCapital
        self.stock = stock

class PreviousHigh(Strategy):
    def __init__(self, player, allocatedCapital, stock):
        super().__init__(player, allocatedCapital, stock)
        self.buyCapital = 10000
        self.profitPercentage = 0.02
        self.stopLossPercentage = 0.02
        self.availableCapital = allocatedCapital
    def AllocateCapital(self, proposedCapital):
        if self.availableCapital - proposedCapital < 0:
            return -1
        self.availableCapital -= proposedCapital
        return proposedCapital
    def UpdateStrategy(self):
        self.previousHigh = self.stock.xTimeHigh
        self.stock.Update()
    def UpdateStockLoss(self, position):
        if self.stock.price * (1 - self.stopLossPercentage) > position.stopLoss:
            position.stopLoss = self.stock.price * (1 - self.stopLossPercentage)
    def CheckEntry(self):
        #Check if the conditions are met for an entry, check if there is enough capital
        #If conditions are met add to player positions 
        if self.previousHigh <= self.stock.price:
            if self.availableCapital > 0: 
                self.tempCapital = self.AllocateCapital(self.availableCapital)
                if self.tempCapital == -1:
                    print('Not enough capital.')
                    return
                self.tempQuantity = self.tempCapital / self.stock.price
                self.tempStopLoss = self.stock.price * (1 - self.stopLossPercentage)
                self.tempPosition = Position(self.stock, self, self.tempQuantity, self.stock.price, self.tempStopLoss, 'buy', datetime.now())
                self.player.positions.append(self.tempPosition) 
                print('Entry')
    def CheckExit(self, position):
        #Check if the conditions are met for an exit, if stop loss is hit or percentage profit reaches maximum
        #If they are, add to completed trades Player.AddCompleteTrade, calculate profit from current trade and call Player.AddProfit
        #If not, UpdateStockLoss(position)
        if position.price * (1 + self.profitPercentage) <= self.stock.price or position.price * (1 - self.stopLossPercentage) >= self.stock.price:
            self.tempProfit = self.stock.price * position.quanitiy - position.price * position.quantity
            self.tempCompletedTrade = CompletedTrade(self.stock, self, self.tempProfit, position.quantity, position.price, position.tradeType, position.entryDateTime, self.stock.price, 'sell', datetime.now())
            self.player.completedTrades.append(self.tempCompletedTrade)
            self.player.CalculateProfit()
            print(self.player.profit)
            print('Exit')
        else:
            self.UpdateStockLoss(position)

testStrategieCheck = True
testStrategieCounter = 0
def test():
    testPlayer = Player('Samuel', 10000)
    testStock = Stock('BTCUSD', 'KRAKEN')
    testCapital = testPlayer.AllocateCapital(testPlayer.allocatedCapital)
    if testCapital == -1:
        print('Not enough capital.')
        return
    testStrategie = PreviousHigh(testPlayer, testCapital, testStock)
    testPlayer.AddStrategie(testStrategie)
    s = sched.scheduler(time.time, time.sleep)
    def StrategieLoop(sc): 
        for strategie in testPlayer.strategies:
            strategie.UpdateStrategy()
            strategie.CheckEntry()
            
        for position in testPlayer.positions:
            position.strategie.CheckExit(position)

        print('***Stock Check***')
        print(f'Current Price: {strategie.stock.price}')
        print(f'Current High: {strategie.stock.xTimeHigh}')
        global testStrategieCheck
        if testStrategieCheck == True:
            s.enter(10, 1, StrategieLoop, (sc,))

    s.enter(10, 1, StrategieLoop, (s,))
    s.run()

test()
