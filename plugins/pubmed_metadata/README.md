# PubMed metadata

This source ingests the RENCI `pubmed2db` snapshot published at
<https://stars.renci.org/var/babel_outputs/pubmed2db/2026jun30/>. The pinned
release contains 16 gzip-compressed NDJSON shards (about 16.85 GB compressed).

Each upstream record is stored under a `pubmed` source key in a standalone
PubMed index:

```json
{
  "_id": "PMID:12345678",
  "pubmed": {
    "journal": {
      "name": "Example Journal",
      "abbr": "Example J"
    },
    "title": "Example title",
    "vol": "1",
    "iss": "2",
    "pub_date": "2026-06-30",
    "abstract": "Example abstract"
  }
}
```

The parser streams each compressed shard without materializing it in memory. It
requires the exact ten-field upstream schema, string values, valid
`PMID:<digits>` identifiers, valid UTF-8, and valid gzip/NDJSON input. A
malformed record fails the upload with the shard and line number rather than
producing a partial or silently altered document. The default storage also
treats duplicate IDs as an error.

The parser converts NLM month abbreviations to numbers and preserves the
available publication-date precision: `YYYY-MM-DD` when all parts exist,
`YYYY-MM` when the day is missing, and `YYYY` when only the year exists. It
omits `pub_date` when the year is absent. Elasticsearch maps all three forms as
a date; partial dates sort at the beginning of their represented period.

Downloads and uploads are each capped at four concurrent shards. For
compatibility with pending.api's BioThings Hub 0.12.x dependency, the uploader
partitions the 16 shards among four workers instead of relying only on the
per-source concurrency setting introduced in BioThings Hub 1.x. Abstracts are
retained in Elasticsearch `_source` but are not indexed or sortable. The other
metadata fields are indexed. `title` supports full-text matching and relevance
scoring but is not sortable. `journal.name` uses its `.raw` keyword subfield
when sorting; the keyword and date fields are directly sortable. Because this
is a very large source, the uploader retains only one previous MongoDB source
collection instead of the BioThings default of ten.

Build `pubmed_metadata` by itself into a versioned `pubmed_*` Elasticsearch
index. After validating the index, point the stable `annotator-pubmed` alias to
it. NodeAnnotator routes `PMID:` identifiers to that alias.

For subsequent releases, move the alias from the previous index to the newly
validated index in one atomic Elasticsearch alias update. Keep the previous
index temporarily for rollback and remove it separately after validation.
Build configuration and alias state are deployment state and are not stored in
this repository.

This is a full snapshot rather than an incremental feed. DOI and PMC identifiers
are not present in this export. To adopt a newer snapshot, update `RELEASE` in
`static.py` and verify that its shard count and schema are unchanged.

The export is produced by
[TranslatorSRI/pubmed2db](https://github.com/TranslatorSRI/pubmed2db) from NLM
PubMed data. Downstream use must follow the
[NLM PubMed terms and conditions](https://ftp.ncbi.nlm.nih.gov/pubmed/baseline/README.txt).
