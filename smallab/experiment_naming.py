from collections import defaultdict


class DiffNamer():
    def __init__(self):
        pass

    def specification_keys_that_are_not_constant(self, specifications):
        specification_params_dict = defaultdict(set)
        for key,value in specifications[0]:
            specification_params_dict[key].add(value)
        for specification in specifications[1:]:
            for key,value in specification:
                if key in specification_params_dict:
                    specification_params_dict[key].add(value)
                #In this case, this specification has added a key
                else:
                    specification_params_dict[key].add(None)
                    specification_params_dict[key].add(value)
        keys = []
        for key, values in specification_params_dict.items():
            if len(values) >= 2:
                keys.append(key)
        return key




