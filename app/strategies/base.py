class StrategyBase:
    name = "base"
    timeframe = "5m"

    def indicators(self, df):
        return df

    def should_enter(self, df):
        return False

    def should_exit(self, df, position):
        return False
