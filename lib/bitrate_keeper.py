class BitrateKeeper:
    def __init__(self):
        self.stores = {}

    def set_bitrate(self, task_name, filename, bitrate):
        stores = self.stores
        if not stores.get(task_name):
            stores[task_name] = {}
        task_store = stores[task_name]
        if not task_store.get(filename):
            task_store[filename] = []
        task_store[filename].append(bitrate)

    def get_bitrate_list(self, task_name, filename=None):
        if filename:
            return self.stores.get(task_name) and self.stores[task_name].get(filename)
        else:
            return self.stores.get(task_name)
