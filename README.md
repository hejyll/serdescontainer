# Serializable/Deserializable container

## Setup

```bash
pip install git+https://github.com/hejyll/serdescontainer
```

## Usage

Objects of classes inheriting from `serdescontainer.BaseContainer` can be easily serialized/deserialized by using methods such as `to_dict` and `from_dict` as in the following sample.

```python
#!/usr/bin/env python3
import datetime as dt
import enum
import json
from dataclasses import dataclass
from pprint import pprint
from typing import List, Dict

from serdescontainer import BaseContainer


class Fruit(enum.IntEnum):
    APPLE: int = 0
    BANANA: int = 1


class Area(enum.Enum):
    AREA1: str = "area1"
    AREA2: str = "area2"


@dataclass
class State:
    fruit: Fruit
    expiration_datetime: dt.datetime
    storage: Area


@dataclass
class Manager:
    name: str
    division: str


@dataclass
class Management(BaseContainer):
    states: List[State]
    description: str
    area_manager: Dict[Area, Manager]


print("# Construct object")
m = Management(
    [
        State(
            Fruit.APPLE, dt.datetime.fromisoformat("2024-06-05 06:00:00"), Area.AREA2
        ),
        State(
            Fruit.BANANA, dt.datetime.fromisoformat("2024-06-11 18:00:00"), Area.AREA1
        ),
    ],
    "fruit management",
    {
        Area.AREA1: Manager("Bob", "Div1"),
        Area.AREA2: Manager("Jhon", "Div2"),
    },
)
pprint(m)
# Management(states=[State(fruit=<Fruit.APPLE: 0>,
#                          expiration_datetime=datetime.datetime(2024, 6, 5, 6, 0),
#                          storage=<Area.AREA2: 'area2'>),
#                    State(fruit=<Fruit.BANANA: 1>,
#                          expiration_datetime=datetime.datetime(2024, 6, 11, 18, 0),
#                          storage=<Area.AREA1: 'area1'>)],
#            description='fruit management',
#            area_manager={<Area.AREA2: 'area2'>: Manager(name='Jhon',
#                                                         division='Div2'),
#                          <Area.AREA1: 'area1'>: Manager(name='Bob',
#                                                         division='Div1')})

# Convert user-defined class object that inherits from BaseContainer to dict.
# Leaf objects are not serializable (e.g. datetime.datetime objs are still a Python object)
print("\n# To dict")
pprint(m.to_dict(serialize=False))
# {'area_manager': {<Area.AREA2: 'area2'>: {'division': 'Div2', 'name': 'Jhon'},
#                   <Area.AREA1: 'area1'>: {'division': 'Div1', 'name': 'Bob'}},
#  'description': 'fruit management',
#  'states': [{'expiration_datetime': datetime.datetime(2024, 6, 5, 6, 0),
#              'fruit': <Fruit.APPLE: 0>,
#              'storage': <Area.AREA2: 'area2'>},
#             {'expiration_datetime': datetime.datetime(2024, 6, 11, 18, 0),
#              'fruit': <Fruit.BANANA: 1>,
#              'storage': <Area.AREA1: 'area1'>}]}

# Convert user-defined class object that inherits from BaseContainer to serializable dict.
# Leaf objects can also be serialized (e.g. datetime.datetime are converted to str)
print("\n# To serializable dict")
serialized_m = m.to_dict(serialize=True)
pprint(serialized_m)
# {'area_manager': {'area1': {'division': 'Div1', 'name': 'Bob'},
#                   'area2': {'division': 'Div2', 'name': 'Jhon'}},
#  'description': 'fruit management',
#  'states': [{'expiration_datetime': '2024-06-05 06:00:00',
#              'fruit': 0,
#              'storage': 'area2'},
#             {'expiration_datetime': '2024-06-11 18:00:00',
#              'fruit': 1,
#              'storage': 'area1'}]}

# Convert dict to user-defined class object that inherits from BaseContainer.
print("\n# From serializable dict")
restored_m = Management.from_dict(serialized_m)
if m == restored_m:
    print("Successfully restored from serializable dict")

# Convert JSON file to user-defined class object that inherits from BaseContainer.
print("\n# From JSON file")
with open("a.json", "w") as fp:
    json.dump(serialized_m, fp)
restored_m = Management.from_json("a.json")
if m == restored_m:
    print("Successfully restored from JSON file")
```

## License

These codes are licensed under CC0.

[![CC0](http://i.creativecommons.org/p/zero/1.0/88x31.png "CC0")](http://creativecommons.org/publicdomain/zero/1.0/deed.ja)
