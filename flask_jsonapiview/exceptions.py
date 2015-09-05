class IncorrectTypeError(ValueError):
    def __init__(self):
        super(IncorrectTypeError, self).__init__("incorrect object type")
