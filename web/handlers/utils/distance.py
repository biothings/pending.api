import math


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
