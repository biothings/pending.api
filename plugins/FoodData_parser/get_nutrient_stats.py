import ujson
import os


def load_data(data_folder: str):
    with open(os.path.join(data_folder, 'FoodData_Central_foundation_food_json_2022-04-28.json')) as f:
        data = ujson.load(f)['FoundationFoods']
    for food in data:
        base = {
            'subject': {
                'description': food['description'],
                'ndbNumber': food['ndbNumber'],
                'fdcId': food['fdcId'],
                'foodCategory': food['foodCategory']['description']
            }
        }
        for n in food['foodNutrients']:
            doc = base.copy()
            doc['object'] = {
                'nutrientName': n['nutrient']['name'],
                'nutrientId': n['nutrient']['id'],
                'nutrientRank': n['nutrient']['rank']
            }
            doc['relation'] = {}

            if 'amount' in n:
                doc['object']['nutrientAmount'] = n['amount']
                doc['object']['nutrientAmountUnits'] = n['nutrient']['unitName']

            if 'code' in n['foodNutrientDerivation']:
                doc['relation']['code'] = n['foodNutrientDerivation']['code']
            if 'code' in n['foodNutrientDerivation']['foodNutrientSource']:
                doc['relation']['sourceCode'] = n['foodNutrientDerivation']['foodNutrientSource']['code']
            if 'description' in n['foodNutrientDerivation']:
                doc['relation']['description'] = n['foodNutrientDerivation']['description']
            if 'description' in n['foodNutrientDerivation']['foodNutrientSource']:
                doc['relation']['sourceDescription'] = n['foodNutrientDerivation']['foodNutrientSource']['description']

            if 'min' in n:
                doc['relation']['nutrientMinAmount'] = n['min']
            if 'max' in n:
                doc['relation']['nutrientMaxAmount'] = n['max']
            if 'median' in n:
                doc['relation']['nutrientMedianAmount'] = n['median']

            doc['_id'] = f"{doc['subject']['fdcId']}-{doc['object']['nutrientId']}"
            yield doc


def main():
    obj = {}
    nutrients = {"total": 0}
    for docs in load_data('./'):
        if docs['_id'] in obj:
            print(docs['_id'])
        obj[docs['_id']] = docs

        if docs['object']['nutrientName'] in nutrients:
            nutrients[docs['object']['nutrientName']] += 1
        else:
            nutrients[docs['object']['nutrientName']] = 1

    print('done')
    nutrients["total"] = len(nutrients.keys())
    with open('./output.tsv', 'w') as f:
        f.write("nutrient\tcount\n")
        for i in nutrients:
            f.write(f"{i}\t{nutrients[i]}\n")


if __name__ == '__main__':
    main()
