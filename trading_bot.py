import time
import sched
import cryptowatch as cw
from datetime import datetime, timedelta, date
import os
from dotenv import load_dotenv
from nomics import Nomics

load_dotenv()
apiKey = os.getenv('API_KEY')
nomics = Nomics(apiKey)

print(nomics.Currencies.get_currencies(ids = "BTC", interval = "1h"))

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
        if self.availableCapital - proposedCapital < 0 or self.availableCapital == 0:
            return -1
        self.availableCapital -= proposedCapital
        return proposedCapital
    def AddStrategy(self, strategy):
        self.strategies.append(strategy)
    def AddPosition(self, position):
        self.positions.append(position)
    def RemovePosition(self, position):
        self.positions.remove(position)
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
    def __init__(self, ticker):
        self.ticker = ticker #BTC
        self.xTimeHigh = 0.0
        self.Update()
        allStocks.append(self)
    def Update(self):
        #Update stock data using ticker
        stock = nomics.Currencies.get_currencies(ids = self.ticker, interval = '1h') 
        if float(stock[0]['price']) > self.xTimeHigh:
            self.xTimeHigh = float(stock[0]['price'])
        self.price = float(stock[0]['price'])
        self.lastUpdateTime = stock[0]['price_timestamp'] 

def UpdateAllStocks():
    for stock in allStocks:
        stock.Update()

class Position():
    def __init__(self, stock, strategy, quantity, price, stopLoss, tradeType, entryDateTime):
       self.stock = stock
       self.strategy = strategy
       self.quantity = quantity
       self.price = price
       self.stopLoss = stopLoss
       self.tradeType = tradeType
       self.entryDateTime = entryDateTime

    def CompletePosition(self, player):
        player.RemovePosition(self)

class CompletedTrade():
    def __init__(self, stock, strategy, profit, quantity, entryPrice, entryTradeType, entryDateTime, exitPrice, exitTradeType, exitDateTime):
        self.stock = stock
        self.strategy = strategy
        self.profit = profit
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
        self.profitPercentage = 0.005
        self.stopLossPercentage = 0.005
        self.availableCapital = allocatedCapital
    def AllocateCapital(self, proposedCapital):
        if self.availableCapital - proposedCapital < 0 or self.availableCapital == 0:
            return -1
        self.availableCapital -= proposedCapital
        return proposedCapital
    def ReturnCapital(self, returnedCapital):
       self.availableCapital = returnedCapital 
    def UpdateStrategy(self):
        self.previousHigh = self.stock.xTimeHigh
        self.stock.Update()
    def UpdateStockLoss(self, position):
        if self.stock.price * (1 - self.stopLossPercentage) > position.stopLoss:
            position.stopLoss = self.stock.price * (1 - self.stopLossPercentage)
            print('Stock loss updated.')
    def CheckEntry(self):
        #Check if the conditions are met for an entry, check if there is enough capital
        #If conditions are met add to player positions 
        if self.previousHigh <= self.stock.price:
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
            self.tempProfit = self.stock.price * position.quantity - position.price * position.quantity
            self.tempPositionExitPrice = self.stock.price * position.quantity
            self.tempCompletedTrade = CompletedTrade(self.stock, self, self.tempProfit, position.quantity, position.price, position.tradeType, position.entryDateTime, self.stock.price, 'sell', datetime.now())
            self.player.completedTrades.append(self.tempCompletedTrade)
            position.CompletePosition(self.player)
            self.ReturnCapital(self.tempPositionExitPrice)
            self.player.CalculateProfit()
            print(self.player.profit)
            print('Exit')
        else:
            self.UpdateStockLoss(position)

def test():
    testPlayer = Player('Samuel', 10000)
    testStock = Stock('BTC')
    testCapital = testPlayer.AllocateCapital(testPlayer.allocatedCapital)
    testCheckInterval = 15
    if testCapital == -1:
        print('Not enough capital.')
        return
    testStrategy = PreviousHigh(testPlayer, testCapital, testStock)
    testPlayer.AddStrategy(testStrategy)
    testStrategyCheck = True
    testStrategyCounter = 0
    s = sched.scheduler(time.time, time.sleep)
    def StrategyLoop(sc): 
        for strategy in testPlayer.strategies:
            strategy.UpdateStrategy()
            strategy.CheckEntry()
            
        for position in testPlayer.positions:
            position.strategy.CheckExit(position)

        print('***Stock Check***')
        print(f'Current Price: {strategy.stock.price}')
        print(f'Previous High: {strategy.stock.xTimeHigh}')
        print(f'Total Trades: {len(strategy.player.completedTrades)}')
        print(f'Current Positions: {len(strategy.player.positions)}')
        print(f'Current Profit: {strategy.player.profit}')
        if testStrategyCheck == True:
            s.enter(testCheckInterval, 1, StrategyLoop, (sc,))
                  
    s.enter(testCheckInterval, 1, StrategyLoop, (s,))
    s.run()
test() 

