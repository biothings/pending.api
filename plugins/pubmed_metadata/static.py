"""Release-specific constants for the PubMed metadata source."""

RELEASE = "2026jun30"
BASE_URL = f"https://stars.renci.org/var/babel_outputs/pubmed2db/{RELEASE}/"
SHARD_COUNT = 16

PUBMED_METADATA_FILES = tuple(
    f"pubmed_metadata_{index:05d}.ndjson.gz" for index in range(SHARD_COUNT)
)
PUBMED_METADATA_URLS = tuple(f"{BASE_URL}{filename}" for filename in PUBMED_METADATA_FILES)

NLM_TERMS_URL = "https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/README.txt"
PUBMED2DB_URL = "https://github.com/TranslatorSRI/pubmed2db"
