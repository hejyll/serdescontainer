import abc
import dataclasses
import datetime as dt
import enum
import json
import re
import typing
from pathlib import Path
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

try:
    import yaml

    installed_pyyaml = True
except:
    installed_pyyaml = False

BaseContainerType = TypeVar("BaseContainerType", bound="BaseContainer")


def _to_dict(obj: Any, **kwargs) -> Union[Any, Dict[str, Any]]:
    unserialized_types = kwargs.get("unserialized_types", [])
    if type(obj) in unserialized_types:
        return obj

    serialize = kwargs.get("serialize", False)
    if dataclasses.is_dataclass(obj):
        return _to_dict(dataclasses.asdict(obj), **kwargs)
    elif hasattr(obj, "to_dict"):
        return obj.to_dict()
    elif isinstance(obj, list):
        return [_to_dict(x, **kwargs) for x in obj]
    elif isinstance(obj, tuple):
        return tuple(_to_dict(x, **kwargs) for x in obj)
    elif isinstance(obj, dict):
        return {_to_dict(k, **kwargs): _to_dict(v, **kwargs) for k, v in obj.items()}
    if serialize:
        if isinstance(obj, enum.Enum):
            return obj.value
        elif isinstance(obj, dt.datetime):
            datetime_format = kwargs.get("datetime_format", None)
            return obj.strftime(datetime_format) if datetime_format else str(obj)
        else:
            try:
                json.dumps(obj)
            except TypeError:
                raise TypeError(f"{type(obj)} is not supported type: {obj}")
    return obj


def _get_class_name(type: Any) -> str:
    # e.g. "<class 'Hoge'>", "<enum 'FugaEnum'>"
    return re.match(r"<.+? '(.+?)'>", str(type)).groups()[0]


def _instantiate_type(type: str, custom_classes: List[Any]) -> Any:
    try:
        return eval(f"typing.{type}")
    except:
        try:
            return eval(type)
        except:
            for custom_class in custom_classes:
                class_name = _get_class_name(custom_class)
                base_name = class_name.split(".")[-1]
                if type == base_name:
                    return custom_class
            return type


def _from_dict(obj: Any, ref_type: Any, **kwargs) -> Any:
    if isinstance(ref_type, str):
        if ref_type.startswith("Optional["):
            # remove 'Optional[]'
            ref_type = ref_type.replace("Optional[", "", 1)[:-1]
            return _from_dict(obj, ref_type, **kwargs)

        # TODO: automatic retrieval of custom classes without user assignment
        custom_classes = kwargs.get("custom_classes", [])
        ref_type = _instantiate_type(ref_type, custom_classes)

    if obj is None:
        return None
    elif isinstance(ref_type, typing._GenericAlias):
        type_args = list(ref_type.__args__)
        if ref_type.__origin__ == list:
            return [_from_dict(value, type_args[0], **kwargs) for value in obj]
        elif ref_type.__origin__ == tuple:
            if len(type_args) == 1:
                type_args = [type_args[0]] * len(obj)
            elif len(type_args) == 2 and type_args[-1] == Ellipsis:
                type_args = [type_args[0]] * len(obj)
            if len(type_args) != len(obj):
                raise TypeError(
                    f"tuple length is not match: typing ({ref_type}) vs values {obj}"
                )
            return tuple(
                _from_dict(value, type_arg, **kwargs)
                for type_arg, value in zip(type_args, obj)
            )
        elif ref_type.__origin__ == dict:
            k_type, v_type = type_args
            return {
                _from_dict(k, k_type, **kwargs): _from_dict(v, v_type, **kwargs)
                for k, v in obj.items()
            }
    elif ref_type == dt.datetime and isinstance(obj, str):
        datetime_format = kwargs.get("datetime_format", None)
        if datetime_format:
            return dt.datetime.strptime(obj, None, datetime_format)
        else:
            return dt.datetime.fromisoformat(obj)
    elif ref_type.__class__.__name__ == "EnumMeta":
        return ref_type(obj)
    elif dataclasses.is_dataclass(ref_type):
        if isinstance(obj, dict):
            return _from_dict(ref_type(**obj), None, **kwargs)
    elif dataclasses.is_dataclass(obj):
        for field in dataclasses.fields(obj):
            value = getattr(obj, field.name)
            if type(value) != field.type:
                value = _from_dict(value, field.type, **kwargs)
                setattr(obj, field.name, value)
    return obj


