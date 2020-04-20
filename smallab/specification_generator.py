import collections
import itertools
import json
import typing

import copy


class SpecificationGenerator:
    def generate(self, generation_specification: typing.Dict) -> typing.List[collections.OrderedDict]:
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
        generation_specification = collections.OrderedDict(sorted(generation_specification.items()))
        iterators = []
        for key, value in generation_specification.items():
            if isinstance(value, list):
                iterators.append(list(map(lambda x: (key, x), value)))
        specifications = []
        for updates in itertools.product(*iterators):
            cur_j = copy.deepcopy(generation_specification)
            for update_key, update_value in updates:
                cur_j[update_key] = update_value
            specifications.append(cur_j)
        return specifications

    def from_json_file(self, fp: typing.AnyStr) -> typing.List[typing.Dict]:
        with open(fp) as f:
            j = json.load(f)
        if isinstance(j, list):
            out = []
            for specification in j:
                out.extend(self.generate(specification))
            return out
        else:
            return self.generate(j)


class MultiComputerGenerator(SpecificationGenerator):
    def __init__(self, computer_number, number_of_computers):
        '''
        Divides the specification across multiple computers by giving each computer the i*computer_numberth specification

        If you have 3 computers then the computer numbers would be 0,1,2 and the number_of_computers would be 3

        :param computer_number: 0 indexed number which to assign this computer (MUST NOT OVERLAP WITH ANOTHER COMPUTER)
        :param number_of_computers: The total number of computers which are being used
        '''
        assert computer_number < number_of_computers, "Computer number must be less than number of computers"

        self.computer_number = computer_number
        self.number_of_computers = number_of_computers

    def shard(self, l: typing.List) -> typing.List:
        return l[self.computer_number::self.number_of_computers]

    def generate(self, generation_specification: typing.Dict) -> typing.List[typing.Dict]:
        return self.shard(super().generate(generation_specification))
