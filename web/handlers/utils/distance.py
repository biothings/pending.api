import math

# Some JSON libraries cannot parse `float('inf')`, this constant string can be used for such scenarios.
INFINITY_STR = "Infinity"


class NGDZeroCountException(Exception):
    """
    Raised when the count of a term (i.e. f(x) or f(y) in the wikipedia NGD formula) is 0 in the corpus.
    Normalized Google Distance is not defined in this scenario.
    """
    def __init__(self, term: str):
        self.term = term


class NGDUndefinedException(Exception):
    """
    Raised when Normalized Google Distance cannot be computed for the input two terms.
    """
    def __init__(self, cause: Exception):
        self.cause = cause


class NGDInfinityException(Exception):
    """
    Raised when the counts of two terms (i.e. f(x, y) in the wikipedia NGD formula) is 0 in the corpus.
    Normalized Google Distance is infinite in this scenario, regardless of the formula.
    """
    pass


def normalized_google_distance(n: int, fx: int, fy: int, fxy: int):
    """
    Calculate Normalized Google Distance between two SemmedDB entities.
    See https://en.wikipedia.org/wiki/Normalized_Google_distance

    :param int n: number of indexed webpages times average number of singleton keywords on each webpage.
    In SemmedDB, this number is simply the total number of associations, i.e. the total number of documents in
    SemmedDB ES index (one such document contains only one association)
    :param int fx: number of hits for keyword x
    :param int fy: number of hits for keyword y
    :param int fxy: number of hits that x & y both occur
    """
    assert fx > 0, f"Caller must ensure that fx > 0. Got fx={fx}."
    assert fy > 0, f"Caller must ensure that fy > 0. Got fy={fy}."

    if fxy == 0:
        # In this case, both terms appear separately in the corpus, but they never appear together in a single document.
        # According to wikipedia, NGD is infinite in this case, formula below not used
        return float('inf')

    # It's really annoying to guess what the base is for log calculation.
    # From the example on the wikipedia page, we can infer that it's 2.
    base = 2

    log_fx = math.log(fx, base)
    log_fy = math.log(fy, base)
    log_fxy = math.log(fxy, base)
    log_n = math.log(n, base)

    dividend = max(log_fx, log_fy) - log_fxy
    divisor = log_n - min(log_fx, log_fy)
    return dividend / divisor
