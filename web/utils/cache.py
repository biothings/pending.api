from collections import OrderedDict


class LRUCache:
    """
    This LRUCache is to be used in `async def` functions that `functools.lru_cache` does not work in.

    Credit to https://www.geeksforgeeks.org/lru-cache-in-python-using-ordereddict/
    """
    def __init__(self, capacity: int):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        """
        Returns the cached value to the key in O(1); also move the key to the end to show that it was recently used.
        Return None if key is not cached.
        """
        if key not in self.cache:
            return None
        else:
            self.cache.move_to_end(key)
            return self.cache[key]

    def put(self, key, value):
        """
        Add / update the key by conventional methods; also move the key to the end to show that it was recently used.
        Also check whether the length of the underlying ordered dictionary has exceeded our capacity.
        If so, remove the first key (least recently used)
        """
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)
