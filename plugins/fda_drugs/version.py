def get_release(self) -> str:
    release_version = self.parse_fda_drug_version()
    return release_version
