import abc
import json


class UMLSResourceClient(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def open_resource(self):
        raise NotImplementedError

    @abc.abstractmethod
    def close_resource(self):
        raise NotImplementedError

    @abc.abstractmethod
    def query(self, keyword: str):
        raise NotImplementedError

    # No need to implement a context manager
    # Guess the file/client handler would be open like a daemon

    # if RAM usage of UMLSJsonFileClient is high, we can consider sqlite, redis, or mongodb


class UMLSJsonFileClient(UMLSResourceClient):
    def __init__(self, filepath):
        self.filepath = filepath
        self.handler = None
        self.data = None

    def open_resource(self):
        if self.handler is None:
            self.handler = open(self.filepath, "r")

        if self.data is None:
            self.data = json.load(self.handler)

    def close_resource(self):
        if self.handler is not None:
            self.handler.close()

        if self.data is not None:
            self.data = None

    def query(self, keyword: str):
        return self.data.get(keyword, None)


class UMLSResourceManager:
    def __init__(self):
        # <resource_name: str, resource_obj: UMLSResource>
        self.client_map = dict()

    def register(self, resource_name: str, resource_client: UMLSResourceClient):
        self.client_map[resource_name] = resource_client

    def open_resources(self):
        for client in self.client_map.values():
            client.open_resource()

    def close_resources(self):
        for client in self.client_map.values():
            client.close_resource()

    def resource_names(self):
        return list(self.client_map)

    def get_resource_client(self, resource_name: str) -> UMLSResourceClient:
        return self.client_map.get(resource_name, None)

    def query(self, resource_name: str, keyword: str):
        client = self.get_resource_client(resource_name)
        if client is None:
            raise ValueError(f"Cannot find client for resource '{resource_name}'.")

        resp = client.query(keyword)
        return resp
