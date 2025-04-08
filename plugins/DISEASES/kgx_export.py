import json
from parser import load_data

def main():
    # Replace this with the path to your actual data folder
    data_folder = ".biothings_hub/archive/DISEASES/1.0/"

    # Output filename
    output_file = "example_output.json"

    # Call load_data to get a generator (or list) of documents
    docs_generator = load_data(data_folder)

    with open(output_file, "w") as f:
        for i, doc in enumerate(docs_generator):

            if not doc["DISEASES"]["associatedWith"]:
                continue

            if i == 100:
                break

            json.dump(doc, f)
            f.write("\n")

if __name__ == "__main__":
    main()
