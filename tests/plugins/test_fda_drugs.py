"""
Tests for exercising the functionality and structure of the FDA drug plugin

FDA drug plugin implementation is an Advanced type plugin
"""

from pathlib import Path
import sys
from types import SimpleNamespace
import logging

import pytest


def test_fda_drug_data_loading(plugin_directory: Path, configuration: None):
    """
    Tests the full process for dumping and then uploading the data associated
    with the FDA drugs plugin
    """
    import biothings.hub

    from biothings import config
    from biothings.hub.dataload.dumper import DumperManager
    from biothings.hub.dataload.uploader import UploaderManager
    from biothings.hub.dataplugin.assistant import LocalAssistant
    from biothings.hub.dataplugin.manager import DataPluginManager
    from biothings.utils import hub_db
    from biothings.utils.workers import upload_worker

    plugin_name = "fda_drugs"
    plugin = plugin_directory.joinpath(plugin_name)
    sys.path.append(str(plugin.parent))
    assert plugin.exists()

    hub_db.setup(config)
    LocalAssistant.data_plugin_manager = DataPluginManager(job_manager=None)
    LocalAssistant.dumper_manager = DumperManager(job_manager=None)
    LocalAssistant.uploader_manager = UploaderManager(job_manager=None)

    assistant_url = f"local://{plugin_name}"
    assistant_instance = LocalAssistant(assistant_url)

    dp = hub_db.get_data_plugin()
    dp.remove({"_id": assistant_instance.plugin_name})
    plugin_entry = {
        "_id": assistant_instance.plugin_name,
        "plugin": {
            "url": assistant_url,
            "type": assistant_instance.plugin_type,
            "active": True,
        },
        "download": {"data_folder": str(Path(plugin))},
    }

    dp.insert_one(plugin_entry)

    p_loader = assistant_instance.loader
    p_loader.load_plugin()
    dumper_manager = p_loader.__class__.dumper_manager

    current_plugin = SimpleNamespace(
        plugin_name=plugin_name,
        data_plugin_dir=plugin,
        in_plugin_dir=plugin_name is None,
    )

    # Generate dumper instance
    dumper_class = dumper_manager[plugin_name][0]
    dumper_instance = dumper_class()
    current_plugin.dumper = dumper_instance
    current_plugin.dumper.prepare()

    current_plugin.dumper.create_todump_list(force=True)
    for item in current_plugin.dumper.to_dump:
        current_plugin.dumper.download(item["remote"], item["local"])

    current_plugin.dumper.steps = ["post"]
    current_plugin.dumper.post_dump()
    current_plugin.dumper.register_status("success")
    current_plugin.dumper.release_client()

    uploader_manager = assistant_instance.__class__.uploader_manager

    # Generate uploader instance
    uploader_classes = uploader_manager[plugin_name]
    if not isinstance(uploader_classes, list):
        uploader_classes = [uploader_classes]
    current_plugin.uploader_classes = uploader_classes

    for uploader_cls in current_plugin.uploader_classes:
        uploader = uploader_cls.create(db_conn_info="")
        uploader.make_temp_collection()
        uploader.prepare()

        assert Path(uploader.data_folder).exists()

        upload_worker(
            uploader.fullname,
            uploader.__class__.storage_class,
            uploader.load_data,
            uploader.temp_collection_name,
            10000,
            1,
            uploader.data_folder,
            db=uploader.db,
        )
        uploader.switch_collection()
        uploader.keep_archive = 3
        uploader.clean_archived_collections()

    dp.remove({"_id": current_plugin.plugin_name})
