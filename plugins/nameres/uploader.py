import copy
import functools

import biothings, config
from biothings.hub.dataload.uploader import BaseSourceUploader

from .static import BASE_URL
from .worker import upload_process


logger = config.logger


class NameResUploader(BaseSourceUploader):
    name = "nameres"
    __metadata__ = {"src_meta": {"url": BASE_URL}}

    async def update_data(self, batch_size: int, job_manager: JobManager = None):
        """
        Primary mover for uploading the data to our backend
        """
        pinfo = self.get_pinfo()
        pinfo["step"] = "update_data"
        got_error = False
        data_folder = copy.deepcopy(self.data_folder)
        temp_collection_name = copy.deepcopy(self.temp_collection_name)
        self.unprepare()

        job = await job_manager.defer_to_process(
            pinfo, functools.partial(upload_process, data_folder, temp_collection_name)
        )

        def uploaded(f):
            nonlocal got_error
            if not isinstance(f.result(), int):
                got_error = Exception(f"upload error (should have a int as returned value got {repr(f.result())}")

        job.add_done_callback(uploaded)
        await job
        if got_error:
            raise got_error

        self.switch_collection()
        self.clean_archived_collections()

    async def load(
        self,
        steps=("data", "post", "master", "clean"),
        force=False,
        batch_size=10000,
        job_manager=None,
        **kwargs,
    ):
        # force new arguments
        steps = ("data", "master", "clean")
        batch_size = 5000
        await super().load(steps, force, batch_size, job_manager, **kwargs)

    @classmethod
    def get_mapping(cls) -> dict:
        mapping = {
            "curie": {"type": "keyword"},
            "names": {"type": "text"},
            "types": {"types": "keyword"},
            "preferred_name": {"type": "text"},
            "shortest_name_length": {"types": "integer"},
            "clique_identifier_count": {"types": "integer"},
            "taxa": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
        }
        return mapping
