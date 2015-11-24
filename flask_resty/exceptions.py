class IncorrectTypeError(ValueError):
    def __init__(self, actual, expected):
        super(IncorrectTypeError, self).__init__(
            "incorrect object type, got {} but expected {}"
            .format(actual, expected)
        )
