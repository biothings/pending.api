import math

# Some JSON libraries cannot parse `float('inf')`, this constant string can be used for such scenarios.
INFINITY_STR = "Infinity"
UNDEFINED_STR = "undefined"


class NGDUndefinedException(Exception):
    """
    Raised when Normalized Google Distance cannot be computed for the input two terms.
    """
    pass


class NGDZeroDocFreqException(NGDUndefinedException):
    """
    Raised when the document frequency of a term (i.e. f(x) or f(y) in the wikipedia NGD formula) is 0 in the corpus.
    Normalized Google Distance is not defined in this scenario.
    """
    def __init__(self, term):
        self.term = term  # the term that causes this exception


class NGDInfinityException(Exception):
    """
    Raised when the counts of two terms (i.e. f(x, y) in the wikipedia NGD formula) is 0 in the corpus.
    Normalized Google Distance is infinite in this scenario, regardless of the formula.
    """
    pass


def normalized_google_distance(n: int, f_x: int, f_y: int, f_xy: int):
    """
    Calculate Normalized Google Distance between two SemmedDB entities.
    See https://en.wikipedia.org/wiki/Normalized_Google_distance

    :param int n: number of indexed webpages times average number of singleton keywords on each webpage.
    In SemmedDB, this number is simply the total number of associations, i.e. the total number of documents in
    SemmedDB ES index (one such document contains only one association)
    :param int f_x: document frequency of term (or keyword) x
    :param int f_y: document frequency of term (or keyword) y
    :param int f_xy: document frequency that x & y both occur in
    """
    assert f_x > 0, f"Caller must ensure that f_x > 0. Got f_x={f_x}."
    assert f_y > 0, f"Caller must ensure that f_y > 0. Got f_y={f_y}."

    if f_xy == 0:
        # In this case, both terms appear separately in the corpus, but they never appear together in a single document.
        # According to wikipedia, NGD is infinite in this case, formula below not used
        return float('inf')

    # It's really annoying to guess what the base is for log calculation.
    # From the example on the wikipedia page, we can infer that it's 2.
    base = 2

    log_f_x = math.log(f_x, base)
    log_f_y = math.log(f_y, base)
    log_f_xy = math.log(f_xy, base)
    log_n = math.log(n, base)

    dividend = max(log_f_x, log_f_y) - log_f_xy
    divisor = log_n - min(log_f_x, log_f_y)
    return dividend / divisor
