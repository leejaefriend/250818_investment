import numpy as np
from quantylab.rltrader import utils

class Agent:
    # 상태 차원: 보유 비율, 손익률, 단가 대비 변화율, 거래량
    STATE_DIM = 4

    # 매매 수수료 및 세금
    TRADING_CHARGE = 0.0005  # 0.05%
    TRADING_TAX = 0  # 없음

    # 행동
    ACTION_BUY = 0
    ACTION_SELL = 1
    ACTION_HOLD = 2
    NUM_ACTIONS = 3

    def __init__(self, environment, balance=1000000,
                 min_trading_budget=1000, max_trading_budget=100000):
        self.environment = environment
        self.balance = balance
        self.num_coins = 0
        self.portfolio_value = balance
        self.avg_buy_price = 0
        self.profitloss = 0

        self.min_trading_budget = float(min_trading_budget)
        self.max_trading_budget = float(max_trading_budget)

    def reset(self):
        self.balance = 1000000
        self.num_coins = 0
        self.portfolio_value = self.balance
        self.avg_buy_price = 0
        self.profitloss = 0

    def get_states(self):
        ratio_hold = (
            self.num_coins * self.environment.get_price() / self.portfolio_value
            if self.portfolio_value > 0 else 0
        )
        profit_loss = self.profitloss
        rel_price = (
            (self.environment.get_price() / self.avg_buy_price) - 1
            if self.avg_buy_price > 0 else 0
        )
        volume = self.environment.get_volume() or 0
        return (ratio_hold, profit_loss, rel_price, volume)

    def decide_trading_unit(self, confidence):
        if np.isnan(confidence):
            return self.min_trading_budget
        added_trading_budget = max(min(
            confidence * (self.max_trading_budget - self.min_trading_budget),
            self.max_trading_budget - self.min_trading_budget), 0)
        trading_budget = self.min_trading_budget + added_trading_budget
        return max(trading_budget / self.environment.get_price(), 1)

    def act(self, action, confidence=1.0):
        curr_price = self.environment.get_price()
        if curr_price is None:
            return

        if action == self.ACTION_BUY:
            trading_unit = self.decide_trading_unit(confidence)
            balance_after = self.balance - curr_price * trading_unit
            if balance_after < 0:
                trading_unit = self.balance / (1 + self.TRADING_CHARGE) / curr_price
            self.balance -= curr_price * trading_unit * (1 + self.TRADING_CHARGE)
            self.num_coins += trading_unit
            self.avg_buy_price = curr_price
        elif action == self.ACTION_SELL:
            if self.num_coins > 0:
                self.balance += curr_price * self.num_coins * (1 - (self.TRADING_CHARGE + self.TRADING_TAX))
                self.num_coins = 0

        self.portfolio_value = self.balance + self.num_coins * curr_price
        self.profitloss = (self.portfolio_value - 1000000) / 1000000
