import numpy as np
from quantylab.rltrader import utils

class Agent:
    # 에이전트 상태가 구성하는 값 개수
    # 주식 보유 비율, 손익률, 주당 매수 단가 대비 주가 등락률
    STATE_DIM = 3

    # 매매 수수료 및 세금
    TRADING_CHARGE = 0.0005 # 거래 수수료 0.05%
    TRADING_TAX = 0 # 거래세 미적용

    # 행동
    ACTION_BUY = 0 # 매수
    ACTION_SELL = 1 # 매도
    ACTION_HOLD = 2 # 관망
    # 인공 신경망에서 확률을 구할 행동들
    ACTIONS = [ACTION_BUY, ACTION_SELL, ACTION_HOLD]
    NUM_ACTIONS = len(ACTIONS) # 인공 신경망에서 고려할 출력값의 개수

    def __init__(self, environment, initial_balance, min_trading_budget, max_trading_budget):
        # 현재 주식 가격을 가져오기 위해 환경 참조
        self.environment = environment
        self.initial_balance = initial_balance # 초기 자본금

        # 최소/최대 1회 주문 예산(원화)
        self.min_trading_budget = int(min_trading_budget)
        self.max_trading_budget = int(max_trading_budget)

        # Agent 클래스의 속성
        self.balance = initial_balance # 현재 현금 잔고
        self.num_coins = 0 # 보유 코인 수

        # 포트폴리오 가치 : balance + num_coins * (현재 코인 가격)
        self.portfolio_value = 0
        self.num_buy = 0 # 매수 횟수
        self.num_sell = 0 # 매도 횟수
        self.num_hold = 0 # 관망 횟수

        # Agent 클래스의 상태
        self.ratio_hold = 0 # 코인 보유 비율
        self.profitloss = 0 # 손익률
        self.avg_buy_price = 0 # 코인당 매수 단가

    def reset(self):
        self.balance = self.initial_balance
        self.num_coins = 0
        self.portfolio_value = self.initial_balance
        self.num_buy = 0
        self.num_sell = 0
        self.num_hold = 0
        self.ratio_hold = 0
        self.profitloss = 0
        self.avg_buy_price = 0

    def set_balance(self, balance):
        self.initial_balance = balance

    def get_states(self):
        self.ratio_hold = self.num_coins * self.environment.get_price() / self.portfolio_value
        return(self.ratio_hold, self.profitloss, (self.environment.get_price() / self.avg_buy_price) - 1 if self.avg_buy_price > 0 else 0)

    def decide_action(self, pred_value, pred_policy, epsilon):
        confidence = 0.

        pred = pred_policy
        if pred is None:
            pred = pred_value

        if pred is None:
            # 예측 값이 없을 경우 탐험
            epsilon = 1
        else:
            # 값이 모두 같은 경우 탐험
            maxpred = np.max(pred)
            if (pred == maxpred).all():
                epsilon = 1

        # 탐험 결정
        if np.random.rand() < epsilon:
            exploration = True
            action = np.random.randint(self.NUM_ACTIONS)
        else:
            exploration = False
            action = np.argmax(pred)

        confidence = .5

        if pred_policy is not None:
            confidence = pred[action]
        elif pred_value is not None:
            confidence = utils.sigmoid(pred[action])

        return action, confidence, exploration

    def validate_action(self, action):
        if action == Agent.ACTION_BUY:
            # 적어도 5000원 상당의 코인을 매수할 수 있는지 확인
            if self.balance < 5000:
                return False
            elif action == Agent.ACTION_SELL:
                # 매도 가능 조건 : 보유 코인이 있고, 평가 금액이 5000원 이상
                if self.num_coins * self.environment.get_price() < 5000:
                    return False
            return True

    def decide_trading_unit(self, confidence):
        price = self.environment.get_price()
        if price is None or price <= 0:
            return 0.0

        # 1) 매수 시 예산(원화) 계산
        if action == self.ACTION_BUY:
            if np.isnan(confidence):
                budget = self.min_trading_budget
            else:
                span = max(self.max_trading_price - self.min_trading_price, 0.0)
                added_trading_price = max(min(confidence * span, span), 0.0)  # 원(krw)
                budget = self.min_trading_price + added_trading_price

            budget = min(budget, self.balance)
            if budget < 5000.0:
                return 0.0

            denom = price * (1.0 + self.TRADING_CHARGE)
            units = 0.0 if denom <= 0 else (budget / denom)

            # 최소 주문 수량(수수료 반영)
            min_unit_rule = 5000.0 / denom
            units = max(units, min_unit_rule)

        # 매도 시 수량 결정
        elif action == self.ACTION_SELL:
            units = self.num_coins
            # 최소 주문 금액 미만이면 매도 불가
            if units * price < 5000.0:
                return 0.0

        3)


        # 3) 업비트 최소 주문 5,000원 미만이면 주문하지 않음
        if budget < 5000.0:
            return 0.0

        # 4) 수수료 반영하여 코인 수량 계산


        if np.isnan(confidence):
            return self.min_trading_price
        added_trading_price = max(min(confidence * (self.max_trading_price - self.min_trading_price), self.max_trading_price - self.min_trading_price), 0)
        trading_price = self.min_trading_price + added_trading_price
        return trading_price / self.environment.get_price()




