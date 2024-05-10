import os

import networkx
import obonet


def load_obo(data_folder, obofile):
    graph = obonet.read_obo(os.path.join(data_folder, obofile), ignore_obsolete=False)

    IGNORE_FIELDS = ['is_a'] # captured in parent field already

    for node in graph.nodes(data=True):
        children = list(graph.predecessors(node[0]))
        parents = list(graph.successors(node[0]))
        descendants = list(networkx.ancestors(graph, node[0]))
        ancestors = list(networkx.descendants(graph, node[0]))

        n = {
            '_id': node[0],
            'parents': parents, # predecessors/successors mean the opposite in networkx
            'children': children,
            'ancestors': ancestors, # networkx ancestors/descendants are opposite as well
            'descendants': descendants,
            'num_parents': len(parents),
            'num_children': len(children),
            'num_ancestors': len(ancestors),
            'num_descendants': len(descendants),
            **{k: v for k, v in node[1].items() if k not in IGNORE_FIELDS} # unpack fields like name, def, comment, synonym, xref, etc.
        }

        if 'def' in n and n['def'].startswith('"') and n['def'].endswith('" []'):
            n['def'] = n['def'][1:-4]

        if node[1].get('is_obsolete') == 'true':
            n['is_obsolete'] = True

        if 'replaced_by' in node[1]:
            n['replaced_by'] = node[1]['replaced_by'][0]

        if 'consider' in node[1]:
            n['consider'] = node[1]['consider']

        yield n
