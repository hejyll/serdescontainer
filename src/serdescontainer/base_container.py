import abc
import dataclasses
import datetime as dt
import enum
import json
from pathlib import Path
from typing import Any, Dict, Generic, Optional, TypeVar, Union

try:
    import yaml

    installed_pyyaml = True
except:
    installed_pyyaml = False

BaseContainerType = TypeVar("BaseContainerType", bound="BaseContainer")


def _to_dict(obj: Any, **kwargs) -> Union[Any, Dict[str, Any]]:
    serializable = kwargs.get("serializable", False)
    if dataclasses.is_dataclass(obj):
        return _to_dict(dataclasses.asdict(obj), **kwargs)
    elif hasattr(obj, "to_dict"):
        return obj.to_dict()
    elif isinstance(obj, list):
        return [_to_dict(x, **kwargs) for x in obj]
    elif isinstance(obj, tuple):
        return (_to_dict(x, **kwargs) for x in obj)
    elif isinstance(obj, dict):
        return {k: _to_dict(v, **kwargs) for k, v in obj.items()}
    if serializable:
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


def _deserialize(
    obj: Any,
    datetime_format: Optional[str] = None,
) -> Any:
    if not dataclasses.is_dataclass(obj):
        raise TypeError(f"{type(obj)} is not dataclass")
    for field in dataclasses.fields(obj):
        value = getattr(obj, field.name)
        if type(value) != field.type:
            if field.type == dt.datetime and isinstance(value, str):
                if datetime_format:
                    value = dt.datetime.strptime(value, datetime_format)
                else:
                    value = dt.datetime.fromisoformat(value)
            elif dataclasses.is_dataclass(field.type):
                value = _deserialize(field.type(**value))
            elif field.type.__class__.__name__ == "EnumMeta":
                value = field.type(value)
            setattr(obj, field.name, value)
    return obj


class BaseContainer(abc.ABC, Generic[BaseContainerType]):

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        datetime_format: Optional[str] = None,
    ) -> BaseContainerType:
        if hasattr(cls, "__dataclass_fields__"):
            return _deserialize(cls(**data), datetime_format=datetime_format)
        raise NotImplementedError

    @classmethod
    def from_json(cls, filename: Union[str, Path]) -> BaseContainerType:
        with open(str(filename), "r") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    @classmethod
    def from_yaml(cls, filename: Union[str, Path]) -> BaseContainerType:
        with open(str(filename), "r") as fh:
            data = yaml.safe_load(fh)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, filename: Union[str, Path]) -> BaseContainerType:
        filename = Path(filename)
        if filename.suffix == ".json":
            return cls.from_json(filename)
        elif filename.suffix in [".yaml", ".yml"]:
            return cls.from_yaml(filename)
        else:
            raise ValueError(f"{filename.suffix} is not supported file format")

    def to_dict(
        self,
        serializable: bool = False,
        datetime_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        return _to_dict(
            self,
            serializable=serializable,
            datetime_format=datetime_format,
        )

    def to_json(
        self,
        path: Union[str, Path],
        datetime_format: Optional[str] = None,
        indent: Optional[int] = None,
        ensure_ascii: bool = True,
    ) -> None:
        data = self.to_dict(serializable=True, datetime_format=datetime_format)
        with open(str(path), "w") as fp:
            json.dump(data, fp, indent=indent, ensure_ascii=ensure_ascii)

    def to_yaml(
        self,
        path: Union[str, Path],
        datetime_format: Optional[str] = None,
    ) -> None:
        if not installed_pyyaml:
            raise RuntimeError("PyYAML is not installed")
        data = self.to_dict(serializable=True, datetime_format=datetime_format)
        with open(str(path), "w") as fp:
            yaml.safe_dump(data, fp)
