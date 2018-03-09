import lxml.etree as etree


class MessageData(object):

    def __init__(self, raw):
        self.raw = raw
        self._root = None

    def get_raw_data(self):
        return self.raw.data

    @property
    def root(self):
        if self._root is None:
            self._root = etree.fromstring(self.get_raw_data())
        return self._root

    def first_with_n_prop(self, prop_name):
        lst = self.root.findall(f".//*[@N='{prop_name}']")
        return lst[0] if lst else None

    def __str__(self):
        try:
            return self.raw.data
        except Exception:
            return 'MessageData'