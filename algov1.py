financeWeight = 0.15
supplyWeight = 0.25
populationWeight = 0.1
urgencyWeight = 0.3
capacityWeight = 0.2


def calculateScore(finance, supply, population, urgency, capacity):
    score = (finance * financeWeight +
             supply * supplyWeight +
             population * populationWeight +
             urgency * urgencyWeight +
             capacity * capacityWeight)
    return score


def isNiche(population, capacity, finance):
    try:
        if population < 5 and capacity > 2 and finance > 5:
            return True
    except Exception:
        # if i get smegged by the data
        return False
    return False


import csv
import argparse
import os


def process_csv(csv_path):
    shelters = []
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"ur chiefing the path: {csv_path}")

    with open(csv_path, newline='', encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=1):
            #look through the numbers and exception if the nubmers are cheifed
            def p(field, default=0.0):
                try:
                    return float(row.get(field, default))
                except Exception:
                    return default

            finance = p('finance')
            supply = p('supply')
            population = p('population')
            urgency = p('urgency')
            capacity = p('capacity')

            score = calculateScore(finance, supply, population, urgency, capacity)
            niche = isNiche(population, capacity, finance)

            shelters.append({
                'rank_index': i,
                'name': row.get('name') or row.get('id') or f"row_{i}",
                'finance': finance,
                'supply': supply,
                'population': population,
                'urgency': urgency,
                'capacity': capacity,
                'score': score,
                'niche': niche,
                'raw': row,
            })

    # put niche stuff first
    shelters_sorted = sorted(shelters, key=lambda s: (not s['niche'], -s['score']))

    # rank them
    for idx, s in enumerate(shelters_sorted, start=1):
        s['rank'] = idx

    return shelters_sorted


def write_ranked_csv(shelters, out_path):
    fieldnames = ['rank', 'name', 'niche', 'score', 'finance', 'supply', 'population', 'urgency', 'capacity']
    with open(out_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for s in shelters:
            writer.writerow({k: s.get(k) for k in fieldnames})


def main():
    parser = argparse.ArgumentParser(description='Rank shelters from a CSV and prioritize niche shelters')
    parser.add_argument('csv', nargs='?', default='shelters.csv', help='Input CSV file path')
    parser.add_argument('-o', '--out', default='ranked_shelters.csv', help='Output CSV file path')
    args = parser.parse_args()

    shelters = process_csv(args.csv)
    write_ranked_csv(shelters, args.out)

    #print top 10 shelters
    print(f"Wrote ranked shelters to {args.out}. Top results:")
    for s in shelters[:10]:
        print(f"{s['rank']:>2}: {s['name']}  score={s['score']:.3f}  niche={s['niche']}")


if __name__ == '__main__':
    main()


