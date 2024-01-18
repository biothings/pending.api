import orjson
import csv
import os
from typing import Dict

# maps nutrient names to CHEBI IDs
# to update mappings, the nutrient names can be retrieved from get_nutrient_stats.py
chebi_mappings = {
    'total': '',
    'Energy': '',
    'Water': '',
    'Total lipid (fat)': '',
    'Protein': '',
    'Iron, Fe': 'CHEBI:18248',
    'Magnesium, Mg': 'CHEBI:25107',
    'Phosphorus, P': 'CHEBI:28659',
    'Copper, Cu': 'CHEBI:28694',
    'Manganese, Mn': 'CHEBI:18291',
    'Calcium, Ca': 'CHEBI:22984',
    'Potassium, K': 'CHEBI:26216',
    'Zinc, Zn': 'CHEBI:27363',
    'Ash': '',
    'Carbohydrate, by difference': '',
    'Sodium, Na': 'CHEBI:26708',
    'Nitrogen': 'CHEBI:29351',
    'Niacin': 'CHEBI:176839',
    'Vitamin B-6': 'CHEBI:27306',
    'Thiamin': 'CHEBI:18385',
    'Riboflavin': 'CHEBI:17015',
    'Selenium, Se': 'CHEBI:27568',
    'Fructose': 'CHEBI:28757',
    'Lactose': 'CHEBI:17716',
    'Sucrose': 'CHEBI:17992',
    'Glucose': 'CHEBI:17234',
    'Maltose': 'CHEBI:17306',
    'Folate, total': 'CHEBI:67011',
    'Fiber, total dietary': '',
    'Sugars, Total NLEA': '',
    'Galactose': 'CHEBI:28260',
    'Fatty acids, total saturated': 'CHEBI:26607',
    'Fatty acids, total monounsaturated': '',
    'SFA 16:0': 'CHEBI:140943',
    'SFA 18:0': 'CHEBI:140947',
    'MUFA 18:1 c': 'CHEBI:140948',
    'PUFA 18:2 n-6 c,c': 'CHEBI:140949',
    'SFA 14:0': 'CHEBI:140940',
    'Fatty acids, total polyunsaturated': 'CHEBI:26208',
    'MUFA 16:1 c': 'CHEBI:140944',
    'MUFA 20:1 c': 'CHEBI:132538',
    'SFA 20:0': 'CHEBI:140951',
    'SFA 12:0': 'CHEBI:78119',
    'PUFA 18:2 c': 'CHEBI:140949',
    'PUFA 18:3 c': 'CHEBI:132502',
    'Total fat (NLEA)': '',
    'SFA 17:0': 'CHEBI:140945',
    'SFA 24:0': 'CHEBI:155816',
    'SFA 15:0': 'CHEBI:140942',
    'Vitamin E (alpha-tocopherol)': 'CHEBI:22470',
    'PUFA 18:3 n-3 c,c,c (ALA)': 'CHEBI:140950',
    'PUFA 20:3 c': 'CHEBI:36036',
    'PUFA 20:4 n-6': 'CHEBI:140956',
    'SFA 10:0': '',
    'Tocopherol, delta': 'CHEBI:47772',
    'PUFA 20:4': 'CHEBI:132539',
    'Tocopherol, beta': 'CHEBI:47771',
    'Tocopherol, gamma': 'CHEBI:18185',
    'MUFA 14:1 c': '',
    'PUFA 20:4c': '',
    'Energy (Atwater General Factors)': '',
    'Tocotrienol, gamma': 'CHEBI:33277',
    'Tocotrienol, delta': 'CHEBI:33276',
    'PUFA 22:6 n-3 (DHA)': 'CHEBI:36005',
    'SFA 22:0': 'CHEBI:140958',
    'PUFA 20:5 n-3 (EPA)': 'CHEBI:36006',
    'Tocotrienol, alpha': 'CHEBI:33270',
    'Tocotrienol, beta': 'CHEBI:33275',
    'PUFA 20:5c': 'CHEBI:132540',
    'PUFA 22:6 c': 'CHEBI:132544',
    'PUFA 22:5 n-3 (DPA)': 'CHEBI:61204',
    'MUFA 17:1': 'CHEBI:140946',
    'PUFA 20:2 n-6 c,c': 'CHEBI:140952',
    'MUFA 17:1 c': 'CHEBI:140946',
    'PUFA 22:5 c': '',
    'PUFA 20:2 c': 'CHEBI:140952',
    'PUFA 18:2 CLAs': '',
    'Energy (Atwater Specific Factors)': '',
    'Fatty acids, total trans': 'CHEBI:166968',
    'TFA 16:1 t': 'CHEBI:140944',
    'Fatty acids, total trans-monoenoic': '',
    'TFA 18:1 t': 'CHEBI:140948',
    'TFA 18:2 t not further defined': 'CHEBI:140949',
    'SFA 8:0': 'CHEBI:141071',
    'SFA 4:0': '',
    'SFA 6:0': '',
    'Pantothenic acid': 'CHEBI:7916',
    'MUFA 22:1 c': '',
    'PUFA 18:4': '',
    'PUFA 18:3 n-6 c,c,c': 'CHEBI:140950',
    'MUFA 15:1': '',
    'Vitamin A, RAE': 'CHEBI:12777',
    'PUFA 22:2': 'CHEBI:140959',
    'Vitamin C, total ascorbic acid': 'CHEBI:29073',
    'MUFA 24:1 c': 'CHEBI:140963',
    'PUFA 20:3 n-3': 'CHEBI:140954',
    'PUFA 22:4': 'CHEBI:132542',
    'SFA 11:0': '',
    'TFA 22:1 t': '',
    'Fatty acids, total trans-dienoic': '',
    'Biotin': 'CHEBI:15956',
    'Cholesterol': 'CHEBI:16113',
    'Starch': 'CHEBI:28017',
    'Vitamin D (D2 + D3)': '',
    'Vitamin D (D2 + D3), International Units': '',
    'Vitamin K (phylloquinone)': 'CHEBI:18067',
    'PUFA 20:3 n-9': '',
    'Vitamin B-12': 'CHEBI:176843',
    'Vitamin D2 (ergocalciferol)': 'CHEBI:28934',
    'Cryptoxanthin, beta': 'CHEBI:1036',
    'Carotene, alpha': 'CHEBI:28425',
    'Tryptophan': 'CHEBI:27897',
    'Threonine': 'CHEBI:26986',
    'Methionine': 'CHEBI:16811',
    'Phenylalanine': 'CHEBI:28044',
    'Tyrosine': 'CHEBI:18186',
    'Alanine': 'CHEBI:16449',
    'Glutamic acid': 'CHEBI:18237',
    'Glycine': 'CHEBI:15428',
    'Proline': 'CHEBI:26271',
    'Isoleucine': 'CHEBI:24898',
    'Leucine': 'CHEBI:2501',
    'Lysine': 'CHEBI:25094',
    'Valine': 'CHEBI:27266',
    'Arginine': 'CHEBI:29016',
    'Histidine': 'CHEBI:27570',
    'Aspartic acid': 'CHEBI:22660',
    'Serine': 'CHEBI:17822',
    'Molybdenum, Mo': 'CHEBI:28685',
    'Vitamin K (Dihydrophylloquinone)': '',
    'Carotene, beta': 'CHEBI:17579',
    'Lycopene': 'CHEBI:15948',
    'Retinol': 'CHEBI:50211',
    'Vitamin D3 (cholecalciferol)': 'CHEBI:73558',
    'MUFA 20:1': '',
    'Vitamin K (Menaquinone-4)': 'CHEBI:78277',
    'Carbohydrate, by summation': 'CHEBI:16646',
    'Lutein + zeaxanthin': '',
    'MUFA 22:1 n-9': '',
    'Choline, total': 'CHEBI:15354',
    'Choline, from glycerophosphocholine': '',
    'Betaine': '',
    'Choline, from sphingomyelin': '',
    'Choline, free': '',
    'Choline, from phosphotidyl choline': '',
    'Choline, from phosphocholine': '',
    'Iodine, I': 'CHEBI:24859',
    'Fatty acids, total trans-polyenoic': '',
    'TFA 18:3 t': '',
    'Hydroxyproline': 'CHEBI:24741',
    'Cysteine': 'CHEBI:1535',
    'SFA 21:0': '',
    'Cystine': 'CHEBI:17376',
    'Boron, B': 'CHEBI:27560',
    'Cobalt, Co': 'CHEBI:27638',
    'Nickel, Ni': 'CHEBI:28112',
    'Sulfur, S': 'CHEBI:26833',
    '25-hydroxycholecalciferol': '',
    'SFA 5:0': '',
    'SFA 7:0': 'CHEBI:141070',
    'SFA 9:0': 'CHEBI:141072',
    'MUFA 12:1': '',
    'MUFA 22:1 n-11': '',
    'SFA 23:0': 'CHEBI:141094',
    'PUFA 22:3': 'CHEBI:140960',
    'cis-Lutein/Zeaxanthin': 'CHEBI:27547',
    'PUFA 18:3i': '',
    'TFA 14:1 t': '',
    'TFA 20:1 t': '',
    'Cryptoxanthin, alpha': '',
    'Citric acid': 'CHEBI:30769',
    'Malic acid': 'CHEBI:6650',
    'Zeaxanthin': 'CHEBI:27547',
    'Beta-sitosterol': 'CHEBI:27693',
    'Campesterol': 'CHEBI:28623',
    'Delta-5-avenasterol': '',
    'Beta-sitostanol': '',
    'Stigmasterol': 'CHEBI:89400',
    'trans-beta-Carotene': '',
    'cis-beta-Carotene': '',
    'cis-Lycopene': '',
    'Lutein': 'CHEBI:28838',
    'Ergothioneine': 'CHEBI:4828',
    'Vitamin D4': 'CHEBI:33237',
    'Oxalic acid': 'CHEBI:16995',
    'Quinic acid': 'CHEBI:26493',
    'Fiber, insoluble': '',
    'Fiber, soluble': '',
    'trans-Lycopene': 'CHEBI:15948',
    'Brassicasterol': 'CHEBI:3168',
    'Campestanol': 'CHEBI:36799',
    'Delta-7-Stigmastenol': '',
    'Vitamin A': 'CHEBI:12777',
    'Total dietary fiber (AOAC 2011.25)': '',
    'TFA 18:2 t': '',
    'Daidzin': 'CHEBI:42202',
    'Genistin': '',
    'Glycitin': 'CHEBI:80373',
    'Daidzein': 'CHEBI:28197',
    'Genistein': 'CHEBI:28088',
    'Sugars, total including NLEA': '',
    'Phytosterols, other': '',
    'Stigmastadiene': '',
    'Ergosterol': 'CHEBI:16933',
    'Ergosta-7-enol': '',
    'Ergosta-7,22-dienol': '',
    'Ergosta-5,7-dienol': '',
    'Carotene, gamma': 'CHEBI:27740',
    'MUFA 18:1': 'CHEBI:140948',
    'PUFA 18:2': 'CHEBI:140949',
    'PUFA 18:3': '',
    'Pyruvic acid': 'CHEBI:32816',
    'MUFA 22:1': '',
    'Phytofluene': 'CHEBI:26120',
    'Phytoene': 'CHEBI:26119',
    'Verbascose': 'CHEBI:28586',
    'Raffinose': 'CHEBI:16634',
    'Stachyose': 'CHEBI:17164',
    'Low Molecular Weight Dietary Fiber (LMWDF)': '',
    'High Molecular Weight Dietary Fiber (HMWDF)': '',
    'Specific Gravity': '',
    '10-Formyl folic acid (10HCOFA)': '',
    '5-Formyltetrahydrofolic acid (5-HCOH4': 'CHEBI:15640',
    '5-methyl tetrahydrofolate (5-MTHF)': '',
    'PUFA 20:3': 'CHEBI:36036',
    'Beta-glucan': ''
}


