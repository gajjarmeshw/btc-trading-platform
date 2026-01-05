class Exchange:
    def buy(self, size):
        raise NotImplementedError

    def sell(self):
        raise NotImplementedError
    
    def has_position(self):
        raise NotImplementedError
