"""
coldhot indexer
two collections: mv_cold  (very large, not much changes)
                 mv_hot   (small, often updated)


step 1: index mv_cold as normal
step 2: loop through mv_hot, merge docs based on _id, then update ES index, do it in 1000 per batch


KGX Indxer 1:
two collections: nodes
                 edges

step 1: index nodes as normal
step 2: loop through edges, add "in_edges", and "out_edges" field into nodes index, then update ES index, do it in 1000 per batch


KGX Indxer 2:
two collections: nodes
                 edges

step 1: index edges as normal
step 2: loop through nodes, expand subject and object field (based on node _id and nodes)
        into edges index, then update ES index, do it in 1000 per batch
"""

from biothings.hub.dataindex.indexer import Indexer
from biothings.hub.manager import JobManager

from biothings.hub.dataindex.indexer import _BuildDoc, Step


class PendingHubIndexer(Indexer):
    """
    Indexer specific to the PendingHub

    Wrapper around the Indexer parent
    """


class RTXKG2Indexer:
    """
    Indexer instance for translating MongoDB -> Elasticsearch documents

    Index's in 2 passes similar to the ColdHotIndexer in the biothings SDK

    >>> 1st pass: Index the edges normally
    >>> 2nd pass: Iterate over the nodes and expand edge subject and
                  object fields based off node properties
    """

    INDEXER = BasePendingHubIndexer

    def __init__(self, build_doc, indexer_env, index_name):
        edge_build_doc = _BuildDoc(build_doc)
        node_build_doc = edge_build_doc.extract_coldbuild()

        self.edge_indexer = self.INDEXER(edge_build_doc, indexer_env, index_name)
        self.node_indexer = self.INDEXER(node_build_doc, indexer_env, self.edge_indexer.es_index_name)

    async def index(
        self,
        job_manager: JobManager,
        batch_size: int = 10000,
        steps: tuple[str] = ("pre", "index", "post"),
        ids=None,
        mode=None,
        **kwargs,
    ):
        """
        step 1: index edges as normal
        step 2: loop through nodes, expand subject and object field (based on node _id and nodes)
                into edges index, then update ES index, do it in 1000 per batch
        """
        result = []

        edge_task = self.edge_indexer.index(
            job_manager,
            steps=set(Step.order(steps)) & {"pre", "index"},
            batch_size=batch_size,
            ids=ids,
            mode=mode,
        )
        edge_result = await edge_task
        result.append(edge_result)

        node_task = self.node_indexer.index(
            job_manager,
            steps=set(Step.order(steps)) & {"index", "post"},
            batch_size=batch_size,
            ids=ids,
            mode="merge",
        )
        node_result = await node_task
        result.append(node_result)
        return result