def get_chebi_id(nutrient_name: str):
    try:
        chebi_id = chebi_mappings[nutrient_name]
        return None if chebi_id == '' else chebi_id
    except KeyError:
        return None

# convert csv into a list of dicts


def read_csv(file: str, delim: str):
    info = []
    with open(file) as csv_file:
        reader = csv.reader(csv_file, delimiter=delim)
        categories: list[str]
        i = 0
        for row in reader:
            if len(row) == 0:
                continue
            if i == 0:
                categories = row
            else:
                info.append({})
                for j in range(len(row)):
                    info[i-1][categories[j]] = row[j]
            i += 1

    return info


def get_foodon_ids(data_folder: str) -> Dict[str, str]:
    attribute_data = read_csv(os.path.join(data_folder, 'FoodData_Central_foundation_food_csv_2022-04-28', 'food_attribute.csv'), ',')
    foodon_ids = {}
    for food_attr in attribute_data:
        if food_attr['name'] == 'FoodOn Ontology ID for FDC item':
            foodon_ids[food_attr['fdc_id']] = food_attr['value'][food_attr['value'].find('FOODON'):]
    return foodon_ids


def load_data(data_folder: str):
    foodon_ids = get_foodon_ids(data_folder)
    with open(os.path.join(data_folder, 'FoodData_Central_foundation_food_json_2022-04-28.json')) as f:
        data = orjson.loads(f.read())['FoundationFoods']
    for food in data:
        if not str(food['fdcId']) in foodon_ids:
            continue
        base = {
            'subject': {
                'description': food['description'],
                'ndbNumber': food['ndbNumber'],
                'fdcId': food['fdcId'],
                'foodOnId': foodon_ids[str(food['fdcId'])],
                'foodCategory': food['foodCategory']['description']
            }
        }
        for n in food['foodNutrients']:
            chebi_id = get_chebi_id(n['nutrient']['name'])
            if chebi_id == None:
                continue
            doc = base.copy()
            doc['object'] = {
                'nutrientName': n['nutrient']['name'],
                'nutrientId': n['nutrient']['id'],
                'nutrientRank': n['nutrient']['rank'],
                'chebiId': chebi_id
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


# def main():
#     obj = {}
#     nutrients = {"total": 0}
#     for docs in load_data('./'):
#         if docs['_id'] in obj:
#             print(docs['_id'])
#         obj[docs['_id']] = docs

#         if docs['object']['nutrientName'] in nutrients:
#             nutrients[docs['object']['nutrientName']] += 1
#         else:
#             nutrients[docs['object']['nutrientName']] = 1

#     print('done')
#     nutrients["total"] = len(nutrients.keys())
#     with open('./output.json', 'w') as f:
#         ujson.dump(obj, f, indent=2)


# if __name__ == '__main__':
#     main()
