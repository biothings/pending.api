import os

import bmt


BIOLINK_MODEL_VERSION = os.getenv("BIOLINK_VERSION", "v4.2.2")


def load_biolink_model_toolkit() -> bmt.Toolkit:
    """
    Loads the biolink model toolkit for usage across the nodenorm web APIs
    """
    BIOLINK_MODEL_URL = (
        f"https://raw.githubusercontent.com/biolink/biolink-model/{BIOLINK_MODEL_VERSION}/biolink-model.yaml"
    )
    toolkit = bmt.Toolkit(BIOLINK_MODEL_URL)
    return toolkit
