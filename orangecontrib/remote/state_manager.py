import os
import pickle


class StateManager:
    __id__ = None

    storage_path = os.path.join(os.path.dirname(__file__), 'saved_states')
    if not os.path.exists(storage_path):
        os.mkdir(storage_path)

    @classmethod
    def get_state(cls, id):
        try:
            fn = os.path.join(cls.storage_path, id)
            with open(fn, 'rb') as f:
                return pickle.load(f)
        except (IOError, pickle.UnpicklingError):
            pass

    @classmethod
    def save_state(cls, state, id=None):
        if id is None:
            id = cls.__id__

        if id is None:
            raise ValueError("save_state was called outside worker, "
                             "but no id was provided")

        fn = os.path.join(cls.storage_path, id)
        tmpfn = fn + '.new'
        with open(tmpfn, 'wb') as f:
            pickle.dump(state, f, -1)
        os.replace(tmpfn, fn)

    @classmethod
    def delete_state(cls, id):
        saved_state = os.path.join(cls.storage_path, id)
        if os.path.exists(saved_state):
            os.remove(saved_state)

    @classmethod
    def set_id(cls, id):
        cls.__id__ = id
