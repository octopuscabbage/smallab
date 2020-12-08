from collections import defaultdict

from smallab.specification_hashing import specification_hash


class DiffNamer():
    def __init__(self, specifications):
        self.keys = self.specification_keys_that_are_not_constant(specifications)
        self.extended_keys = []

    def specification_keys_that_are_not_constant(self, specifications):
        specification_params_dict = defaultdict(list)
        for key, value in specifications[0].items():
            specification_params_dict[key].append(value)

        for specification in specifications[1:]:
            for key, value in specification.items():
                if key in specification_params_dict:
                    if value not in specification_params_dict[key]:
                        specification_params_dict[key].append(value)
                # In this case, this specification has added a key
                else:
                    specification_params_dict[key].append(None)
                    specification_params_dict[key].append(value)
        self.specification_params_dict = specification_params_dict
        keys = []
        for key, values in specification_params_dict.items():
            if len(values) >= 2:
                keys.append(key)
        if keys == []:
            keys = specification_params_dict.keys()
        return sorted(keys)

    def __gen_name(self, keys, specification):
        name = []
        for key in keys:
            name.append(str(key) + ":" + str(specification[key]))
        name = "_".join(name)
        if len(
                name) >= 250:  # This is the maximum file length for windows and unix, doesn't take into account full path length
            return specification_hash(specification)
        else:
            return name

    def get_name(self, specification):
        return self.__gen_name(self.keys, specification)

    def get_extended_name(self, specification):
        return self.__gen_name(self.keys + self.extended_keys, specification)

    def extend_name(self, specification):
        for key in specification.keys():
            if key not in self.keys and key not in self.extended_keys:
                self.extended_keys.append(key)