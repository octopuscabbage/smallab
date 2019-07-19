import itertools
import copy
import typing

class SpecificationGenerator():

    def generate(self, generation_specification: typing.Dict) -> typing.List[typing.Dict]:
        '''
        This class takes a generation specification and outputs a list of specifications based on it.
        The format is as follows
        {
            "a": [1,2,3]
            "b": [1,2]
        }

        Generates

        [{
            "a": 1,
            "b": 1
        },
        {
            "a": 2,
            "b": 1
        },
        {
            "a": 3,
            "b": 1
        },
        {
            "a": 1,
            "b": 2
        },
        {
            "a": 2,
            "b": 2
        },
        {
            "a": 3,
            "b": 2
        }
        ]

        if you want key with a list value put it in double brackets ie
        {
            "a": [[1,2,3]]
        }
        '''
        iterators = []
        for key,value in generation_specification.items():
            if isinstance(value,list):
                iterators.append(list(map(lambda x: (key,x),value)))
        specifications = []
        for updates in itertools.product(*iterators):
            cur_j = copy.deepcopy(generation_specification)
            for update_key, update_value in updates:
                cur_j[update_key] = update_value
            specifications.append(cur_j)
        return specifications
