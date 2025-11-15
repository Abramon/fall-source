import os
from typing import Type, TypeVar, Union

T = TypeVar('T')

def _cast_to_bool(value: str) -> bool:
    """Casts a string to a boolean, handling common truthy/falsy values."""
    val_lower = value.lower().strip()
    if val_lower in ('true', '1', 't', 'y', 'yes'):
        return True
    if val_lower in ('false', '0', 'f', 'n', 'no'):
        return False
    raise ValueError(f"Cannot cast '{value}' to bool.")

def load_env_var(
    name: str,
    default: T = None,
    cast_to: Type[T] = str
) -> Union[T, None]:
    """
    Loads an environment variable, with a default value and type casting.

    Args:
        name (str): The name of the environment variable.
        default (T, optional): The default value to return if the variable
                               is not set. Defaults to None.
        cast_to (Type[T], optional): The type to cast the variable value to.
                                     Supports str, int, float, and bool.
                                     Defaults to str.

    Returns:
        Union[T, None]: The value of the environment variable, cast to the
                        specified type, or the default value.

    Raises:
        ValueError: If the value cannot be cast to the specified type.
    """
    value = os.environ.get(name)

    if value is None:
        return default

    try:
        if cast_to is bool:
            # Special handling for boolean values
            return _cast_to_bool(value)
        return cast_to(value)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"Failed to cast environment variable '{name}' with value "
            f"'{value}' to type '{cast_to.__name__}'."
        ) from e
