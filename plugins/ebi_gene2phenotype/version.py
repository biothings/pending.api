def get_release(self):
    import re
    from datetime import datetime

    dates = []
    date_pattern = re.compile(r'\d{1,2}_\d{1,2}_\d{4}')

    for url in self.__class__.SRC_URLS:
        res = self.client.head(url, allow_redirects=True)
        header = res.headers['Content-Disposition']
        match = date_pattern.findall(header)
        if len(match) != 1:
            raise ValueError("Parser Date Extraction Error")
        dates.append(datetime.strptime(match[0], '%d_%m_%Y').date())

    if dates[0] < dates[1]:
        latest_version = dates[1]
    else:
        latest_version = dates[0]

    return latest_version.isoformat()
