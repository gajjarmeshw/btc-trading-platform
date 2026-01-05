class RiskGovernor:
    def __init__(self, max_daily_loss=3):
        self.max_daily_loss = max_daily_loss

    def can_trade(self):
        return True
