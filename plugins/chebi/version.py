def get_release(self):

    import datetime
    import requests

    res = requests.head('http://purl.obolibrary.org/obo/chebi.obo')
    try:
        return datetime.datetime.strptime(
            res.headers['Date'], '%a, %d %b %Y %H:%M:%S %Z'
        ).strftime('%Y-%m-%d')
    except AttributeError:
        return datetime.datetime.now().strftime('%Y-%m-%d')
