import os

import bmt


# We only want to load this once as it does incur some time to load the model, and we call this
# everytime we use the following endpoints:
# > get_normalized_nodes
# > get_semantic_types

BIOLINK_MODEL_VERSION = os.getenv("BIOLINK_VERSION", "v4.2.2")
BIOLINK_MODEL_URL = (
    f"https://raw.githubusercontent.com/biolink/biolink-model/{BIOLINK_MODEL_VERSION}/biolink-model.yaml"
)
toolkit = bmt.Toolkit(BIOLINK_MODEL_URL)