class BaseContainer(abc.ABC, Generic[BaseContainerType]):

    def custom_classes() -> List[Any]:
        """Specifies user-defined classes used in attribute for `from_dict`.

        Returns:
            list of classes: user-defined classes
        """
        return []

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        datetime_format: Optional[str] = None,
    ) -> BaseContainerType:
        """Convert dict to user-defined class object that inherits from BaseContainer.
        Nested dict objects are also converted to appropriate class.

        Args:
            data (dict): Dict object to be converted.
            datetime_format (str): Format for converting datetime with `datetime.strptime`.
                If not specified, it is converted by iso-format.

        Returns:
            object: Converted user-defined class object.
        """
        if hasattr(cls, "__dataclass_fields__"):
            return _from_dict(
                data,
                cls,
                custom_classes=cls.custom_classes(),
                datetime_format=datetime_format,
            )
        raise NotImplementedError

    @classmethod
    def from_json(
        cls,
        path: Union[str, Path],
        datetime_format: Optional[str] = None,
    ) -> BaseContainerType:
        """Convert JSON file to user-defined class object that inherits from BaseContainer.

        Args:
            path (str or `pathlib.Path`): Input JSON file path.
            datetime_format (str): Format for converting datetime with `datetime.strptime`.
                If not specified, it is converted by iso-format.

        Returns:
            object: Converted user-defined class object.
        """
        with open(str(path), "r") as fh:
            data = json.load(fh)
        return cls.from_dict(data, datetime_format=datetime_format)

    @classmethod
    def from_yaml(
        cls,
        path: Union[str, Path],
        datetime_format: Optional[str] = None,
    ) -> BaseContainerType:
        """Convert YAML file to user-defined class object that inherits from BaseContainer.

        Args:
            path (str or `pathlib.Path`): Input YAML file path.
            datetime_format (str): Format for converting datetime with `datetime.strptime`.
                If not specified, it is converted by iso-format.

        Returns:
            object: Converted user-defined class object.
        """
        if not installed_pyyaml:
            raise RuntimeError("PyYAML is not installed")
        with open(str(path), "r") as fh:
            data = yaml.safe_load(fh)
        return cls.from_dict(data, datetime_format=datetime_format)

    @classmethod
    def from_file(
        cls,
        path: Union[str, Path],
        datetime_format: Optional[str] = None,
    ) -> BaseContainerType:
        """Convert YAML file to user-defined class object that inherits from BaseContainer.

        Args:
            path (str or `pathlib.Path`): Input file path.
            datetime_format (str): Format for converting datetime with `datetime.strptime`.
                If not specified, it is converted by iso-format.

        Returns:
            object: Converted user-defined class object.
        """
        path = Path(path)
        if path.suffix == ".json":
            return cls.from_json(path, datetime_format=datetime_format)
        elif path.suffix in [".yaml", ".yml"]:
            return cls.from_yaml(path, datetime_format=datetime_format)
        else:
            raise ValueError(f"{path.suffix} is not supported file format")

    def to_dict(
        self,
        serialize: bool = False,
        ignore_none_fields: bool = False,
        unserialized_types: List[Any] = [],
        datetime_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Convert user-defined class object that inherits from BaseContainer to dict.

        Args:
            serialize (bool): Whether the leaf object should be serializable or not.
            unserialized_types (type of list): Specify types not to serialize even if serialize=True.
                e.g. if serializing for MongoDB, you `datetime.datetime` should not be serialized.
            ignore_none_fields (bool): Fields with the value None are not output.
            datetime_format (str): Format for converting datetime with `datetime.stfptime`.
                If not specified, it is converted by iso-format.

        Returns:
            dict: Converted dict object.
        """
        ret = _to_dict(
            self,
            serialize=serialize,
            unserialized_types=unserialized_types,
            datetime_format=datetime_format,
        )
        if ignore_none_fields:
            ret = {key: value for key, value in ret.items() if value is not None}
        return ret

    def to_json(
        self,
        path: Union[str, Path],
        ignore_none_fields: bool = False,
        datetime_format: Optional[str] = None,
        indent: Optional[int] = None,
        ensure_ascii: bool = True,
    ) -> None:
        """Convert user-defined class object that inherits from BaseContainer to JSON file.

        Args:
            path (str or `pathlib.Path`): Output JSON file path.
            ignore_none_fields (bool): Fields with the value None are not output.
            datetime_format (str): Format for converting datetime with `datetime.stfptime`.
                If not specified, it is converted by iso-format.
            indent (int): Same as `indent` of `json.dump`.
            ensure_ascii (bool): Same as `ensure_ascii` of `json.dump`.
        """
        data = self.to_dict(
            serialize=True,
            ignore_none_fields=ignore_none_fields,
            datetime_format=datetime_format,
        )
        with open(str(path), "w") as fp:
            json.dump(data, fp, indent=indent, ensure_ascii=ensure_ascii)

    def to_yaml(
        self,
        path: Union[str, Path],
        ignore_none_fields: bool = False,
        datetime_format: Optional[str] = None,
    ) -> None:
        """Convert user-defined class object that inherits from BaseContainer to YAML file.

        Args:
            path (str or `pathlib.Path`): Output YAML file path.
            ignore_none_fields (bool): Fields with the value None are not output.
            datetime_format (str): Format for converting datetime with `datetime.stfptime`.
                If not specified, it is converted by iso-format.
        """
        if not installed_pyyaml:
            raise RuntimeError("PyYAML is not installed")
        data = self.to_dict(
            serialize=True,
            ignore_none_fields=ignore_none_fields,
            datetime_format=datetime_format,
        )
        with open(str(path), "w") as fp:
            yaml.safe_dump(data, fp)
