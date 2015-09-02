class DummyClass:
    def a(self):
        return "a"

    b = "b"

    def __str__(self):
        return "test"

    def annotated_method(self) -> str:
        pass

    @classmethod
    def annotated_class_method(cls) -> str:
        pass


class DummyIterable:
    members = ["a"]

    def __init__(self, members):
        self.members = members

    def __len__(self):
        return len(self.members)

    def __getitem__(self, item):
        return self.members[item]

    def __iter__(self):
        for x in self.members:
            yield x

    def __str__(self):
        return str(self.members)
