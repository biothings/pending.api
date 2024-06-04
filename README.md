This repository maintains a set of biomedical knowledgebase APIs built with the [BioThings SDK](https://biothings.io).
These APIs are either the Knowledgebase APIs built for [the Translator Project](https://ncats.nih.gov/research/research-activities/translator)
or the "pending" APIs to be integrated into the [official BioThings APIs](https://biothings.io) (e.g. [MyGene.info](https://mygene.info), 
[MyVariant.info](https://myvariant.info), [MyChem.info](https://mychem.info), [MyDisease.info](https://mydisease.info) etc.)

The list of Translator-associated knowledgebase APIs are hosted at:
https://biothings.ncats.io.

There are additional APIs are hosted at https://pending.biothings.io.

## Knowledgebase APIs for the Translator Project

Each knowledgebase API is created as a "data plugin" (see examples under [plugins](/plugins) folder). The [BioThings SDK](https://biothings.io) package
will then process the data plugin and turn it into a hosted "BioThings API". You can follow the tutorial of the [data plugin](https://github.com/biothings/pending.api/tree/master/plugins) for more details.

### How to add a new API

Our internal developement team will handle the process of adding a new data plugin and deploying it as a new API. 
For our internal developers, please follow [this documentation](
https://github.com/biothings/biothings-internal/wiki/How-To-Add-A-New-KP-API-(to-pending.api))

### How to update data for an existing API
For external collaborators who have submitted their "data plugins" as new APIs, you can follow this workflow to request
a update of your data:

https://github.com/biothings/biothings_explorer/blob/main/docs/README-maintaining-a-data-source.md

The documentation is maintained at the [biothings_explorer](https://github.com/biothings/biothings_explorer) repository,
as each knowledgebase API will be integrated into the [BioThings Explorer application](https://explorer.biothings.io) become
a Translator's standard KP (Knowledge Provider) API.
