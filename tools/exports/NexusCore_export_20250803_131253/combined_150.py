
# === NexusCore/tools\exports\export_20250803_114325\combined_110.py ===

# === NexusCore/openenv\Lib\site-packages\huggingface_hub\serialization\_torch.py ===
# Copyright 2024 The HuggingFace Team. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Contains pytorch-specific helpers."""

import importlib
import json
import os
import re
from collections import defaultdict, namedtuple
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, NamedTuple, Optional, Set, Tuple, Union

from packaging import version

from .. import constants, logging
from ._base import MAX_SHARD_SIZE, StateDictSplit, split_state_dict_into_shards_factory


logger = logging.get_logger(__file__)

if TYPE_CHECKING:
    import torch

# SAVING


def save_torch_model(
    model: "torch.nn.Module",
    save_directory: Union[str, Path],
    *,
    filename_pattern: Optional[str] = None,
    force_contiguous: bool = True,
    max_shard_size: Union[int, str] = MAX_SHARD_SIZE,
    metadata: Optional[Dict[str, str]] = None,
    safe_serialization: bool = True,
    is_main_process: bool = True,
    shared_tensors_to_discard: Optional[List[str]] = None,
):
    """
    Saves a given torch model to disk, handling sharding and shared tensors issues.

    See also [`save_torch_state_dict`] to save a state dict with more flexibility.

    For more information about tensor sharing, check out [this guide](https://huggingface.co/docs/safetensors/torch_shared_tensors).

    The model state dictionary is split into shards so that each shard is smaller than a given size. The shards are
    saved in the `save_directory` with the given `filename_pattern`. If the model is too big to fit in a single shard,
    an index file is saved in the `save_directory` to indicate where each tensor is saved. This helper uses
    [`split_torch_state_dict_into_shards`] under the hood. If `safe_serialization` is `True`, the shards are saved as
    safetensors (the default). Otherwise, the shards are saved as pickle.

    Before saving the model, the `save_directory` is cleaned from any previous shard files.

    <Tip warning={true}>

    If one of the model's tensor is bigger than `max_shard_size`, it will end up in its own shard which will have a
    size greater than `max_shard_size`.

    </Tip>

    <Tip warning={true}>

    If your model is a `transformers.PreTrainedModel`, you should pass `model._tied_weights_keys` as `shared_tensors_to_discard` to properly handle shared tensors saving. This ensures the correct duplicate tensors are discarded during saving.

    </Tip>

    Args:
        model (`torch.nn.Module`):
            The model to save on disk.
        save_directory (`str` or `Path`):
            The directory in which the model will be saved.
        filename_pattern (`str`, *optional*):
            The pattern to generate the files names in which the model will be saved. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
            Defaults to `"model{suffix}.safetensors"` or `pytorch_model{suffix}.bin` depending on `safe_serialization`
            parameter.
        force_contiguous (`boolean`, *optional*):
            Forcing the state_dict to be saved as contiguous tensors. This has no effect on the correctness of the
            model, but it could potentially change performance if the layout of the tensor was chosen specifically for
            that reason. Defaults to `True`.
        max_shard_size (`int` or `str`, *optional*):
            The maximum size of each shard, in bytes. Defaults to 5GB.
        metadata (`Dict[str, str]`, *optional*):
            Extra information to save along with the model. Some metadata will be added for each dropped tensors.
            This information will not be enough to recover the entire shared structure but might help understanding
            things.
        safe_serialization (`bool`, *optional*):
            Whether to save as safetensors, which is the default behavior. If `False`, the shards are saved as pickle.
            Safe serialization is recommended for security reasons. Saving as pickle is deprecated and will be removed
            in a future version.
        is_main_process (`bool`, *optional*):
            Whether the process calling this is the main process or not. Useful when in distributed training like
            TPUs and need to call this function from all processes. In this case, set `is_main_process=True` only on
            the main process to avoid race conditions. Defaults to True.
        shared_tensors_to_discard (`List[str]`, *optional*):
            List of tensor names to drop when saving shared tensors. If not provided and shared tensors are
            detected, it will drop the first name alphabetically.

    Example:

    ```py
    >>> from huggingface_hub import save_torch_model
    >>> model = ... # A PyTorch model

    # Save state dict to "path/to/folder". The model will be split into shards of 5GB each and saved as safetensors.
    >>> save_torch_model(model, "path/to/folder")

    # Load model back
    >>> from huggingface_hub import load_torch_model  # TODO
    >>> load_torch_model(model, "path/to/folder")
    >>>
    ```
    """
    save_torch_state_dict(
        state_dict=model.state_dict(),
        filename_pattern=filename_pattern,
        force_contiguous=force_contiguous,
        max_shard_size=max_shard_size,
        metadata=metadata,
        safe_serialization=safe_serialization,
        save_directory=save_directory,
        is_main_process=is_main_process,
        shared_tensors_to_discard=shared_tensors_to_discard,
    )


def save_torch_state_dict(
    state_dict: Dict[str, "torch.Tensor"],
    save_directory: Union[str, Path],
    *,
    filename_pattern: Optional[str] = None,
    force_contiguous: bool = True,
    max_shard_size: Union[int, str] = MAX_SHARD_SIZE,
    metadata: Optional[Dict[str, str]] = None,
    safe_serialization: bool = True,
    is_main_process: bool = True,
    shared_tensors_to_discard: Optional[List[str]] = None,
) -> None:
    """
    Save a model state dictionary to the disk, handling sharding and shared tensors issues.

    See also [`save_torch_model`] to directly save a PyTorch model.

    For more information about tensor sharing, check out [this guide](https://huggingface.co/docs/safetensors/torch_shared_tensors).

    The model state dictionary is split into shards so that each shard is smaller than a given size. The shards are
    saved in the `save_directory` with the given `filename_pattern`. If the model is too big to fit in a single shard,
    an index file is saved in the `save_directory` to indicate where each tensor is saved. This helper uses
    [`split_torch_state_dict_into_shards`] under the hood. If `safe_serialization` is `True`, the shards are saved as
    safetensors (the default). Otherwise, the shards are saved as pickle.

    Before saving the model, the `save_directory` is cleaned from any previous shard files.

    <Tip warning={true}>

    If one of the model's tensor is bigger than `max_shard_size`, it will end up in its own shard which will have a
    size greater than `max_shard_size`.

    </Tip>

    <Tip warning={true}>

    If your model is a `transformers.PreTrainedModel`, you should pass `model._tied_weights_keys` as `shared_tensors_to_discard` to properly handle shared tensors saving. This ensures the correct duplicate tensors are discarded during saving.

    </Tip>

    Args:
        state_dict (`Dict[str, torch.Tensor]`):
            The state dictionary to save.
        save_directory (`str` or `Path`):
            The directory in which the model will be saved.
        filename_pattern (`str`, *optional*):
            The pattern to generate the files names in which the model will be saved. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
            Defaults to `"model{suffix}.safetensors"` or `pytorch_model{suffix}.bin` depending on `safe_serialization`
            parameter.
        force_contiguous (`boolean`, *optional*):
            Forcing the state_dict to be saved as contiguous tensors. This has no effect on the correctness of the
            model, but it could potentially change performance if the layout of the tensor was chosen specifically for
            that reason. Defaults to `True`.
        max_shard_size (`int` or `str`, *optional*):
            The maximum size of each shard, in bytes. Defaults to 5GB.
        metadata (`Dict[str, str]`, *optional*):
            Extra information to save along with the model. Some metadata will be added for each dropped tensors.
            This information will not be enough to recover the entire shared structure but might help understanding
            things.
        safe_serialization (`bool`, *optional*):
            Whether to save as safetensors, which is the default behavior. If `False`, the shards are saved as pickle.
            Safe serialization is recommended for security reasons. Saving as pickle is deprecated and will be removed
            in a future version.
        is_main_process (`bool`, *optional*):
            Whether the process calling this is the main process or not. Useful when in distributed training like
            TPUs and need to call this function from all processes. In this case, set `is_main_process=True` only on
            the main process to avoid race conditions. Defaults to True.
        shared_tensors_to_discard (`List[str]`, *optional*):
            List of tensor names to drop when saving shared tensors. If not provided and shared tensors are
            detected, it will drop the first name alphabetically.

    Example:

    ```py
    >>> from huggingface_hub import save_torch_state_dict
    >>> model = ... # A PyTorch model

    # Save state dict to "path/to/folder". The model will be split into shards of 5GB each and saved as safetensors.
    >>> state_dict = model_to_save.state_dict()
    >>> save_torch_state_dict(state_dict, "path/to/folder")
    ```
    """
    save_directory = str(save_directory)

    if filename_pattern is None:
        filename_pattern = (
            constants.SAFETENSORS_WEIGHTS_FILE_PATTERN
            if safe_serialization
            else constants.PYTORCH_WEIGHTS_FILE_PATTERN
        )

    if metadata is None:
        metadata = {}
    if safe_serialization:
        try:
            from safetensors.torch import save_file as save_file_fn
        except ImportError as e:
            raise ImportError(
                "Please install `safetensors` to use safe serialization. "
                "You can install it with `pip install safetensors`."
            ) from e
        # Clean state dict for safetensors
        state_dict = _clean_state_dict_for_safetensors(
            state_dict,
            metadata,
            force_contiguous=force_contiguous,
            shared_tensors_to_discard=shared_tensors_to_discard,
        )
    else:
        from torch import save as save_file_fn  # type: ignore[assignment, no-redef]

        logger.warning(
            "You are using unsafe serialization. Due to security reasons, it is recommended not to load "
            "pickled models from untrusted sources. If you intend to share your model, we strongly recommend "
            "using safe serialization by installing `safetensors` with `pip install safetensors`."
        )
    # Split dict
    state_dict_split = split_torch_state_dict_into_shards(
        state_dict, filename_pattern=filename_pattern, max_shard_size=max_shard_size
    )

    # Only main process should clean up existing files to avoid race conditions in distributed environment
    if is_main_process:
        existing_files_regex = re.compile(filename_pattern.format(suffix=r"(-\d{5}-of-\d{5})?") + r"(\.index\.json)?")
        for filename in os.listdir(save_directory):
            if existing_files_regex.match(filename):
                try:
                    logger.debug(f"Removing existing file '{filename}' from folder.")
                    os.remove(os.path.join(save_directory, filename))
                except Exception as e:
                    logger.warning(
                        f"Error when trying to remove existing '{filename}' from folder: {e}. Continuing..."
                    )

    # Save each shard
    per_file_metadata = {"format": "pt"}
    if not state_dict_split.is_sharded:
        per_file_metadata.update(metadata)
    safe_file_kwargs = {"metadata": per_file_metadata} if safe_serialization else {}
    for filename, tensors in state_dict_split.filename_to_tensors.items():
        shard = {tensor: state_dict[tensor] for tensor in tensors}
        save_file_fn(shard, os.path.join(save_directory, filename), **safe_file_kwargs)
        logger.debug(f"Shard saved to {filename}")

    # Save the index (if any)
    if state_dict_split.is_sharded:
        index_path = filename_pattern.format(suffix="") + ".index.json"
        index = {
            "metadata": {**state_dict_split.metadata, **metadata},
            "weight_map": state_dict_split.tensor_to_filename,
        }
        with open(os.path.join(save_directory, index_path), "w") as f:
            json.dump(index, f, indent=2)
        logger.info(
            f"The model is bigger than the maximum size per checkpoint ({max_shard_size}). "
            f"Model weighs have been saved in {len(state_dict_split.filename_to_tensors)} checkpoint shards. "
            f"You can find where each parameters has been saved in the index located at {index_path}."
        )

    logger.info(f"Model weights successfully saved to {save_directory}!")


def split_torch_state_dict_into_shards(
    state_dict: Dict[str, "torch.Tensor"],
    *,
    filename_pattern: str = constants.SAFETENSORS_WEIGHTS_FILE_PATTERN,
    max_shard_size: Union[int, str] = MAX_SHARD_SIZE,
) -> StateDictSplit:
    """
    Split a model state dictionary in shards so that each shard is smaller than a given size.

    The shards are determined by iterating through the `state_dict` in the order of its keys. There is no optimization
    made to make each shard as close as possible to the maximum size passed. For example, if the limit is 10GB and we
    have tensors of sizes [6GB, 6GB, 2GB, 6GB, 2GB, 2GB] they will get sharded as [6GB], [6+2GB], [6+2+2GB] and not
    [6+2+2GB], [6+2GB], [6GB].


    <Tip>

    To save a model state dictionary to the disk, see [`save_torch_state_dict`]. This helper uses
    `split_torch_state_dict_into_shards` under the hood.

    </Tip>

    <Tip warning={true}>

    If one of the model's tensor is bigger than `max_shard_size`, it will end up in its own shard which will have a
    size greater than `max_shard_size`.

    </Tip>

    Args:
        state_dict (`Dict[str, torch.Tensor]`):
            The state dictionary to save.
        filename_pattern (`str`, *optional*):
            The pattern to generate the files names in which the model will be saved. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
            Defaults to `"model{suffix}.safetensors"`.
        max_shard_size (`int` or `str`, *optional*):
            The maximum size of each shard, in bytes. Defaults to 5GB.

    Returns:
        [`StateDictSplit`]: A `StateDictSplit` object containing the shards and the index to retrieve them.

    Example:
    ```py
    >>> import json
    >>> import os
    >>> from safetensors.torch import save_file as safe_save_file
    >>> from huggingface_hub import split_torch_state_dict_into_shards

    >>> def save_state_dict(state_dict: Dict[str, torch.Tensor], save_directory: str):
    ...     state_dict_split = split_torch_state_dict_into_shards(state_dict)
    ...     for filename, tensors in state_dict_split.filename_to_tensors.items():
    ...         shard = {tensor: state_dict[tensor] for tensor in tensors}
    ...         safe_save_file(
    ...             shard,
    ...             os.path.join(save_directory, filename),
    ...             metadata={"format": "pt"},
    ...         )
    ...     if state_dict_split.is_sharded:
    ...         index = {
    ...             "metadata": state_dict_split.metadata,
    ...             "weight_map": state_dict_split.tensor_to_filename,
    ...         }
    ...         with open(os.path.join(save_directory, "model.safetensors.index.json"), "w") as f:
    ...             f.write(json.dumps(index, indent=2))
    ```
    """
    return split_state_dict_into_shards_factory(
        state_dict,
        max_shard_size=max_shard_size,
        filename_pattern=filename_pattern,
        get_storage_size=get_torch_storage_size,
        get_storage_id=get_torch_storage_id,
    )


# LOADING


def load_torch_model(
    model: "torch.nn.Module",
    checkpoint_path: Union[str, os.PathLike],
    *,
    strict: bool = False,
    safe: bool = True,
    weights_only: bool = False,
    map_location: Optional[Union[str, "torch.device"]] = None,
    mmap: bool = False,
    filename_pattern: Optional[str] = None,
) -> NamedTuple:
    """
    Load a checkpoint into a model, handling both sharded and non-sharded checkpoints.

    Args:
        model (`torch.nn.Module`):
            The model in which to load the checkpoint.
        checkpoint_path (`str` or `os.PathLike`):
            Path to either the checkpoint file or directory containing the checkpoint(s).
        strict (`bool`, *optional*, defaults to `False`):
            Whether to strictly enforce that the keys in the model state dict match the keys in the checkpoint.
        safe (`bool`, *optional*, defaults to `True`):
            If `safe` is True, the safetensors files will be loaded. If `safe` is False, the function
            will first attempt to load safetensors files if they are available, otherwise it will fall back to loading
            pickle files. `filename_pattern` parameter takes precedence over `safe` parameter.
        weights_only (`bool`, *optional*, defaults to `False`):
            If True, only loads the model weights without optimizer states and other metadata.
            Only supported in PyTorch >= 1.13.
        map_location (`str` or `torch.device`, *optional*):
            A `torch.device` object, string or a dict specifying how to remap storage locations. It
            indicates the location where all tensors should be loaded.
        mmap (`bool`, *optional*, defaults to `False`):
            Whether to use memory-mapped file loading. Memory mapping can improve loading performance
            for large models in PyTorch >= 2.1.0 with zipfile-based checkpoints.
        filename_pattern (`str`, *optional*):
            The pattern to look for the index file. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
            Defaults to `"model{suffix}.safetensors"`.
    Returns:
        `NamedTuple`: A named tuple with `missing_keys` and `unexpected_keys` fields.
            - `missing_keys` is a list of str containing the missing keys, i.e. keys that are in the model but not in the checkpoint.
            - `unexpected_keys` is a list of str containing the unexpected keys, i.e. keys that are in the checkpoint but not in the model.

    Raises:
        [`FileNotFoundError`](https://docs.python.org/3/library/exceptions.html#FileNotFoundError)
            If the checkpoint file or directory does not exist.
        [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError)
            If safetensors or torch is not installed when trying to load a .safetensors file or a PyTorch checkpoint respectively.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
           If the checkpoint path is invalid or if the checkpoint format cannot be determined.

    Example:
    ```python
    >>> from huggingface_hub import load_torch_model
    >>> model = ... # A PyTorch model
    >>> load_torch_model(model, "path/to/checkpoint")
    ```
    """
    checkpoint_path = Path(checkpoint_path)

    if not checkpoint_path.exists():
        raise ValueError(f"Checkpoint path {checkpoint_path} does not exist")
    # 1. Check if checkpoint is a single file
    if checkpoint_path.is_file():
        state_dict = load_state_dict_from_file(
            checkpoint_file=checkpoint_path,
            map_location=map_location,
            weights_only=weights_only,
        )
        return model.load_state_dict(state_dict, strict=strict)

    # 2. If not, checkpoint_path is a directory
    if filename_pattern is None:
        filename_pattern = constants.SAFETENSORS_WEIGHTS_FILE_PATTERN
        index_path = checkpoint_path / (filename_pattern.format(suffix="") + ".index.json")
        # Only fallback to pickle format if safetensors index is not found and safe is False.
        if not index_path.is_file() and not safe:
            filename_pattern = constants.PYTORCH_WEIGHTS_FILE_PATTERN

    index_path = checkpoint_path / (filename_pattern.format(suffix="") + ".index.json")

    if index_path.is_file():
        return _load_sharded_checkpoint(
            model=model,
            save_directory=checkpoint_path,
            strict=strict,
            weights_only=weights_only,
            filename_pattern=filename_pattern,
        )

    # Look for single model file
    model_files = list(checkpoint_path.glob("*.safetensors" if safe else "*.bin"))
    if len(model_files) == 1:
        state_dict = load_state_dict_from_file(
            checkpoint_file=model_files[0],
            map_location=map_location,
            weights_only=weights_only,
            mmap=mmap,
        )
        return model.load_state_dict(state_dict, strict=strict)

    raise ValueError(
        f"Directory '{checkpoint_path}' does not contain a valid checkpoint. "
        "Expected either a sharded checkpoint with an index file, or a single model file."
    )


def _load_sharded_checkpoint(
    model: "torch.nn.Module",
    save_directory: os.PathLike,
    *,
    strict: bool = False,
    weights_only: bool = False,
    filename_pattern: str = constants.SAFETENSORS_WEIGHTS_FILE_PATTERN,
) -> NamedTuple:
    """
    Loads a sharded checkpoint into a model. This is the same as
    [`torch.nn.Module.load_state_dict`](https://pytorch.org/docs/stable/generated/torch.nn.Module.html?highlight=load_state_dict#torch.nn.Module.load_state_dict)
    but for a sharded checkpoint. Each shard is loaded one by one and removed from memory after being loaded into the model.

    Args:
        model (`torch.nn.Module`):
            The model in which to load the checkpoint.
        save_directory (`str` or `os.PathLike`):
            A path to a folder containing the sharded checkpoint.
        strict (`bool`, *optional*, defaults to `False`):
            Whether to strictly enforce that the keys in the model state dict match the keys in the sharded checkpoint.
        weights_only (`bool`, *optional*, defaults to `False`):
            If True, only loads the model weights without optimizer states and other metadata.
            Only supported in PyTorch >= 1.13.
        filename_pattern (`str`, *optional*, defaults to `"model{suffix}.safetensors"`):
            The pattern to look for the index file. Pattern must be a string that
            can be formatted with `filename_pattern.format(suffix=...)` and must contain the keyword `suffix`
            Defaults to `"model{suffix}.safetensors"`.

    Returns:
        `NamedTuple`: A named tuple with `missing_keys` and `unexpected_keys` fields,
            - `missing_keys` is a list of str containing the missing keys
            - `unexpected_keys` is a list of str containing the unexpected keys
    """

    # 1. Load and validate index file
    # The index file contains mapping of parameter names to shard files
    index_path = filename_pattern.format(suffix="") + ".index.json"
    index_file = os.path.join(save_directory, index_path)
    with open(index_file, "r", encoding="utf-8") as f:
        index = json.load(f)

    # 2. Validate keys if in strict mode
    # This is done before loading any shards to fail fast
    if strict:
        _validate_keys_for_strict_loading(model, index["weight_map"].keys())

    # 3. Load each shard using `load_state_dict`
    # Get unique shard files (multiple parameters can be in same shard)
    shard_files = list(set(index["weight_map"].values()))
    for shard_file in shard_files:
        # Load shard into memory
        shard_path = os.path.join(save_directory, shard_file)
        state_dict = load_state_dict_from_file(
            shard_path,
            map_location="cpu",
            weights_only=weights_only,
        )
        # Update model with parameters from this shard
        model.load_state_dict(state_dict, strict=strict)
        # Explicitly remove the state dict from memory
        del state_dict

    # 4. Return compatibility info
    loaded_keys = set(index["weight_map"].keys())
    model_keys = set(model.state_dict().keys())
    return _IncompatibleKeys(
        missing_keys=list(model_keys - loaded_keys), unexpected_keys=list(loaded_keys - model_keys)
    )


def load_state_dict_from_file(
    checkpoint_file: Union[str, os.PathLike],
    map_location: Optional[Union[str, "torch.device"]] = None,
    weights_only: bool = False,
    mmap: bool = False,
) -> Union[Dict[str, "torch.Tensor"], Any]:
    """
    Loads a checkpoint file, handling both safetensors and pickle checkpoint formats.

    Args:
        checkpoint_file (`str` or `os.PathLike`):
            Path to the checkpoint file to load. Can be either a safetensors or pickle (`.bin`) checkpoint.
        map_location (`str` or `torch.device`, *optional*):
            A `torch.device` object, string or a dict specifying how to remap storage locations. It
            indicates the location where all tensors should be loaded.
        weights_only (`bool`, *optional*, defaults to `False`):
            If True, only loads the model weights without optimizer states and other metadata.
            Only supported for pickle (`.bin`) checkpoints with PyTorch >= 1.13. Has no effect when
            loading safetensors files.
        mmap (`bool`, *optional*, defaults to `False`):
            Whether to use memory-mapped file loading. Memory mapping can improve loading performance
            for large models in PyTorch >= 2.1.0 with zipfile-based checkpoints. Has no effect when
            loading safetensors files, as the `safetensors` library uses memory mapping by default.

    Returns:
        `Union[Dict[str, "torch.Tensor"], Any]`: The loaded checkpoint.
            - For safetensors files: always returns a dictionary mapping parameter names to tensors.
            - For pickle files: returns any Python object that was pickled (commonly a state dict, but could be
              an entire model, optimizer state, or any other Python object).

    Raises:
        [`FileNotFoundError`](https://docs.python.org/3/library/exceptions.html#FileNotFoundError)
            If the checkpoint file does not exist.
        [`ImportError`](https://docs.python.org/3/library/exceptions.html#ImportError)
            If safetensors or torch is not installed when trying to load a .safetensors file or a PyTorch checkpoint respectively.
        [`OSError`](https://docs.python.org/3/library/exceptions.html#OSError)
            If the checkpoint file format is invalid or if git-lfs files are not properly downloaded.
        [`ValueError`](https://docs.python.org/3/library/exceptions.html#ValueError)
            If the checkpoint file path is empty or invalid.

    Example:
    ```python
    >>> from huggingface_hub import load_state_dict_from_file

    # Load a PyTorch checkpoint
    >>> state_dict = load_state_dict_from_file("path/to/model.bin", map_location="cpu")
    >>> model.load_state_dict(state_dict)

    # Load a safetensors checkpoint
    >>> state_dict = load_state_dict_from_file("path/to/model.safetensors")
    >>> model.load_state_dict(state_dict)
    ```
    """
    checkpoint_path = Path(checkpoint_file)

    # Check if file exists and is a regular file (not a directory)
    if not checkpoint_path.is_file():
        raise FileNotFoundError(
            f"No checkpoint file found at '{checkpoint_path}'. Please verify the path is correct and "
            "the file has been properly downloaded."
        )

    # Load safetensors checkpoint
    if checkpoint_path.suffix == ".safetensors":
        try:
            from safetensors import safe_open
            from safetensors.torch import load_file
        except ImportError as e:
            raise ImportError(
                "Please install `safetensors` to load safetensors checkpoint. "
                "You can install it with `pip install safetensors`."
            ) from e

        # Check format of the archive
        with safe_open(checkpoint_file, framework="pt") as f:  # type: ignore[attr-defined]
            metadata = f.metadata()
        # see comment: https://github.com/huggingface/transformers/blob/3d213b57fe74302e5902d68ed9478c3ad1aaa713/src/transformers/modeling_utils.py#L3966
        if metadata is not None and metadata.get("format") not in ["pt", "mlx"]:
            raise OSError(
                f"The safetensors archive passed at {checkpoint_file} does not contain the valid metadata. Make sure "
                "you save your model with the `save_torch_model` method."
            )
        device = str(map_location.type) if map_location is not None and hasattr(map_location, "type") else map_location
        # meta device is not supported with safetensors, falling back to CPU
        if device == "meta":
            logger.warning("Meta device is not supported with safetensors. Falling back to CPU device.")
            device = "cpu"
        return load_file(checkpoint_file, device=device)  # type: ignore[arg-type]
    # Otherwise, load from pickle
    try:
        import torch
        from torch import load
    except ImportError as e:
        raise ImportError(
            "Please install `torch` to load torch tensors. You can install it with `pip install torch`."
        ) from e
    # Add additional kwargs, mmap is only supported in torch >= 2.1.0
    additional_kwargs = {}
    if version.parse(torch.__version__) >= version.parse("2.1.0"):
        additional_kwargs["mmap"] = mmap

    # weights_only is only supported in torch >= 1.13.0
    if version.parse(torch.__version__) >= version.parse("1.13.0"):
        additional_kwargs["weights_only"] = weights_only

    return load(
        checkpoint_file,
        map_location=map_location,
        **additional_kwargs,
    )


# HELPERS


def _validate_keys_for_strict_loading(
    model: "torch.nn.Module",
    loaded_keys: Iterable[str],
) -> None:
    """
    Validate that model keys match loaded keys when strict loading is enabled.

    Args:
        model: The PyTorch model being loaded
        loaded_keys: The keys present in the checkpoint

    Raises:
        RuntimeError: If there are missing or unexpected keys in strict mode
    """
    loaded_keys_set = set(loaded_keys)
    model_keys = set(model.state_dict().keys())
    missing_keys = model_keys - loaded_keys_set  # Keys in model but not in checkpoint
    unexpected_keys = loaded_keys_set - model_keys  # Keys in checkpoint but not in model

    if missing_keys or unexpected_keys:
        error_message = f"Error(s) in loading state_dict for {model.__class__.__name__}"
        if missing_keys:
            str_missing_keys = ",".join([f'"{k}"' for k in sorted(missing_keys)])
            error_message += f"\nMissing key(s): {str_missing_keys}."
        if unexpected_keys:
            str_unexpected_keys = ",".join([f'"{k}"' for k in sorted(unexpected_keys)])
            error_message += f"\nUnexpected key(s): {str_unexpected_keys}."
        raise RuntimeError(error_message)


def _get_unique_id(tensor: "torch.Tensor") -> Union[int, Tuple[Any, ...]]:
    """Returns a unique id for plain tensor
    or a (potentially nested) Tuple of unique id for the flattened Tensor
    if the input is a wrapper tensor subclass Tensor
    """

    try:
        from torch.distributed.tensor import DTensor

        if isinstance(tensor, DTensor):
            local_tensor = tensor.to_local()
            return local_tensor.storage().data_ptr()
    except ImportError:
        pass

    try:
        # for torch 2.1 and above we can also handle tensor subclasses
        from torch.utils._python_dispatch import is_traceable_wrapper_subclass

        if is_traceable_wrapper_subclass(tensor):
            attrs, _ = tensor.__tensor_flatten__()  # type: ignore[attr-defined]
            return tuple(_get_unique_id(getattr(tensor, attr)) for attr in attrs)

    except ImportError:
        # for torch version less than 2.1, we can fallback to original implementation
        pass

    if tensor.device.type == "xla" and is_torch_tpu_available():
        # NOTE: xla tensors dont have storage
        # use some other unique id to distinguish.
        # this is a XLA tensor, it must be created using torch_xla's
        # device. So the following import is safe:
        import torch_xla  # type: ignore[import]

        unique_id = torch_xla._XLAC._xla_get_tensor_id(tensor)
    else:
        unique_id = storage_ptr(tensor)

    return unique_id


def get_torch_storage_id(tensor: "torch.Tensor") -> Optional[Tuple["torch.device", Union[int, Tuple[Any, ...]], int]]:
    """
    Return unique identifier to a tensor storage.

    Multiple different tensors can share the same underlying storage. This identifier is
    guaranteed to be unique and constant for this tensor's storage during its lifetime. Two tensor storages with
    non-overlapping lifetimes may have the same id.
    In the case of meta tensors, we return None since we can't tell if they share the same storage.

    Taken from https://github.com/huggingface/transformers/blob/1ecf5f7c982d761b4daaa96719d162c324187c64/src/transformers/pytorch_utils.py#L278.
    """
    if tensor.device.type == "meta":
        return None
    else:
        return tensor.device, _get_unique_id(tensor), get_torch_storage_size(tensor)


def get_torch_storage_size(tensor: "torch.Tensor") -> int:
    """
    Taken from https://github.com/huggingface/safetensors/blob/08db34094e9e59e2f9218f2df133b7b4aaff5a99/bindings/python/py_src/safetensors/torch.py#L31C1-L41C59
    """
    try:
        from torch.distributed.tensor import DTensor

        if isinstance(tensor, DTensor):
            # this returns the size of the FULL tensor in bytes
            return tensor.nbytes
    except ImportError:
        pass

    try:
        # for torch 2.1 and above we can also handle tensor subclasses
        from torch.utils._python_dispatch import is_traceable_wrapper_subclass

        if is_traceable_wrapper_subclass(tensor):
            attrs, _ = tensor.__tensor_flatten__()  # type: ignore[attr-defined]
            return sum(get_torch_storage_size(getattr(tensor, attr)) for attr in attrs)
    except ImportError:
        # for torch version less than 2.1, we can fallback to original implementation
        pass

    try:
        return tensor.untyped_storage().nbytes()
    except AttributeError:
        # Fallback for torch==1.10
        try:
            return tensor.storage().size() * _get_dtype_size(tensor.dtype)
        except NotImplementedError:
            # Fallback for meta storage
            # On torch >=2.0 this is the tensor size
            return tensor.nelement() * _get_dtype_size(tensor.dtype)


@lru_cache()
def is_torch_tpu_available(check_device=True):
    """
    Checks if `torch_xla` is installed and potentially if a TPU is in the environment

    Taken from https://github.com/huggingface/transformers/blob/1ecf5f7c982d761b4daaa96719d162c324187c64/src/transformers/utils/import_utils.py#L463.
    """
    if importlib.util.find_spec("torch_xla") is not None:
        if check_device:
            # We need to check if `xla_device` can be found, will raise a RuntimeError if not
            try:
                import torch_xla.core.xla_model as xm  # type: ignore[import]

                _ = xm.xla_device()
                return True
            except RuntimeError:
                return False
        return True
    return False


def storage_ptr(tensor: "torch.Tensor") -> Union[int, Tuple[Any, ...]]:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L11.
    """
    try:
        # for torch 2.1 and above we can also handle tensor subclasses
        from torch.utils._python_dispatch import is_traceable_wrapper_subclass

        if is_traceable_wrapper_subclass(tensor):
            return _get_unique_id(tensor)  # type: ignore
    except ImportError:
        # for torch version less than 2.1, we can fallback to original implementation
        pass

    try:
        return tensor.untyped_storage().data_ptr()
    except Exception:
        # Fallback for torch==1.10
        try:
            return tensor.storage().data_ptr()
        except NotImplementedError:
            # Fallback for meta storage
            return 0


def _clean_state_dict_for_safetensors(
    state_dict: Dict[str, "torch.Tensor"],
    metadata: Dict[str, str],
    force_contiguous: bool = True,
    shared_tensors_to_discard: Optional[List[str]] = None,
):
    """Remove shared tensors from state_dict and update metadata accordingly (for reloading).

    Warning: `state_dict` and `metadata` are mutated in-place!

    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L155.
    """
    to_removes = _remove_duplicate_names(state_dict, discard_names=shared_tensors_to_discard)
    for kept_name, to_remove_group in to_removes.items():
        for to_remove in to_remove_group:
            if metadata is None:
                metadata = {}

            if to_remove not in metadata:
                # Do not override user data
                metadata[to_remove] = kept_name
            del state_dict[to_remove]
    if force_contiguous:
        state_dict = {k: v.contiguous() for k, v in state_dict.items()}
    return state_dict


def _end_ptr(tensor: "torch.Tensor") -> int:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L23.
    """
    if tensor.nelement():
        stop = tensor.view(-1)[-1].data_ptr() + _get_dtype_size(tensor.dtype)
    else:
        stop = tensor.data_ptr()
    return stop


def _filter_shared_not_shared(tensors: List[Set[str]], state_dict: Dict[str, "torch.Tensor"]) -> List[Set[str]]:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L44
    """
    filtered_tensors = []
    for shared in tensors:
        if len(shared) < 2:
            filtered_tensors.append(shared)
            continue

        areas = []
        for name in shared:
            tensor = state_dict[name]
            areas.append((tensor.data_ptr(), _end_ptr(tensor), name))
        areas.sort()

        _, last_stop, last_name = areas[0]
        filtered_tensors.append({last_name})
        for start, stop, name in areas[1:]:
            if start >= last_stop:
                filtered_tensors.append({name})
            else:
                filtered_tensors[-1].add(name)
            last_stop = stop

    return filtered_tensors


def _find_shared_tensors(state_dict: Dict[str, "torch.Tensor"]) -> List[Set[str]]:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L69.
    """
    import torch

    tensors_dict = defaultdict(set)
    for k, v in state_dict.items():
        if v.device != torch.device("meta") and storage_ptr(v) != 0 and get_torch_storage_size(v) != 0:
            # Need to add device as key because of multiple GPU.
            tensors_dict[(v.device, storage_ptr(v), get_torch_storage_size(v))].add(k)
    tensors = list(sorted(tensors_dict.values()))
    tensors = _filter_shared_not_shared(tensors, state_dict)
    return tensors


def _is_complete(tensor: "torch.Tensor") -> bool:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L80
    """
    try:
        # for torch 2.1 and above we can also handle tensor subclasses
        from torch.utils._python_dispatch import is_traceable_wrapper_subclass

        if is_traceable_wrapper_subclass(tensor):
            attrs, _ = tensor.__tensor_flatten__()  # type: ignore[attr-defined]
            return all(_is_complete(getattr(tensor, attr)) for attr in attrs)
    except ImportError:
        # for torch version less than 2.1, we can fallback to original implementation
        pass

    return tensor.data_ptr() == storage_ptr(tensor) and tensor.nelement() * _get_dtype_size(
        tensor.dtype
    ) == get_torch_storage_size(tensor)


def _remove_duplicate_names(
    state_dict: Dict[str, "torch.Tensor"],
    *,
    preferred_names: Optional[List[str]] = None,
    discard_names: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """
    Taken from https://github.com/huggingface/safetensors/blob/079781fd0dc455ba0fe851e2b4507c33d0c0d407/bindings/python/py_src/safetensors/torch.py#L80
    """
    if preferred_names is None:
        preferred_names = []
    unique_preferred_names = set(preferred_names)
    if discard_names is None:
        discard_names = []
    unique_discard_names = set(discard_names)

    shareds = _find_shared_tensors(state_dict)
    to_remove = defaultdict(list)
    for shared in shareds:
        complete_names = set([name for name in shared if _is_complete(state_dict[name])])
        if not complete_names:
            raise RuntimeError(
                "Error while trying to find names to remove to save state dict, but found no suitable name to keep"
                f" for saving amongst: {shared}. None is covering the entire storage. Refusing to save/load the model"
                " since you could be storing much more memory than needed. Please refer to"
                " https://huggingface.co/docs/safetensors/torch_shared_tensors for more information. Or open an"
                " issue."
            )

        keep_name = sorted(list(complete_names))[0]

        # Mechanism to preferentially select keys to keep
        # coming from the on-disk file to allow
        # loading models saved with a different choice
        # of keep_name
        preferred = complete_names.difference(unique_discard_names)
        if preferred:
            keep_name = sorted(list(preferred))[0]

        if unique_preferred_names:
            preferred = unique_preferred_names.intersection(complete_names)
            if preferred:
                keep_name = sorted(list(preferred))[0]
        for name in sorted(shared):
            if name != keep_name:
                to_remove[keep_name].append(name)
    return to_remove


@lru_cache()
def _get_dtype_size(dtype: "torch.dtype") -> int:
    """
    Taken from https://github.com/huggingface/safetensors/blob/08db34094e9e59e2f9218f2df133b7b4aaff5a99/bindings/python/py_src/safetensors/torch.py#L344
    """
    import torch

    # torch.float8 formats require 2.1; we do not support these dtypes on earlier versions
    _float8_e4m3fn = getattr(torch, "float8_e4m3fn", None)
    _float8_e5m2 = getattr(torch, "float8_e5m2", None)
    _SIZE = {
        torch.int64: 8,
        torch.float32: 4,
        torch.int32: 4,
        torch.bfloat16: 2,
        torch.float16: 2,
        torch.int16: 2,
        torch.uint8: 1,
        torch.int8: 1,
        torch.bool: 1,
        torch.float64: 8,
        _float8_e4m3fn: 1,
        _float8_e5m2: 1,
    }
    return _SIZE[dtype]


class _IncompatibleKeys(namedtuple("IncompatibleKeys", ["missing_keys", "unexpected_keys"])):
    """
    This is used to report missing and unexpected keys in the state dict.
    Taken from https://github.com/pytorch/pytorch/blob/main/torch/nn/modules/module.py#L52.

    """

    def __repr__(self) -> str:
        if not self.missing_keys and not self.unexpected_keys:
            return "<All keys matched successfully>"
        return super().__repr__()

    __str__ = __repr__

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\distlib\metadata.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""Implementation of the Metadata for Python packages PEPs.

Supports all metadata formats (1.0, 1.1, 1.2, 1.3/2.1 and 2.2).
"""
from __future__ import unicode_literals

import codecs
from email import message_from_file
import json
import logging
import re

from . import DistlibException, __version__
from .compat import StringIO, string_types, text_type
from .markers import interpret
from .util import extract_by_key, get_extras
from .version import get_scheme, PEP440_VERSION_RE

logger = logging.getLogger(__name__)


class MetadataMissingError(DistlibException):
    """A required metadata is missing"""


class MetadataConflictError(DistlibException):
    """Attempt to read or write metadata fields that are conflictual."""


class MetadataUnrecognizedVersionError(DistlibException):
    """Unknown metadata version number."""


class MetadataInvalidError(DistlibException):
    """A metadata value is invalid"""


# public API of this module
__all__ = ['Metadata', 'PKG_INFO_ENCODING', 'PKG_INFO_PREFERRED_VERSION']

# Encoding used for the PKG-INFO files
PKG_INFO_ENCODING = 'utf-8'

# preferred version. Hopefully will be changed
# to 1.2 once PEP 345 is supported everywhere
PKG_INFO_PREFERRED_VERSION = '1.1'

_LINE_PREFIX_1_2 = re.compile('\n       \\|')
_LINE_PREFIX_PRE_1_2 = re.compile('\n        ')
_241_FIELDS = ('Metadata-Version', 'Name', 'Version', 'Platform', 'Summary', 'Description', 'Keywords', 'Home-page',
               'Author', 'Author-email', 'License')

_314_FIELDS = ('Metadata-Version', 'Name', 'Version', 'Platform', 'Supported-Platform', 'Summary', 'Description',
               'Keywords', 'Home-page', 'Author', 'Author-email', 'License', 'Classifier', 'Download-URL', 'Obsoletes',
               'Provides', 'Requires')

_314_MARKERS = ('Obsoletes', 'Provides', 'Requires', 'Classifier', 'Download-URL')

_345_FIELDS = ('Metadata-Version', 'Name', 'Version', 'Platform', 'Supported-Platform', 'Summary', 'Description',
               'Keywords', 'Home-page', 'Author', 'Author-email', 'Maintainer', 'Maintainer-email', 'License',
               'Classifier', 'Download-URL', 'Obsoletes-Dist', 'Project-URL', 'Provides-Dist', 'Requires-Dist',
               'Requires-Python', 'Requires-External')

_345_MARKERS = ('Provides-Dist', 'Requires-Dist', 'Requires-Python', 'Obsoletes-Dist', 'Requires-External',
                'Maintainer', 'Maintainer-email', 'Project-URL')

_426_FIELDS = ('Metadata-Version', 'Name', 'Version', 'Platform', 'Supported-Platform', 'Summary', 'Description',
               'Keywords', 'Home-page', 'Author', 'Author-email', 'Maintainer', 'Maintainer-email', 'License',
               'Classifier', 'Download-URL', 'Obsoletes-Dist', 'Project-URL', 'Provides-Dist', 'Requires-Dist',
               'Requires-Python', 'Requires-External', 'Private-Version', 'Obsoleted-By', 'Setup-Requires-Dist',
               'Extension', 'Provides-Extra')

_426_MARKERS = ('Private-Version', 'Provides-Extra', 'Obsoleted-By', 'Setup-Requires-Dist', 'Extension')

# See issue #106: Sometimes 'Requires' and 'Provides' occur wrongly in
# the metadata. Include them in the tuple literal below to allow them
# (for now).
# Ditto for Obsoletes - see issue #140.
_566_FIELDS = _426_FIELDS + ('Description-Content-Type', 'Requires', 'Provides', 'Obsoletes')

_566_MARKERS = ('Description-Content-Type', )

_643_MARKERS = ('Dynamic', 'License-File')

_643_FIELDS = _566_FIELDS + _643_MARKERS

_ALL_FIELDS = set()
_ALL_FIELDS.update(_241_FIELDS)
_ALL_FIELDS.update(_314_FIELDS)
_ALL_FIELDS.update(_345_FIELDS)
_ALL_FIELDS.update(_426_FIELDS)
_ALL_FIELDS.update(_566_FIELDS)
_ALL_FIELDS.update(_643_FIELDS)

EXTRA_RE = re.compile(r'''extra\s*==\s*("([^"]+)"|'([^']+)')''')


def _version2fieldlist(version):
    if version == '1.0':
        return _241_FIELDS
    elif version == '1.1':
        return _314_FIELDS
    elif version == '1.2':
        return _345_FIELDS
    elif version in ('1.3', '2.1'):
        # avoid adding field names if already there
        return _345_FIELDS + tuple(f for f in _566_FIELDS if f not in _345_FIELDS)
    elif version == '2.0':
        raise ValueError('Metadata 2.0 is withdrawn and not supported')
        # return _426_FIELDS
    elif version == '2.2':
        return _643_FIELDS
    raise MetadataUnrecognizedVersionError(version)


def _best_version(fields):
    """Detect the best version depending on the fields used."""

    def _has_marker(keys, markers):
        return any(marker in keys for marker in markers)

    keys = [key for key, value in fields.items() if value not in ([], 'UNKNOWN', None)]
    possible_versions = ['1.0', '1.1', '1.2', '1.3', '2.1', '2.2']  # 2.0 removed

    # first let's try to see if a field is not part of one of the version
    for key in keys:
        if key not in _241_FIELDS and '1.0' in possible_versions:
            possible_versions.remove('1.0')
            logger.debug('Removed 1.0 due to %s', key)
        if key not in _314_FIELDS and '1.1' in possible_versions:
            possible_versions.remove('1.1')
            logger.debug('Removed 1.1 due to %s', key)
        if key not in _345_FIELDS and '1.2' in possible_versions:
            possible_versions.remove('1.2')
            logger.debug('Removed 1.2 due to %s', key)
        if key not in _566_FIELDS and '1.3' in possible_versions:
            possible_versions.remove('1.3')
            logger.debug('Removed 1.3 due to %s', key)
        if key not in _566_FIELDS and '2.1' in possible_versions:
            if key != 'Description':  # In 2.1, description allowed after headers
                possible_versions.remove('2.1')
                logger.debug('Removed 2.1 due to %s', key)
        if key not in _643_FIELDS and '2.2' in possible_versions:
            possible_versions.remove('2.2')
            logger.debug('Removed 2.2 due to %s', key)
        # if key not in _426_FIELDS and '2.0' in possible_versions:
        # possible_versions.remove('2.0')
        # logger.debug('Removed 2.0 due to %s', key)

    # possible_version contains qualified versions
    if len(possible_versions) == 1:
        return possible_versions[0]  # found !
    elif len(possible_versions) == 0:
        logger.debug('Out of options - unknown metadata set: %s', fields)
        raise MetadataConflictError('Unknown metadata set')

    # let's see if one unique marker is found
    is_1_1 = '1.1' in possible_versions and _has_marker(keys, _314_MARKERS)
    is_1_2 = '1.2' in possible_versions and _has_marker(keys, _345_MARKERS)
    is_2_1 = '2.1' in possible_versions and _has_marker(keys, _566_MARKERS)
    # is_2_0 = '2.0' in possible_versions and _has_marker(keys, _426_MARKERS)
    is_2_2 = '2.2' in possible_versions and _has_marker(keys, _643_MARKERS)
    if int(is_1_1) + int(is_1_2) + int(is_2_1) + int(is_2_2) > 1:
        raise MetadataConflictError('You used incompatible 1.1/1.2/2.1/2.2 fields')

    # we have the choice, 1.0, or 1.2, 2.1 or 2.2
    #   - 1.0 has a broken Summary field but works with all tools
    #   - 1.1 is to avoid
    #   - 1.2 fixes Summary but has little adoption
    #   - 2.1 adds more features
    #   - 2.2 is the latest
    if not is_1_1 and not is_1_2 and not is_2_1 and not is_2_2:
        # we couldn't find any specific marker
        if PKG_INFO_PREFERRED_VERSION in possible_versions:
            return PKG_INFO_PREFERRED_VERSION
    if is_1_1:
        return '1.1'
    if is_1_2:
        return '1.2'
    if is_2_1:
        return '2.1'
    # if is_2_2:
    # return '2.2'

    return '2.2'


# This follows the rules about transforming keys as described in
# https://www.python.org/dev/peps/pep-0566/#id17
_ATTR2FIELD = {name.lower().replace("-", "_"): name for name in _ALL_FIELDS}
_FIELD2ATTR = {field: attr for attr, field in _ATTR2FIELD.items()}

_PREDICATE_FIELDS = ('Requires-Dist', 'Obsoletes-Dist', 'Provides-Dist')
_VERSIONS_FIELDS = ('Requires-Python', )
_VERSION_FIELDS = ('Version', )
_LISTFIELDS = ('Platform', 'Classifier', 'Obsoletes', 'Requires', 'Provides', 'Obsoletes-Dist', 'Provides-Dist',
               'Requires-Dist', 'Requires-External', 'Project-URL', 'Supported-Platform', 'Setup-Requires-Dist',
               'Provides-Extra', 'Extension', 'License-File')
_LISTTUPLEFIELDS = ('Project-URL', )

_ELEMENTSFIELD = ('Keywords', )

_UNICODEFIELDS = ('Author', 'Maintainer', 'Summary', 'Description')

_MISSING = object()

_FILESAFE = re.compile('[^A-Za-z0-9.]+')


def _get_name_and_version(name, version, for_filename=False):
    """Return the distribution name with version.

    If for_filename is true, return a filename-escaped form."""
    if for_filename:
        # For both name and version any runs of non-alphanumeric or '.'
        # characters are replaced with a single '-'.  Additionally any
        # spaces in the version string become '.'
        name = _FILESAFE.sub('-', name)
        version = _FILESAFE.sub('-', version.replace(' ', '.'))
    return '%s-%s' % (name, version)


class LegacyMetadata(object):
    """The legacy metadata of a release.

    Supports versions 1.0, 1.1, 1.2, 2.0 and 1.3/2.1 (auto-detected). You can
    instantiate the class with one of these arguments (or none):
    - *path*, the path to a metadata file
    - *fileobj* give a file-like object with metadata as content
    - *mapping* is a dict-like object
    - *scheme* is a version scheme name
    """

    # TODO document the mapping API and UNKNOWN default key

    def __init__(self, path=None, fileobj=None, mapping=None, scheme='default'):
        if [path, fileobj, mapping].count(None) < 2:
            raise TypeError('path, fileobj and mapping are exclusive')
        self._fields = {}
        self.requires_files = []
        self._dependencies = None
        self.scheme = scheme
        if path is not None:
            self.read(path)
        elif fileobj is not None:
            self.read_file(fileobj)
        elif mapping is not None:
            self.update(mapping)
            self.set_metadata_version()

    def set_metadata_version(self):
        self._fields['Metadata-Version'] = _best_version(self._fields)

    def _write_field(self, fileobj, name, value):
        fileobj.write('%s: %s\n' % (name, value))

    def __getitem__(self, name):
        return self.get(name)

    def __setitem__(self, name, value):
        return self.set(name, value)

    def __delitem__(self, name):
        field_name = self._convert_name(name)
        try:
            del self._fields[field_name]
        except KeyError:
            raise KeyError(name)

    def __contains__(self, name):
        return (name in self._fields or self._convert_name(name) in self._fields)

    def _convert_name(self, name):
        if name in _ALL_FIELDS:
            return name
        name = name.replace('-', '_').lower()
        return _ATTR2FIELD.get(name, name)

    def _default_value(self, name):
        if name in _LISTFIELDS or name in _ELEMENTSFIELD:
            return []
        return 'UNKNOWN'

    def _remove_line_prefix(self, value):
        if self.metadata_version in ('1.0', '1.1'):
            return _LINE_PREFIX_PRE_1_2.sub('\n', value)
        else:
            return _LINE_PREFIX_1_2.sub('\n', value)

    def __getattr__(self, name):
        if name in _ATTR2FIELD:
            return self[name]
        raise AttributeError(name)

    #
    # Public API
    #

    def get_fullname(self, filesafe=False):
        """
        Return the distribution name with version.

        If filesafe is true, return a filename-escaped form.
        """
        return _get_name_and_version(self['Name'], self['Version'], filesafe)

    def is_field(self, name):
        """return True if name is a valid metadata key"""
        name = self._convert_name(name)
        return name in _ALL_FIELDS

    def is_multi_field(self, name):
        name = self._convert_name(name)
        return name in _LISTFIELDS

    def read(self, filepath):
        """Read the metadata values from a file path."""
        fp = codecs.open(filepath, 'r', encoding='utf-8')
        try:
            self.read_file(fp)
        finally:
            fp.close()

    def read_file(self, fileob):
        """Read the metadata values from a file object."""
        msg = message_from_file(fileob)
        self._fields['Metadata-Version'] = msg['metadata-version']

        # When reading, get all the fields we can
        for field in _ALL_FIELDS:
            if field not in msg:
                continue
            if field in _LISTFIELDS:
                # we can have multiple lines
                values = msg.get_all(field)
                if field in _LISTTUPLEFIELDS and values is not None:
                    values = [tuple(value.split(',')) for value in values]
                self.set(field, values)
            else:
                # single line
                value = msg[field]
                if value is not None and value != 'UNKNOWN':
                    self.set(field, value)

        # PEP 566 specifies that the body be used for the description, if
        # available
        body = msg.get_payload()
        self["Description"] = body if body else self["Description"]
        # logger.debug('Attempting to set metadata for %s', self)
        # self.set_metadata_version()

    def write(self, filepath, skip_unknown=False):
        """Write the metadata fields to filepath."""
        fp = codecs.open(filepath, 'w', encoding='utf-8')
        try:
            self.write_file(fp, skip_unknown)
        finally:
            fp.close()

    def write_file(self, fileobject, skip_unknown=False):
        """Write the PKG-INFO format data to a file object."""
        self.set_metadata_version()

        for field in _version2fieldlist(self['Metadata-Version']):
            values = self.get(field)
            if skip_unknown and values in ('UNKNOWN', [], ['UNKNOWN']):
                continue
            if field in _ELEMENTSFIELD:
                self._write_field(fileobject, field, ','.join(values))
                continue
            if field not in _LISTFIELDS:
                if field == 'Description':
                    if self.metadata_version in ('1.0', '1.1'):
                        values = values.replace('\n', '\n        ')
                    else:
                        values = values.replace('\n', '\n       |')
                values = [values]

            if field in _LISTTUPLEFIELDS:
                values = [','.join(value) for value in values]

            for value in values:
                self._write_field(fileobject, field, value)

    def update(self, other=None, **kwargs):
        """Set metadata values from the given iterable `other` and kwargs.

        Behavior is like `dict.update`: If `other` has a ``keys`` method,
        they are looped over and ``self[key]`` is assigned ``other[key]``.
        Else, ``other`` is an iterable of ``(key, value)`` iterables.

        Keys that don't match a metadata field or that have an empty value are
        dropped.
        """

        def _set(key, value):
            if key in _ATTR2FIELD and value:
                self.set(self._convert_name(key), value)

        if not other:
            # other is None or empty container
            pass
        elif hasattr(other, 'keys'):
            for k in other.keys():
                _set(k, other[k])
        else:
            for k, v in other:
                _set(k, v)

        if kwargs:
            for k, v in kwargs.items():
                _set(k, v)

    def set(self, name, value):
        """Control then set a metadata field."""
        name = self._convert_name(name)

        if ((name in _ELEMENTSFIELD or name == 'Platform') and not isinstance(value, (list, tuple))):
            if isinstance(value, string_types):
                value = [v.strip() for v in value.split(',')]
            else:
                value = []
        elif (name in _LISTFIELDS and not isinstance(value, (list, tuple))):
            if isinstance(value, string_types):
                value = [value]
            else:
                value = []

        if logger.isEnabledFor(logging.WARNING):
            project_name = self['Name']

            scheme = get_scheme(self.scheme)
            if name in _PREDICATE_FIELDS and value is not None:
                for v in value:
                    # check that the values are valid
                    if not scheme.is_valid_matcher(v.split(';')[0]):
                        logger.warning("'%s': '%s' is not valid (field '%s')", project_name, v, name)
            # FIXME this rejects UNKNOWN, is that right?
            elif name in _VERSIONS_FIELDS and value is not None:
                if not scheme.is_valid_constraint_list(value):
                    logger.warning("'%s': '%s' is not a valid version (field '%s')", project_name, value, name)
            elif name in _VERSION_FIELDS and value is not None:
                if not scheme.is_valid_version(value):
                    logger.warning("'%s': '%s' is not a valid version (field '%s')", project_name, value, name)

        if name in _UNICODEFIELDS:
            if name == 'Description':
                value = self._remove_line_prefix(value)

        self._fields[name] = value

    def get(self, name, default=_MISSING):
        """Get a metadata field."""
        name = self._convert_name(name)
        if name not in self._fields:
            if default is _MISSING:
                default = self._default_value(name)
            return default
        if name in _UNICODEFIELDS:
            value = self._fields[name]
            return value
        elif name in _LISTFIELDS:
            value = self._fields[name]
            if value is None:
                return []
            res = []
            for val in value:
                if name not in _LISTTUPLEFIELDS:
                    res.append(val)
                else:
                    # That's for Project-URL
                    res.append((val[0], val[1]))
            return res

        elif name in _ELEMENTSFIELD:
            value = self._fields[name]
            if isinstance(value, string_types):
                return value.split(',')
        return self._fields[name]

    def check(self, strict=False):
        """Check if the metadata is compliant. If strict is True then raise if
        no Name or Version are provided"""
        self.set_metadata_version()

        # XXX should check the versions (if the file was loaded)
        missing, warnings = [], []

        for attr in ('Name', 'Version'):  # required by PEP 345
            if attr not in self:
                missing.append(attr)

        if strict and missing != []:
            msg = 'missing required metadata: %s' % ', '.join(missing)
            raise MetadataMissingError(msg)

        for attr in ('Home-page', 'Author'):
            if attr not in self:
                missing.append(attr)

        # checking metadata 1.2 (XXX needs to check 1.1, 1.0)
        if self['Metadata-Version'] != '1.2':
            return missing, warnings

        scheme = get_scheme(self.scheme)

        def are_valid_constraints(value):
            for v in value:
                if not scheme.is_valid_matcher(v.split(';')[0]):
                    return False
            return True

        for fields, controller in ((_PREDICATE_FIELDS, are_valid_constraints),
                                   (_VERSIONS_FIELDS, scheme.is_valid_constraint_list), (_VERSION_FIELDS,
                                                                                         scheme.is_valid_version)):
            for field in fields:
                value = self.get(field, None)
                if value is not None and not controller(value):
                    warnings.append("Wrong value for '%s': %s" % (field, value))

        return missing, warnings

    def todict(self, skip_missing=False):
        """Return fields as a dict.

        Field names will be converted to use the underscore-lowercase style
        instead of hyphen-mixed case (i.e. home_page instead of Home-page).
        This is as per https://www.python.org/dev/peps/pep-0566/#id17.
        """
        self.set_metadata_version()

        fields = _version2fieldlist(self['Metadata-Version'])

        data = {}

        for field_name in fields:
            if not skip_missing or field_name in self._fields:
                key = _FIELD2ATTR[field_name]
                if key != 'project_url':
                    data[key] = self[field_name]
                else:
                    data[key] = [','.join(u) for u in self[field_name]]

        return data

    def add_requirements(self, requirements):
        if self['Metadata-Version'] == '1.1':
            # we can't have 1.1 metadata *and* Setuptools requires
            for field in ('Obsoletes', 'Requires', 'Provides'):
                if field in self:
                    del self[field]
        self['Requires-Dist'] += requirements

    # Mapping API
    # TODO could add iter* variants

    def keys(self):
        return list(_version2fieldlist(self['Metadata-Version']))

    def __iter__(self):
        for key in self.keys():
            yield key

    def values(self):
        return [self[key] for key in self.keys()]

    def items(self):
        return [(key, self[key]) for key in self.keys()]

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.name, self.version)


METADATA_FILENAME = 'pydist.json'
WHEEL_METADATA_FILENAME = 'metadata.json'
LEGACY_METADATA_FILENAME = 'METADATA'


class Metadata(object):
    """
    The metadata of a release. This implementation uses 2.1
    metadata where possible. If not possible, it wraps a LegacyMetadata
    instance which handles the key-value metadata format.
    """

    METADATA_VERSION_MATCHER = re.compile(r'^\d+(\.\d+)*$')

    NAME_MATCHER = re.compile('^[0-9A-Z]([0-9A-Z_.-]*[0-9A-Z])?$', re.I)

    FIELDNAME_MATCHER = re.compile('^[A-Z]([0-9A-Z-]*[0-9A-Z])?$', re.I)

    VERSION_MATCHER = PEP440_VERSION_RE

    SUMMARY_MATCHER = re.compile('.{1,2047}')

    METADATA_VERSION = '2.0'

    GENERATOR = 'distlib (%s)' % __version__

    MANDATORY_KEYS = {
        'name': (),
        'version': (),
        'summary': ('legacy', ),
    }

    INDEX_KEYS = ('name version license summary description author '
                  'author_email keywords platform home_page classifiers '
                  'download_url')

    DEPENDENCY_KEYS = ('extras run_requires test_requires build_requires '
                       'dev_requires provides meta_requires obsoleted_by '
                       'supports_environments')

    SYNTAX_VALIDATORS = {
        'metadata_version': (METADATA_VERSION_MATCHER, ()),
        'name': (NAME_MATCHER, ('legacy', )),
        'version': (VERSION_MATCHER, ('legacy', )),
        'summary': (SUMMARY_MATCHER, ('legacy', )),
        'dynamic': (FIELDNAME_MATCHER, ('legacy', )),
    }

    __slots__ = ('_legacy', '_data', 'scheme')

    def __init__(self, path=None, fileobj=None, mapping=None, scheme='default'):
        if [path, fileobj, mapping].count(None) < 2:
            raise TypeError('path, fileobj and mapping are exclusive')
        self._legacy = None
        self._data = None
        self.scheme = scheme
        # import pdb; pdb.set_trace()
        if mapping is not None:
            try:
                self._validate_mapping(mapping, scheme)
                self._data = mapping
            except MetadataUnrecognizedVersionError:
                self._legacy = LegacyMetadata(mapping=mapping, scheme=scheme)
                self.validate()
        else:
            data = None
            if path:
                with open(path, 'rb') as f:
                    data = f.read()
            elif fileobj:
                data = fileobj.read()
            if data is None:
                # Initialised with no args - to be added
                self._data = {
                    'metadata_version': self.METADATA_VERSION,
                    'generator': self.GENERATOR,
                }
            else:
                if not isinstance(data, text_type):
                    data = data.decode('utf-8')
                try:
                    self._data = json.loads(data)
                    self._validate_mapping(self._data, scheme)
                except ValueError:
                    # Note: MetadataUnrecognizedVersionError does not
                    # inherit from ValueError (it's a DistlibException,
                    # which should not inherit from ValueError).
                    # The ValueError comes from the json.load - if that
                    # succeeds and we get a validation error, we want
                    # that to propagate
                    self._legacy = LegacyMetadata(fileobj=StringIO(data), scheme=scheme)
                    self.validate()

    common_keys = set(('name', 'version', 'license', 'keywords', 'summary'))

    none_list = (None, list)
    none_dict = (None, dict)

    mapped_keys = {
        'run_requires': ('Requires-Dist', list),
        'build_requires': ('Setup-Requires-Dist', list),
        'dev_requires': none_list,
        'test_requires': none_list,
        'meta_requires': none_list,
        'extras': ('Provides-Extra', list),
        'modules': none_list,
        'namespaces': none_list,
        'exports': none_dict,
        'commands': none_dict,
        'classifiers': ('Classifier', list),
        'source_url': ('Download-URL', None),
        'metadata_version': ('Metadata-Version', None),
    }

    del none_list, none_dict

    def __getattribute__(self, key):
        common = object.__getattribute__(self, 'common_keys')
        mapped = object.__getattribute__(self, 'mapped_keys')
        if key in mapped:
            lk, maker = mapped[key]
            if self._legacy:
                if lk is None:
                    result = None if maker is None else maker()
                else:
                    result = self._legacy.get(lk)
            else:
                value = None if maker is None else maker()
                if key not in ('commands', 'exports', 'modules', 'namespaces', 'classifiers'):
                    result = self._data.get(key, value)
                else:
                    # special cases for PEP 459
                    sentinel = object()
                    result = sentinel
                    d = self._data.get('extensions')
                    if d:
                        if key == 'commands':
                            result = d.get('python.commands', value)
                        elif key == 'classifiers':
                            d = d.get('python.details')
                            if d:
                                result = d.get(key, value)
                        else:
                            d = d.get('python.exports')
                            if not d:
                                d = self._data.get('python.exports')
                            if d:
                                result = d.get(key, value)
                    if result is sentinel:
                        result = value
        elif key not in common:
            result = object.__getattribute__(self, key)
        elif self._legacy:
            result = self._legacy.get(key)
        else:
            result = self._data.get(key)
        return result

    def _validate_value(self, key, value, scheme=None):
        if key in self.SYNTAX_VALIDATORS:
            pattern, exclusions = self.SYNTAX_VALIDATORS[key]
            if (scheme or self.scheme) not in exclusions:
                m = pattern.match(value)
                if not m:
                    raise MetadataInvalidError("'%s' is an invalid value for "
                                               "the '%s' property" % (value, key))

    def __setattr__(self, key, value):
        self._validate_value(key, value)
        common = object.__getattribute__(self, 'common_keys')
        mapped = object.__getattribute__(self, 'mapped_keys')
        if key in mapped:
            lk, _ = mapped[key]
            if self._legacy:
                if lk is None:
                    raise NotImplementedError
                self._legacy[lk] = value
            elif key not in ('commands', 'exports', 'modules', 'namespaces', 'classifiers'):
                self._data[key] = value
            else:
                # special cases for PEP 459
                d = self._data.setdefault('extensions', {})
                if key == 'commands':
                    d['python.commands'] = value
                elif key == 'classifiers':
                    d = d.setdefault('python.details', {})
                    d[key] = value
                else:
                    d = d.setdefault('python.exports', {})
                    d[key] = value
        elif key not in common:
            object.__setattr__(self, key, value)
        else:
            if key == 'keywords':
                if isinstance(value, string_types):
                    value = value.strip()
                    if value:
                        value = value.split()
                    else:
                        value = []
            if self._legacy:
                self._legacy[key] = value
            else:
                self._data[key] = value

    @property
    def name_and_version(self):
        return _get_name_and_version(self.name, self.version, True)

    @property
    def provides(self):
        if self._legacy:
            result = self._legacy['Provides-Dist']
        else:
            result = self._data.setdefault('provides', [])
        s = '%s (%s)' % (self.name, self.version)
        if s not in result:
            result.append(s)
        return result

    @provides.setter
    def provides(self, value):
        if self._legacy:
            self._legacy['Provides-Dist'] = value
        else:
            self._data['provides'] = value

    def get_requirements(self, reqts, extras=None, env=None):
        """
        Base method to get dependencies, given a set of extras
        to satisfy and an optional environment context.
        :param reqts: A list of sometimes-wanted dependencies,
                      perhaps dependent on extras and environment.
        :param extras: A list of optional components being requested.
        :param env: An optional environment for marker evaluation.
        """
        if self._legacy:
            result = reqts
        else:
            result = []
            extras = get_extras(extras or [], self.extras)
            for d in reqts:
                if 'extra' not in d and 'environment' not in d:
                    # unconditional
                    include = True
                else:
                    if 'extra' not in d:
                        # Not extra-dependent - only environment-dependent
                        include = True
                    else:
                        include = d.get('extra') in extras
                    if include:
                        # Not excluded because of extras, check environment
                        marker = d.get('environment')
                        if marker:
                            include = interpret(marker, env)
                if include:
                    result.extend(d['requires'])
            for key in ('build', 'dev', 'test'):
                e = ':%s:' % key
                if e in extras:
                    extras.remove(e)
                    # A recursive call, but it should terminate since 'test'
                    # has been removed from the extras
                    reqts = self._data.get('%s_requires' % key, [])
                    result.extend(self.get_requirements(reqts, extras=extras, env=env))
        return result

    @property
    def dictionary(self):
        if self._legacy:
            return self._from_legacy()
        return self._data

    @property
    def dependencies(self):
        if self._legacy:
            raise NotImplementedError
        else:
            return extract_by_key(self._data, self.DEPENDENCY_KEYS)

    @dependencies.setter
    def dependencies(self, value):
        if self._legacy:
            raise NotImplementedError
        else:
            self._data.update(value)

    def _validate_mapping(self, mapping, scheme):
        if mapping.get('metadata_version') != self.METADATA_VERSION:
            raise MetadataUnrecognizedVersionError()
        missing = []
        for key, exclusions in self.MANDATORY_KEYS.items():
            if key not in mapping:
                if scheme not in exclusions:
                    missing.append(key)
        if missing:
            msg = 'Missing metadata items: %s' % ', '.join(missing)
            raise MetadataMissingError(msg)
        for k, v in mapping.items():
            self._validate_value(k, v, scheme)

    def validate(self):
        if self._legacy:
            missing, warnings = self._legacy.check(True)
            if missing or warnings:
                logger.warning('Metadata: missing: %s, warnings: %s', missing, warnings)
        else:
            self._validate_mapping(self._data, self.scheme)

    def todict(self):
        if self._legacy:
            return self._legacy.todict(True)
        else:
            result = extract_by_key(self._data, self.INDEX_KEYS)
            return result

    def _from_legacy(self):
        assert self._legacy and not self._data
        result = {
            'metadata_version': self.METADATA_VERSION,
            'generator': self.GENERATOR,
        }
        lmd = self._legacy.todict(True)  # skip missing ones
        for k in ('name', 'version', 'license', 'summary', 'description', 'classifier'):
            if k in lmd:
                if k == 'classifier':
                    nk = 'classifiers'
                else:
                    nk = k
                result[nk] = lmd[k]
        kw = lmd.get('Keywords', [])
        if kw == ['']:
            kw = []
        result['keywords'] = kw
        keys = (('requires_dist', 'run_requires'), ('setup_requires_dist', 'build_requires'))
        for ok, nk in keys:
            if ok in lmd and lmd[ok]:
                result[nk] = [{'requires': lmd[ok]}]
        result['provides'] = self.provides
        # author = {}
        # maintainer = {}
        return result

    LEGACY_MAPPING = {
        'name': 'Name',
        'version': 'Version',
        ('extensions', 'python.details', 'license'): 'License',
        'summary': 'Summary',
        'description': 'Description',
        ('extensions', 'python.project', 'project_urls', 'Home'): 'Home-page',
        ('extensions', 'python.project', 'contacts', 0, 'name'): 'Author',
        ('extensions', 'python.project', 'contacts', 0, 'email'): 'Author-email',
        'source_url': 'Download-URL',
        ('extensions', 'python.details', 'classifiers'): 'Classifier',
    }

    def _to_legacy(self):

        def process_entries(entries):
            reqts = set()
            for e in entries:
                extra = e.get('extra')
                env = e.get('environment')
                rlist = e['requires']
                for r in rlist:
                    if not env and not extra:
                        reqts.add(r)
                    else:
                        marker = ''
                        if extra:
                            marker = 'extra == "%s"' % extra
                        if env:
                            if marker:
                                marker = '(%s) and %s' % (env, marker)
                            else:
                                marker = env
                        reqts.add(';'.join((r, marker)))
            return reqts

        assert self._data and not self._legacy
        result = LegacyMetadata()
        nmd = self._data
        # import pdb; pdb.set_trace()
        for nk, ok in self.LEGACY_MAPPING.items():
            if not isinstance(nk, tuple):
                if nk in nmd:
                    result[ok] = nmd[nk]
            else:
                d = nmd
                found = True
                for k in nk:
                    try:
                        d = d[k]
                    except (KeyError, IndexError):
                        found = False
                        break
                if found:
                    result[ok] = d
        r1 = process_entries(self.run_requires + self.meta_requires)
        r2 = process_entries(self.build_requires + self.dev_requires)
        if self.extras:
            result['Provides-Extra'] = sorted(self.extras)
        result['Requires-Dist'] = sorted(r1)
        result['Setup-Requires-Dist'] = sorted(r2)
        # TODO: any other fields wanted
        return result

    def write(self, path=None, fileobj=None, legacy=False, skip_unknown=True):
        if [path, fileobj].count(None) != 1:
            raise ValueError('Exactly one of path and fileobj is needed')
        self.validate()
        if legacy:
            if self._legacy:
                legacy_md = self._legacy
            else:
                legacy_md = self._to_legacy()
            if path:
                legacy_md.write(path, skip_unknown=skip_unknown)
            else:
                legacy_md.write_file(fileobj, skip_unknown=skip_unknown)
        else:
            if self._legacy:
                d = self._from_legacy()
            else:
                d = self._data
            if fileobj:
                json.dump(d, fileobj, ensure_ascii=True, indent=2, sort_keys=True)
            else:
                with codecs.open(path, 'w', 'utf-8') as f:
                    json.dump(d, f, ensure_ascii=True, indent=2, sort_keys=True)

    def add_requirements(self, requirements):
        if self._legacy:
            self._legacy.add_requirements(requirements)
        else:
            run_requires = self._data.setdefault('run_requires', [])
            always = None
            for entry in run_requires:
                if 'environment' not in entry and 'extra' not in entry:
                    always = entry
                    break
            if always is None:
                always = {'requires': requirements}
                run_requires.insert(0, always)
            else:
                rset = set(always['requires']) | set(requirements)
                always['requires'] = sorted(rset)

    def __repr__(self):
        name = self.name or '(no name)'
        version = self.version or 'no version'
        return '<%s %s %s (%s)>' % (self.__class__.__name__, self.metadata_version, name, version)

# === NexusCore/openenv\Lib\site-packages\gitdb\pack.py ===
# Copyright (C) 2010, 2011 Sebastian Thiel (byronimo@gmail.com) and contributors
#
# This module is part of GitDB and is released under
# the New BSD License: https://opensource.org/license/bsd-3-clause/
"""Contains PackIndexFile and PackFile implementations"""
import zlib

from gitdb.exc import (
    BadObject,
    AmbiguousObjectName,
    UnsupportedOperation,
    ParseError
)

from gitdb.util import (
    mman,
    LazyMixin,
    unpack_from,
    bin_to_hex,
    byte_ord,
)

from gitdb.fun import (
    create_pack_object_header,
    pack_object_header_info,
    is_equal_canonical_sha,
    type_id_to_type_map,
    write_object,
    stream_copy,
    chunk_size,
    delta_types,
    OFS_DELTA,
    REF_DELTA,
    msb_size
)

try:
    from gitdb_speedups._perf import PackIndexFile_sha_to_index
except ImportError:
    pass
# END try c module

from gitdb.base import (      # Amazing !
    OInfo,
    OStream,
    OPackInfo,
    OPackStream,
    ODeltaStream,
    ODeltaPackInfo,
    ODeltaPackStream,
)

from gitdb.stream import (
    DecompressMemMapReader,
    DeltaApplyReader,
    Sha1Writer,
    NullStream,
    FlexibleSha1Writer
)

from struct import pack
from binascii import crc32

from gitdb.const import NULL_BYTE

import tempfile
import array
import os
import sys

__all__ = ('PackIndexFile', 'PackFile', 'PackEntity')


#{ Utilities

def pack_object_at(cursor, offset, as_stream):
    """
    :return: Tuple(abs_data_offset, PackInfo|PackStream)
        an object of the correct type according to the type_id  of the object.
        If as_stream is True, the object will contain a stream, allowing  the
        data to be read decompressed.
    :param data: random accessible data containing all required information
    :parma offset: offset in to the data at which the object information is located
    :param as_stream: if True, a stream object will be returned that can read
        the data, otherwise you receive an info object only"""
    data = cursor.use_region(offset).buffer()
    type_id, uncomp_size, data_rela_offset = pack_object_header_info(data)
    total_rela_offset = None                # set later, actual offset until data stream begins
    delta_info = None

    # OFFSET DELTA
    if type_id == OFS_DELTA:
        i = data_rela_offset
        c = byte_ord(data[i])
        i += 1
        delta_offset = c & 0x7f
        while c & 0x80:
            c = byte_ord(data[i])
            i += 1
            delta_offset += 1
            delta_offset = (delta_offset << 7) + (c & 0x7f)
        # END character loop
        delta_info = delta_offset
        total_rela_offset = i
    # REF DELTA
    elif type_id == REF_DELTA:
        total_rela_offset = data_rela_offset + 20
        delta_info = data[data_rela_offset:total_rela_offset]
    # BASE OBJECT
    else:
        # assume its a base object
        total_rela_offset = data_rela_offset
    # END handle type id
    abs_data_offset = offset + total_rela_offset
    if as_stream:
        stream = DecompressMemMapReader(data[total_rela_offset:], False, uncomp_size)
        if delta_info is None:
            return abs_data_offset, OPackStream(offset, type_id, uncomp_size, stream)
        else:
            return abs_data_offset, ODeltaPackStream(offset, type_id, uncomp_size, delta_info, stream)
    else:
        if delta_info is None:
            return abs_data_offset, OPackInfo(offset, type_id, uncomp_size)
        else:
            return abs_data_offset, ODeltaPackInfo(offset, type_id, uncomp_size, delta_info)
        # END handle info
    # END handle stream


def write_stream_to_pack(read, write, zstream, base_crc=None):
    """Copy a stream as read from read function, zip it, and write the result.
    Count the number of written bytes and return it
    :param base_crc: if not None, the crc will be the base for all compressed data
        we consecutively write and generate a crc32 from. If None, no crc will be generated
    :return: tuple(no bytes read, no bytes written, crc32) crc might be 0 if base_crc
        was false"""
    br = 0      # bytes read
    bw = 0      # bytes written
    want_crc = base_crc is not None
    crc = 0
    if want_crc:
        crc = base_crc
    # END initialize crc

    while True:
        chunk = read(chunk_size)
        br += len(chunk)
        compressed = zstream.compress(chunk)
        bw += len(compressed)
        write(compressed)           # cannot assume return value

        if want_crc:
            crc = crc32(compressed, crc)
        # END handle crc

        if len(chunk) != chunk_size:
            break
    # END copy loop

    compressed = zstream.flush()
    bw += len(compressed)
    write(compressed)
    if want_crc:
        crc = crc32(compressed, crc)
    # END handle crc

    return (br, bw, crc)


#} END utilities


class IndexWriter:

    """Utility to cache index information, allowing to write all information later
    in one go to the given stream
    **Note:** currently only writes v2 indices"""
    __slots__ = '_objs'

    def __init__(self):
        self._objs = list()

    def append(self, binsha, crc, offset):
        """Append one piece of object information"""
        self._objs.append((binsha, crc, offset))

    def write(self, pack_sha, write):
        """Write the index file using the given write method
        :param pack_sha: binary sha over the whole pack that we index
        :return: sha1 binary sha over all index file contents"""
        # sort for sha1 hash
        self._objs.sort(key=lambda o: o[0])

        sha_writer = FlexibleSha1Writer(write)
        sha_write = sha_writer.write
        sha_write(PackIndexFile.index_v2_signature)
        sha_write(pack(">L", PackIndexFile.index_version_default))

        # fanout
        tmplist = list((0,) * 256)                                # fanout or list with 64 bit offsets
        for t in self._objs:
            tmplist[byte_ord(t[0][0])] += 1
        # END prepare fanout
        for i in range(255):
            v = tmplist[i]
            sha_write(pack('>L', v))
            tmplist[i + 1] += v
        # END write each fanout entry
        sha_write(pack('>L', tmplist[255]))

        # sha1 ordered
        # save calls, that is push them into c
        sha_write(b''.join(t[0] for t in self._objs))

        # crc32
        for t in self._objs:
            sha_write(pack('>L', t[1] & 0xffffffff))
        # END for each crc

        tmplist = list()
        # offset 32
        for t in self._objs:
            ofs = t[2]
            if ofs > 0x7fffffff:
                tmplist.append(ofs)
                ofs = 0x80000000 + len(tmplist) - 1
            # END handle 64 bit offsets
            sha_write(pack('>L', ofs & 0xffffffff))
        # END for each offset

        # offset 64
        for ofs in tmplist:
            sha_write(pack(">Q", ofs))
        # END for each offset

        # trailer
        assert(len(pack_sha) == 20)
        sha_write(pack_sha)
        sha = sha_writer.sha(as_hex=False)
        write(sha)
        return sha


class PackIndexFile(LazyMixin):

    """A pack index provides offsets into the corresponding pack, allowing to find
    locations for offsets faster."""

    # Dont use slots as we dynamically bind functions for each version, need a dict for this
    # The slots you see here are just to keep track of our instance variables
    # __slots__ = ('_indexpath', '_fanout_table', '_cursor', '_version',
    #               '_sha_list_offset', '_crc_list_offset', '_pack_offset', '_pack_64_offset')

    # used in v2 indices
    _sha_list_offset = 8 + 1024
    index_v2_signature = b'\xfftOc'
    index_version_default = 2

    def __init__(self, indexpath):
        super().__init__()
        self._indexpath = indexpath

    def close(self):
        mman.force_map_handle_removal_win(self._indexpath)
        self._cursor = None

    def _set_cache_(self, attr):
        if attr == "_packfile_checksum":
            self._packfile_checksum = self._cursor.map()[-40:-20]
        elif attr == "_packfile_checksum":
            self._packfile_checksum = self._cursor.map()[-20:]
        elif attr == "_cursor":
            # Note: We don't lock the file when reading as we cannot be sure
            # that we can actually write to the location - it could be a read-only
            # alternate for instance
            self._cursor = mman.make_cursor(self._indexpath).use_region()
            # We will assume that the index will always fully fit into memory !
            if mman.window_size() > 0 and self._cursor.file_size() > mman.window_size():
                raise AssertionError("The index file at %s is too large to fit into a mapped window (%i > %i). This is a limitation of the implementation" % (
                    self._indexpath, self._cursor.file_size(), mman.window_size()))
            # END assert window size
        else:
            # now its time to initialize everything - if we are here, someone wants
            # to access the fanout table or related properties

            # CHECK VERSION
            mmap = self._cursor.map()
            self._version = (mmap[:4] == self.index_v2_signature and 2) or 1
            if self._version == 2:
                version_id = unpack_from(">L", mmap, 4)[0]
                assert version_id == self._version, "Unsupported index version: %i" % version_id
            # END assert version

            # SETUP FUNCTIONS
            # setup our functions according to the actual version
            for fname in ('entry', 'offset', 'sha', 'crc'):
                setattr(self, fname, getattr(self, "_%s_v%i" % (fname, self._version)))
            # END for each function to initialize

            # INITIALIZE DATA
            # byte offset is 8 if version is 2, 0 otherwise
            self._initialize()
        # END handle attributes

    #{ Access V1

    def _entry_v1(self, i):
        """:return: tuple(offset, binsha, 0)"""
        return unpack_from(">L20s", self._cursor.map(), 1024 + i * 24) + (0, )

    def _offset_v1(self, i):
        """see ``_offset_v2``"""
        return unpack_from(">L", self._cursor.map(), 1024 + i * 24)[0]

    def _sha_v1(self, i):
        """see ``_sha_v2``"""
        base = 1024 + (i * 24) + 4
        return self._cursor.map()[base:base + 20]

    def _crc_v1(self, i):
        """unsupported"""
        return 0

    #} END access V1

    #{ Access V2
    def _entry_v2(self, i):
        """:return: tuple(offset, binsha, crc)"""
        return (self._offset_v2(i), self._sha_v2(i), self._crc_v2(i))

    def _offset_v2(self, i):
        """:return: 32 or 64 byte offset into pack files. 64 byte offsets will only
            be returned if the pack is larger than 4 GiB, or 2^32"""
        offset = unpack_from(">L", self._cursor.map(), self._pack_offset + i * 4)[0]

        # if the high-bit is set, this indicates that we have to lookup the offset
        # in the 64 bit region of the file. The current offset ( lower 31 bits )
        # are the index into it
        if offset & 0x80000000:
            offset = unpack_from(">Q", self._cursor.map(), self._pack_64_offset + (offset & ~0x80000000) * 8)[0]
        # END handle 64 bit offset

        return offset

    def _sha_v2(self, i):
        """:return: sha at the given index of this file index instance"""
        base = self._sha_list_offset + i * 20
        return self._cursor.map()[base:base + 20]

    def _crc_v2(self, i):
        """:return: 4 bytes crc for the object at index i"""
        return unpack_from(">L", self._cursor.map(), self._crc_list_offset + i * 4)[0]

    #} END access V2

    #{ Initialization

    def _initialize(self):
        """initialize base data"""
        self._fanout_table = self._read_fanout((self._version == 2) * 8)

        if self._version == 2:
            self._crc_list_offset = self._sha_list_offset + self.size() * 20
            self._pack_offset = self._crc_list_offset + self.size() * 4
            self._pack_64_offset = self._pack_offset + self.size() * 4
        # END setup base

    def _read_fanout(self, byte_offset):
        """Generate a fanout table from our data"""
        d = self._cursor.map()
        out = list()
        append = out.append
        for i in range(256):
            append(unpack_from('>L', d, byte_offset + i * 4)[0])
        # END for each entry
        return out

    #} END initialization

    #{ Properties
    def version(self):
        return self._version

    def size(self):
        """:return: amount of objects referred to by this index"""
        return self._fanout_table[255]

    def path(self):
        """:return: path to the packindexfile"""
        return self._indexpath

    def packfile_checksum(self):
        """:return: 20 byte sha representing the sha1 hash of the pack file"""
        return self._cursor.map()[-40:-20]

    def indexfile_checksum(self):
        """:return: 20 byte sha representing the sha1 hash of this index file"""
        return self._cursor.map()[-20:]

    def offsets(self):
        """:return: sequence of all offsets in the order in which they were written

        **Note:** return value can be random accessed, but may be immmutable"""
        if self._version == 2:
            # read stream to array, convert to tuple
            a = array.array('I')    # 4 byte unsigned int, long are 8 byte on 64 bit it appears
            a.frombytes(self._cursor.map()[self._pack_offset:self._pack_64_offset])

            # networkbyteorder to something array likes more
            if sys.byteorder == 'little':
                a.byteswap()
            return a
        else:
            return tuple(self.offset(index) for index in range(self.size()))
        # END handle version

    def sha_to_index(self, sha):
        """
        :return: index usable with the ``offset`` or ``entry`` method, or None
            if the sha was not found in this pack index
        :param sha: 20 byte sha to lookup"""
        first_byte = byte_ord(sha[0])
        get_sha = self.sha
        lo = 0                  # lower index, the left bound of the bisection
        if first_byte != 0:
            lo = self._fanout_table[first_byte - 1]
        hi = self._fanout_table[first_byte]     # the upper, right bound of the bisection

        # bisect until we have the sha
        while lo < hi:
            mid = (lo + hi) // 2
            mid_sha = get_sha(mid)
            if sha < mid_sha:
                hi = mid
            elif sha == mid_sha:
                return mid
            else:
                lo = mid + 1
            # END handle midpoint
        # END bisect
        return None

    def partial_sha_to_index(self, partial_bin_sha, canonical_length):
        """
        :return: index as in `sha_to_index` or None if the sha was not found in this
            index file
        :param partial_bin_sha: an at least two bytes of a partial binary sha as bytes
        :param canonical_length: length of the original hexadecimal representation of the
            given partial binary sha
        :raise AmbiguousObjectName:"""
        if len(partial_bin_sha) < 2:
            raise ValueError("Require at least 2 bytes of partial sha")

        assert isinstance(partial_bin_sha, bytes), "partial_bin_sha must be bytes"
        first_byte = byte_ord(partial_bin_sha[0])

        get_sha = self.sha
        lo = 0                  # lower index, the left bound of the bisection
        if first_byte != 0:
            lo = self._fanout_table[first_byte - 1]
        hi = self._fanout_table[first_byte]     # the upper, right bound of the bisection

        # fill the partial to full 20 bytes
        filled_sha = partial_bin_sha + NULL_BYTE * (20 - len(partial_bin_sha))

        # find lowest
        while lo < hi:
            mid = (lo + hi) // 2
            mid_sha = get_sha(mid)
            if filled_sha < mid_sha:
                hi = mid
            elif filled_sha == mid_sha:
                # perfect match
                lo = mid
                break
            else:
                lo = mid + 1
            # END handle midpoint
        # END bisect

        if lo < self.size():
            cur_sha = get_sha(lo)
            if is_equal_canonical_sha(canonical_length, partial_bin_sha, cur_sha):
                next_sha = None
                if lo + 1 < self.size():
                    next_sha = get_sha(lo + 1)
                if next_sha and next_sha == cur_sha:
                    raise AmbiguousObjectName(partial_bin_sha)
                return lo
            # END if we have a match
        # END if we found something
        return None

    if 'PackIndexFile_sha_to_index' in globals():
        # NOTE: Its just about 25% faster, the major bottleneck might be the attr
        # accesses
        def sha_to_index(self, sha):
            return PackIndexFile_sha_to_index(self, sha)
    # END redefine heavy-hitter with c version

    #} END properties


class PackFile(LazyMixin):

    """A pack is a file written according to the Version 2 for git packs

    As we currently use memory maps, it could be assumed that the maximum size of
    packs therefore is 32 bit on 32 bit systems. On 64 bit systems, this should be
    fine though.

    **Note:** at some point, this might be implemented using streams as well, or
    streams are an alternate path in the case memory maps cannot be created
    for some reason - one clearly doesn't want to read 10GB at once in that
    case"""

    __slots__ = ('_packpath', '_cursor', '_size', '_version')
    pack_signature = 0x5041434b     # 'PACK'
    pack_version_default = 2

    # offset into our data at which the first object starts
    first_object_offset = 3 * 4       # header bytes
    footer_size = 20                # final sha

    def __init__(self, packpath):
        self._packpath = packpath

    def close(self):
        mman.force_map_handle_removal_win(self._packpath)
        self._cursor = None

    def _set_cache_(self, attr):
        # we fill the whole cache, whichever attribute gets queried first
        self._cursor = mman.make_cursor(self._packpath).use_region()

        # read the header information
        type_id, self._version, self._size = unpack_from(">LLL", self._cursor.map(), 0)

        # TODO: figure out whether we should better keep the lock, or maybe
        # add a .keep file instead ?
        if type_id != self.pack_signature:
            raise ParseError("Invalid pack signature: %i" % type_id)

    def _iter_objects(self, start_offset, as_stream=True):
        """Handle the actual iteration of objects within this pack"""
        c = self._cursor
        content_size = c.file_size() - self.footer_size
        cur_offset = start_offset or self.first_object_offset

        null = NullStream()
        while cur_offset < content_size:
            data_offset, ostream = pack_object_at(c, cur_offset, True)
            # scrub the stream to the end - this decompresses the object, but yields
            # the amount of compressed bytes we need to get to the next offset

            stream_copy(ostream.read, null.write, ostream.size, chunk_size)
            assert ostream.stream._br == ostream.size
            cur_offset += (data_offset - ostream.pack_offset) + ostream.stream.compressed_bytes_read()

            # if a stream is requested, reset it beforehand
            # Otherwise return the Stream object directly, its derived from the
            # info object
            if as_stream:
                ostream.stream.seek(0)
            yield ostream
        # END until we have read everything

    #{ Pack Information

    def size(self):
        """:return: The amount of objects stored in this pack"""
        return self._size

    def version(self):
        """:return: the version of this pack"""
        return self._version

    def data(self):
        """
        :return: read-only data of this pack. It provides random access and usually
            is a memory map.
        :note: This method is unsafe as it returns a window into a file which might be larger than than the actual window size"""
        # can use map as we are starting at offset 0. Otherwise we would have to use buffer()
        return self._cursor.use_region().map()

    def checksum(self):
        """:return: 20 byte sha1 hash on all object sha's contained in this file"""
        return self._cursor.use_region(self._cursor.file_size() - 20).buffer()[:]

    def path(self):
        """:return: path to the packfile"""
        return self._packpath
    #} END pack information

    #{ Pack Specific

    def collect_streams(self, offset):
        """
        :return: list of pack streams which are required to build the object
            at the given offset. The first entry of the list is the object at offset,
            the last one is either a full object, or a REF_Delta stream. The latter
            type needs its reference object to be locked up in an ODB to form a valid
            delta chain.
            If the object at offset is no delta, the size of the list is 1.
        :param offset: specifies the first byte of the object within this pack"""
        out = list()
        c = self._cursor
        while True:
            ostream = pack_object_at(c, offset, True)[1]
            out.append(ostream)
            if ostream.type_id == OFS_DELTA:
                offset = ostream.pack_offset - ostream.delta_info
            else:
                # the only thing we can lookup are OFFSET deltas. Everything
                # else is either an object, or a ref delta, in the latter
                # case someone else has to find it
                break
            # END handle type
        # END while chaining streams
        return out

    #} END pack specific

    #{ Read-Database like Interface

    def info(self, offset):
        """Retrieve information about the object at the given file-absolute offset

        :param offset: byte offset
        :return: OPackInfo instance, the actual type differs depending on the type_id attribute"""
        return pack_object_at(self._cursor, offset or self.first_object_offset, False)[1]

    def stream(self, offset):
        """Retrieve an object at the given file-relative offset as stream along with its information

        :param offset: byte offset
        :return: OPackStream instance, the actual type differs depending on the type_id attribute"""
        return pack_object_at(self._cursor, offset or self.first_object_offset, True)[1]

    def stream_iter(self, start_offset=0):
        """
        :return: iterator yielding OPackStream compatible instances, allowing
            to access the data in the pack directly.
        :param start_offset: offset to the first object to iterate. If 0, iteration
            starts at the very first object in the pack.

        **Note:** Iterating a pack directly is costly as the datastream has to be decompressed
        to determine the bounds between the objects"""
        return self._iter_objects(start_offset, as_stream=True)

    #} END Read-Database like Interface


class PackEntity(LazyMixin):

    """Combines the PackIndexFile and the PackFile into one, allowing the
    actual objects to be resolved and iterated"""

    __slots__ = ('_index',           # our index file
                 '_pack',            # our pack file
                 '_offset_map'       # on demand dict mapping one offset to the next consecutive one
                 )

    IndexFileCls = PackIndexFile
    PackFileCls = PackFile

    def __init__(self, pack_or_index_path):
        """Initialize ourselves with the path to the respective pack or index file"""
        basename, ext = os.path.splitext(pack_or_index_path)
        self._index = self.IndexFileCls("%s.idx" % basename)            # PackIndexFile instance
        self._pack = self.PackFileCls("%s.pack" % basename)         # corresponding PackFile instance

    def close(self):
        self._index.close()
        self._pack.close()

    def _set_cache_(self, attr):
        # currently this can only be _offset_map
        # TODO: make this a simple sorted offset array which can be bisected
        # to find the respective entry, from which we can take a +1 easily
        # This might be slower, but should also be much lighter in memory !
        offsets_sorted = sorted(self._index.offsets())
        last_offset = len(self._pack.data()) - self._pack.footer_size
        assert offsets_sorted, "Cannot handle empty indices"

        offset_map = None
        if len(offsets_sorted) == 1:
            offset_map = {offsets_sorted[0]: last_offset}
        else:
            iter_offsets = iter(offsets_sorted)
            iter_offsets_plus_one = iter(offsets_sorted)
            next(iter_offsets_plus_one)
            consecutive = zip(iter_offsets, iter_offsets_plus_one)

            offset_map = dict(consecutive)

            # the last offset is not yet set
            offset_map[offsets_sorted[-1]] = last_offset
        # END handle offset amount
        self._offset_map = offset_map

    def _sha_to_index(self, sha):
        """:return: index for the given sha, or raise"""
        index = self._index.sha_to_index(sha)
        if index is None:
            raise BadObject(sha)
        return index

    def _iter_objects(self, as_stream):
        """Iterate over all objects in our index and yield their OInfo or OStream instences"""
        _sha = self._index.sha
        _object = self._object
        for index in range(self._index.size()):
            yield _object(_sha(index), as_stream, index)
        # END for each index

    def _object(self, sha, as_stream, index=-1):
        """:return: OInfo or OStream object providing information about the given sha
        :param index: if not -1, its assumed to be the sha's index in the IndexFile"""
        # its a little bit redundant here, but it needs to be efficient
        if index < 0:
            index = self._sha_to_index(sha)
        if sha is None:
            sha = self._index.sha(index)
        # END assure sha is present ( in output )
        offset = self._index.offset(index)
        type_id, uncomp_size, data_rela_offset = pack_object_header_info(self._pack._cursor.use_region(offset).buffer())
        if as_stream:
            if type_id not in delta_types:
                packstream = self._pack.stream(offset)
                return OStream(sha, packstream.type, packstream.size, packstream.stream)
            # END handle non-deltas

            # produce a delta stream containing all info
            # To prevent it from applying the deltas when querying the size,
            # we extract it from the delta stream ourselves
            streams = self.collect_streams_at_offset(offset)
            dstream = DeltaApplyReader.new(streams)

            return ODeltaStream(sha, dstream.type, None, dstream)
        else:
            if type_id not in delta_types:
                return OInfo(sha, type_id_to_type_map[type_id], uncomp_size)
            # END handle non-deltas

            # deltas are a little tougher - unpack the first bytes to obtain
            # the actual target size, as opposed to the size of the delta data
            streams = self.collect_streams_at_offset(offset)
            buf = streams[0].read(512)
            offset, src_size = msb_size(buf)
            offset, target_size = msb_size(buf, offset)

            # collect the streams to obtain the actual object type
            if streams[-1].type_id in delta_types:
                raise BadObject(sha, "Could not resolve delta object")
            return OInfo(sha, streams[-1].type, target_size)
        # END handle stream

    #{ Read-Database like Interface

    def info(self, sha):
        """Retrieve information about the object identified by the given sha

        :param sha: 20 byte sha1
        :raise BadObject:
        :return: OInfo instance, with 20 byte sha"""
        return self._object(sha, False)

    def stream(self, sha):
        """Retrieve an object stream along with its information as identified by the given sha

        :param sha: 20 byte sha1
        :raise BadObject:
        :return: OStream instance, with 20 byte sha"""
        return self._object(sha, True)

    def info_at_index(self, index):
        """As ``info``, but uses a PackIndexFile compatible index to refer to the object"""
        return self._object(None, False, index)

    def stream_at_index(self, index):
        """As ``stream``, but uses a PackIndexFile compatible index to refer to the
        object"""
        return self._object(None, True, index)

    #} END Read-Database like Interface

    #{ Interface

    def pack(self):
        """:return: the underlying pack file instance"""
        return self._pack

    def index(self):
        """:return: the underlying pack index file instance"""
        return self._index

    def is_valid_stream(self, sha, use_crc=False):
        """
        Verify that the stream at the given sha is valid.

        :param use_crc: if True, the index' crc is run over the compressed stream of
            the object, which is much faster than checking the sha1. It is also
            more prone to unnoticed corruption or manipulation.
        :param sha: 20 byte sha1 of the object whose stream to verify
            whether the compressed stream of the object is valid. If it is
            a delta, this only verifies that the delta's data is valid, not the
            data of the actual undeltified object, as it depends on more than
            just this stream.
            If False, the object will be decompressed and the sha generated. It must
            match the given sha

        :return: True if the stream is valid
        :raise UnsupportedOperation: If the index is version 1 only
        :raise BadObject: sha was not found"""
        if use_crc:
            if self._index.version() < 2:
                raise UnsupportedOperation("Version 1 indices do not contain crc's, verify by sha instead")
            # END handle index version

            index = self._sha_to_index(sha)
            offset = self._index.offset(index)
            next_offset = self._offset_map[offset]
            crc_value = self._index.crc(index)

            # create the current crc value, on the compressed object data
            # Read it in chunks, without copying the data
            crc_update = zlib.crc32
            pack_data = self._pack.data()
            cur_pos = offset
            this_crc_value = 0
            while cur_pos < next_offset:
                rbound = min(cur_pos + chunk_size, next_offset)
                size = rbound - cur_pos
                this_crc_value = crc_update(pack_data[cur_pos:cur_pos + size], this_crc_value)
                cur_pos += size
            # END window size loop

            # crc returns signed 32 bit numbers, the AND op forces it into unsigned
            # mode ... wow, sneaky, from dulwich.
            return (this_crc_value & 0xffffffff) == crc_value
        else:
            shawriter = Sha1Writer()
            stream = self._object(sha, as_stream=True)
            # write a loose object, which is the basis for the sha
            write_object(stream.type, stream.size, stream.read, shawriter.write)

            assert shawriter.sha(as_hex=False) == sha
            return shawriter.sha(as_hex=False) == sha
        # END handle crc/sha verification
        return True

    def info_iter(self):
        """
        :return: Iterator over all objects in this pack. The iterator yields
            OInfo instances"""
        return self._iter_objects(as_stream=False)

    def stream_iter(self):
        """
        :return: iterator over all objects in this pack. The iterator yields
            OStream instances"""
        return self._iter_objects(as_stream=True)

    def collect_streams_at_offset(self, offset):
        """
        As the version in the PackFile, but can resolve REF deltas within this pack
        For more info, see ``collect_streams``

        :param offset: offset into the pack file at which the object can be found"""
        streams = self._pack.collect_streams(offset)

        # try to resolve the last one if needed. It is assumed to be either
        # a REF delta, or a base object, as OFFSET deltas are resolved by the pack
        if streams[-1].type_id == REF_DELTA:
            stream = streams[-1]
            while stream.type_id in delta_types:
                if stream.type_id == REF_DELTA:
                    # smmap can return memory view objects, which can't be compared as buffers/bytes can ...
                    if isinstance(stream.delta_info, memoryview):
                        sindex = self._index.sha_to_index(stream.delta_info.tobytes())
                    else:
                        sindex = self._index.sha_to_index(stream.delta_info)
                    if sindex is None:
                        break
                    stream = self._pack.stream(self._index.offset(sindex))
                    streams.append(stream)
                else:
                    # must be another OFS DELTA - this could happen if a REF
                    # delta we resolve previously points to an OFS delta. Who
                    # would do that ;) ? We can handle it though
                    stream = self._pack.stream(stream.delta_info)
                    streams.append(stream)
                # END handle ref delta
            # END resolve ref streams
        # END resolve streams

        return streams

    def collect_streams(self, sha):
        """
        As ``PackFile.collect_streams``, but takes a sha instead of an offset.
        Additionally, ref_delta streams will be resolved within this pack.
        If this is not possible, the stream will be left alone, hence it is adivsed
        to check for unresolved ref-deltas and resolve them before attempting to
        construct a delta stream.

        :param sha: 20 byte sha1 specifying the object whose related streams you want to collect
        :return: list of streams, first being the actual object delta, the last being
            a possibly unresolved base object.
        :raise BadObject:"""
        return self.collect_streams_at_offset(self._index.offset(self._sha_to_index(sha)))

    @classmethod
    def write_pack(cls, object_iter, pack_write, index_write=None,
                   object_count=None, zlib_compression=zlib.Z_BEST_SPEED):
        """
        Create a new pack by putting all objects obtained by the object_iterator
        into a pack which is written using the pack_write method.
        The respective index is produced as well if index_write is not Non.

        :param object_iter: iterator yielding odb output objects
        :param pack_write: function to receive strings to write into the pack stream
        :param indx_write: if not None, the function writes the index file corresponding
            to the pack.
        :param object_count: if you can provide the amount of objects in your iteration,
            this would be the place to put it. Otherwise we have to pre-iterate and store
            all items into a list to get the number, which uses more memory than necessary.
        :param zlib_compression: the zlib compression level to use
        :return: tuple(pack_sha, index_binsha) binary sha over all the contents of the pack
            and over all contents of the index. If index_write was None, index_binsha will be None

        **Note:** The destination of the write functions is up to the user. It could
        be a socket, or a file for instance

        **Note:** writes only undeltified objects"""
        objs = object_iter
        if not object_count:
            if not isinstance(object_iter, (tuple, list)):
                objs = list(object_iter)
            # END handle list type
            object_count = len(objs)
        # END handle object

        pack_writer = FlexibleSha1Writer(pack_write)
        pwrite = pack_writer.write
        ofs = 0                                         # current offset into the pack file
        index = None
        wants_index = index_write is not None

        # write header
        pwrite(pack('>LLL', PackFile.pack_signature, PackFile.pack_version_default, object_count))
        ofs += 12

        if wants_index:
            index = IndexWriter()
        # END handle index header

        actual_count = 0
        for obj in objs:
            actual_count += 1
            crc = 0

            # object header
            hdr = create_pack_object_header(obj.type_id, obj.size)
            if index_write:
                crc = crc32(hdr)
            else:
                crc = None
            # END handle crc
            pwrite(hdr)

            # data stream
            zstream = zlib.compressobj(zlib_compression)
            ostream = obj.stream
            br, bw, crc = write_stream_to_pack(ostream.read, pwrite, zstream, base_crc=crc)
            assert(br == obj.size)
            if wants_index:
                index.append(obj.binsha, crc, ofs)
            # END handle index

            ofs += len(hdr) + bw
            if actual_count == object_count:
                break
            # END abort once we are done
        # END for each object

        if actual_count != object_count:
            raise ValueError(
                "Expected to write %i objects into pack, but received only %i from iterators" % (object_count, actual_count))
        # END count assertion

        # write footer
        pack_sha = pack_writer.sha(as_hex=False)
        assert len(pack_sha) == 20
        pack_write(pack_sha)
        ofs += len(pack_sha)                            # just for completeness ;)

        index_sha = None
        if wants_index:
            index_sha = index.write(pack_sha, index_write)
        # END handle index

        return pack_sha, index_sha

    @classmethod
    def create(cls, object_iter, base_dir, object_count=None, zlib_compression=zlib.Z_BEST_SPEED):
        """Create a new on-disk entity comprised of a properly named pack file and a properly named
        and corresponding index file. The pack contains all OStream objects contained in object iter.
        :param base_dir: directory which is to contain the files
        :return: PackEntity instance initialized with the new pack

        **Note:** for more information on the other parameters see the write_pack method"""
        pack_fd, pack_path = tempfile.mkstemp('', 'pack', base_dir)
        index_fd, index_path = tempfile.mkstemp('', 'index', base_dir)
        pack_write = lambda d: os.write(pack_fd, d)
        index_write = lambda d: os.write(index_fd, d)

        pack_binsha, index_binsha = cls.write_pack(object_iter, pack_write, index_write, object_count, zlib_compression)
        os.close(pack_fd)
        os.close(index_fd)

        fmt = "pack-%s.%s"
        new_pack_path = os.path.join(base_dir, fmt % (bin_to_hex(pack_binsha), 'pack'))
        new_index_path = os.path.join(base_dir, fmt % (bin_to_hex(pack_binsha), 'idx'))
        os.rename(pack_path, new_pack_path)
        os.rename(index_path, new_index_path)

        return cls(new_pack_path)

    #} END interface

# === NexusCore/openenv\Lib\site-packages\pip\_vendor\distlib\metadata.py ===
# -*- coding: utf-8 -*-
#
# Copyright (C) 2012 The Python Software Foundation.
# See LICENSE.txt and CONTRIBUTORS.txt.
#
"""Implementation of the Metadata for Python packages PEPs.

Supports all metadata formats (1.0, 1.1, 1.2, 1.3/2.1 and 2.2).
"""
from __future__ import unicode_literals

import codecs
from email import message_from_file
import json
import logging
import re

from . import DistlibException, __version__
from .compat import StringIO, string_types, text_type
from .markers import interpret
from .util import extract_by_key, get_extras
from .version import get_scheme, PEP440_VERSION_RE

logger = logging.getLogger(__name__)


class MetadataMissingError(DistlibException):
    """A required metadata is missing"""


class MetadataConflictError(DistlibException):
    """Attempt to read or write metadata fields that are conflictual."""


class MetadataUnrecognizedVersionError(DistlibException):
    """Unknown metadata version number."""


class MetadataInvalidError(DistlibException):
    """A metadata value is invalid"""


# public API of this module
__all__ = ['Metadata', 'PKG_INFO_ENCODING', 'PKG_INFO_PREFERRED_VERSION']

# Encoding used for the PKG-INFO files
PKG_INFO_ENCODING = 'utf-8'

# preferred version. Hopefully will be changed
# to 1.2 once PEP 345 is supported everywhere
PKG_INFO_PREFERRED_VERSION = '1.1'

_LINE_PREFIX_1_2 = re.compile('\n       \\|')
_LINE_PREFIX_PRE_1_2 = re.compile('\n        ')
_241_FIELDS = ('Metadata-Version', 'Name', 'Version', 'Platform', 'Summary', 'Description', 'Keywords', 'Home-page',
               'Author', 'Author-email', 'License')

_314_FIELDS = ('Metadata-Version', 'Name', 'Version', 'Platform', 'Supported-Platform', 'Summary', 'Description',
               'Keywords', 'Home-page', 'Author', 'Author-email', 'License', 'Classifier', 'Download-URL', 'Obsoletes',
               'Provides', 'Requires')

_314_MARKERS = ('Obsoletes', 'Provides', 'Requires', 'Classifier', 'Download-URL')

_345_FIELDS = ('Metadata-Version', 'Name', 'Version', 'Platform', 'Supported-Platform', 'Summary', 'Description',
               'Keywords', 'Home-page', 'Author', 'Author-email', 'Maintainer', 'Maintainer-email', 'License',
               'Classifier', 'Download-URL', 'Obsoletes-Dist', 'Project-URL', 'Provides-Dist', 'Requires-Dist',
               'Requires-Python', 'Requires-External')

_345_MARKERS = ('Provides-Dist', 'Requires-Dist', 'Requires-Python', 'Obsoletes-Dist', 'Requires-External',
                'Maintainer', 'Maintainer-email', 'Project-URL')

_426_FIELDS = ('Metadata-Version', 'Name', 'Version', 'Platform', 'Supported-Platform', 'Summary', 'Description',
               'Keywords', 'Home-page', 'Author', 'Author-email', 'Maintainer', 'Maintainer-email', 'License',
               'Classifier', 'Download-URL', 'Obsoletes-Dist', 'Project-URL', 'Provides-Dist', 'Requires-Dist',
               'Requires-Python', 'Requires-External', 'Private-Version', 'Obsoleted-By', 'Setup-Requires-Dist',
               'Extension', 'Provides-Extra')

_426_MARKERS = ('Private-Version', 'Provides-Extra', 'Obsoleted-By', 'Setup-Requires-Dist', 'Extension')

# See issue #106: Sometimes 'Requires' and 'Provides' occur wrongly in
# the metadata. Include them in the tuple literal below to allow them
# (for now).
# Ditto for Obsoletes - see issue #140.
_566_FIELDS = _426_FIELDS + ('Description-Content-Type', 'Requires', 'Provides', 'Obsoletes')

_566_MARKERS = ('Description-Content-Type', )

_643_MARKERS = ('Dynamic', 'License-File')

_643_FIELDS = _566_FIELDS + _643_MARKERS

_ALL_FIELDS = set()
_ALL_FIELDS.update(_241_FIELDS)
_ALL_FIELDS.update(_314_FIELDS)
_ALL_FIELDS.update(_345_FIELDS)
_ALL_FIELDS.update(_426_FIELDS)
_ALL_FIELDS.update(_566_FIELDS)
_ALL_FIELDS.update(_643_FIELDS)

EXTRA_RE = re.compile(r'''extra\s*==\s*("([^"]+)"|'([^']+)')''')


def _version2fieldlist(version):
    if version == '1.0':
        return _241_FIELDS
    elif version == '1.1':
        return _314_FIELDS
    elif version == '1.2':
        return _345_FIELDS
    elif version in ('1.3', '2.1'):
        # avoid adding field names if already there
        return _345_FIELDS + tuple(f for f in _566_FIELDS if f not in _345_FIELDS)
    elif version == '2.0':
        raise ValueError('Metadata 2.0 is withdrawn and not supported')
        # return _426_FIELDS
    elif version == '2.2':
        return _643_FIELDS
    raise MetadataUnrecognizedVersionError(version)


def _best_version(fields):
    """Detect the best version depending on the fields used."""

    def _has_marker(keys, markers):
        return any(marker in keys for marker in markers)

    keys = [key for key, value in fields.items() if value not in ([], 'UNKNOWN', None)]
    possible_versions = ['1.0', '1.1', '1.2', '1.3', '2.1', '2.2']  # 2.0 removed

    # first let's try to see if a field is not part of one of the version
    for key in keys:
        if key not in _241_FIELDS and '1.0' in possible_versions:
            possible_versions.remove('1.0')
            logger.debug('Removed 1.0 due to %s', key)
        if key not in _314_FIELDS and '1.1' in possible_versions:
            possible_versions.remove('1.1')
            logger.debug('Removed 1.1 due to %s', key)
        if key not in _345_FIELDS and '1.2' in possible_versions:
            possible_versions.remove('1.2')
            logger.debug('Removed 1.2 due to %s', key)
        if key not in _566_FIELDS and '1.3' in possible_versions:
            possible_versions.remove('1.3')
            logger.debug('Removed 1.3 due to %s', key)
        if key not in _566_FIELDS and '2.1' in possible_versions:
            if key != 'Description':  # In 2.1, description allowed after headers
                possible_versions.remove('2.1')
                logger.debug('Removed 2.1 due to %s', key)
        if key not in _643_FIELDS and '2.2' in possible_versions:
            possible_versions.remove('2.2')
            logger.debug('Removed 2.2 due to %s', key)
        # if key not in _426_FIELDS and '2.0' in possible_versions:
        # possible_versions.remove('2.0')
        # logger.debug('Removed 2.0 due to %s', key)

    # possible_version contains qualified versions
    if len(possible_versions) == 1:
        return possible_versions[0]  # found !
    elif len(possible_versions) == 0:
        logger.debug('Out of options - unknown metadata set: %s', fields)
        raise MetadataConflictError('Unknown metadata set')

    # let's see if one unique marker is found
    is_1_1 = '1.1' in possible_versions and _has_marker(keys, _314_MARKERS)
    is_1_2 = '1.2' in possible_versions and _has_marker(keys, _345_MARKERS)
    is_2_1 = '2.1' in possible_versions and _has_marker(keys, _566_MARKERS)
    # is_2_0 = '2.0' in possible_versions and _has_marker(keys, _426_MARKERS)
    is_2_2 = '2.2' in possible_versions and _has_marker(keys, _643_MARKERS)
    if int(is_1_1) + int(is_1_2) + int(is_2_1) + int(is_2_2) > 1:
        raise MetadataConflictError('You used incompatible 1.1/1.2/2.1/2.2 fields')

    # we have the choice, 1.0, or 1.2, 2.1 or 2.2
    #   - 1.0 has a broken Summary field but works with all tools
    #   - 1.1 is to avoid
    #   - 1.2 fixes Summary but has little adoption
    #   - 2.1 adds more features
    #   - 2.2 is the latest
    if not is_1_1 and not is_1_2 and not is_2_1 and not is_2_2:
        # we couldn't find any specific marker
        if PKG_INFO_PREFERRED_VERSION in possible_versions:
            return PKG_INFO_PREFERRED_VERSION
    if is_1_1:
        return '1.1'
    if is_1_2:
        return '1.2'
    if is_2_1:
        return '2.1'
    # if is_2_2:
    # return '2.2'

    return '2.2'


# This follows the rules about transforming keys as described in
# https://www.python.org/dev/peps/pep-0566/#id17
_ATTR2FIELD = {name.lower().replace("-", "_"): name for name in _ALL_FIELDS}
_FIELD2ATTR = {field: attr for attr, field in _ATTR2FIELD.items()}

_PREDICATE_FIELDS = ('Requires-Dist', 'Obsoletes-Dist', 'Provides-Dist')
_VERSIONS_FIELDS = ('Requires-Python', )
_VERSION_FIELDS = ('Version', )
_LISTFIELDS = ('Platform', 'Classifier', 'Obsoletes', 'Requires', 'Provides', 'Obsoletes-Dist', 'Provides-Dist',
               'Requires-Dist', 'Requires-External', 'Project-URL', 'Supported-Platform', 'Setup-Requires-Dist',
               'Provides-Extra', 'Extension', 'License-File')
_LISTTUPLEFIELDS = ('Project-URL', )

_ELEMENTSFIELD = ('Keywords', )

_UNICODEFIELDS = ('Author', 'Maintainer', 'Summary', 'Description')

_MISSING = object()

_FILESAFE = re.compile('[^A-Za-z0-9.]+')


def _get_name_and_version(name, version, for_filename=False):
    """Return the distribution name with version.

    If for_filename is true, return a filename-escaped form."""
    if for_filename:
        # For both name and version any runs of non-alphanumeric or '.'
        # characters are replaced with a single '-'.  Additionally any
        # spaces in the version string become '.'
        name = _FILESAFE.sub('-', name)
        version = _FILESAFE.sub('-', version.replace(' ', '.'))
    return '%s-%s' % (name, version)


class LegacyMetadata(object):
    """The legacy metadata of a release.

    Supports versions 1.0, 1.1, 1.2, 2.0 and 1.3/2.1 (auto-detected). You can
    instantiate the class with one of these arguments (or none):
    - *path*, the path to a metadata file
    - *fileobj* give a file-like object with metadata as content
    - *mapping* is a dict-like object
    - *scheme* is a version scheme name
    """

    # TODO document the mapping API and UNKNOWN default key

    def __init__(self, path=None, fileobj=None, mapping=None, scheme='default'):
        if [path, fileobj, mapping].count(None) < 2:
            raise TypeError('path, fileobj and mapping are exclusive')
        self._fields = {}
        self.requires_files = []
        self._dependencies = None
        self.scheme = scheme
        if path is not None:
            self.read(path)
        elif fileobj is not None:
            self.read_file(fileobj)
        elif mapping is not None:
            self.update(mapping)
            self.set_metadata_version()

    def set_metadata_version(self):
        self._fields['Metadata-Version'] = _best_version(self._fields)

    def _write_field(self, fileobj, name, value):
        fileobj.write('%s: %s\n' % (name, value))

    def __getitem__(self, name):
        return self.get(name)

    def __setitem__(self, name, value):
        return self.set(name, value)

    def __delitem__(self, name):
        field_name = self._convert_name(name)
        try:
            del self._fields[field_name]
        except KeyError:
            raise KeyError(name)

    def __contains__(self, name):
        return (name in self._fields or self._convert_name(name) in self._fields)

    def _convert_name(self, name):
        if name in _ALL_FIELDS:
            return name
        name = name.replace('-', '_').lower()
        return _ATTR2FIELD.get(name, name)

    def _default_value(self, name):
        if name in _LISTFIELDS or name in _ELEMENTSFIELD:
            return []
        return 'UNKNOWN'

    def _remove_line_prefix(self, value):
        if self.metadata_version in ('1.0', '1.1'):
            return _LINE_PREFIX_PRE_1_2.sub('\n', value)
        else:
            return _LINE_PREFIX_1_2.sub('\n', value)

    def __getattr__(self, name):
        if name in _ATTR2FIELD:
            return self[name]
        raise AttributeError(name)

    #
    # Public API
    #

    def get_fullname(self, filesafe=False):
        """
        Return the distribution name with version.

        If filesafe is true, return a filename-escaped form.
        """
        return _get_name_and_version(self['Name'], self['Version'], filesafe)

    def is_field(self, name):
        """return True if name is a valid metadata key"""
        name = self._convert_name(name)
        return name in _ALL_FIELDS

    def is_multi_field(self, name):
        name = self._convert_name(name)
        return name in _LISTFIELDS

    def read(self, filepath):
        """Read the metadata values from a file path."""
        fp = codecs.open(filepath, 'r', encoding='utf-8')
        try:
            self.read_file(fp)
        finally:
            fp.close()

    def read_file(self, fileob):
        """Read the metadata values from a file object."""
        msg = message_from_file(fileob)
        self._fields['Metadata-Version'] = msg['metadata-version']

        # When reading, get all the fields we can
        for field in _ALL_FIELDS:
            if field not in msg:
                continue
            if field in _LISTFIELDS:
                # we can have multiple lines
                values = msg.get_all(field)
                if field in _LISTTUPLEFIELDS and values is not None:
                    values = [tuple(value.split(',')) for value in values]
                self.set(field, values)
            else:
                # single line
                value = msg[field]
                if value is not None and value != 'UNKNOWN':
                    self.set(field, value)

        # PEP 566 specifies that the body be used for the description, if
        # available
        body = msg.get_payload()
        self["Description"] = body if body else self["Description"]
        # logger.debug('Attempting to set metadata for %s', self)
        # self.set_metadata_version()

    def write(self, filepath, skip_unknown=False):
        """Write the metadata fields to filepath."""
        fp = codecs.open(filepath, 'w', encoding='utf-8')
        try:
            self.write_file(fp, skip_unknown)
        finally:
            fp.close()

    def write_file(self, fileobject, skip_unknown=False):
        """Write the PKG-INFO format data to a file object."""
        self.set_metadata_version()

        for field in _version2fieldlist(self['Metadata-Version']):
            values = self.get(field)
            if skip_unknown and values in ('UNKNOWN', [], ['UNKNOWN']):
                continue
            if field in _ELEMENTSFIELD:
                self._write_field(fileobject, field, ','.join(values))
                continue
            if field not in _LISTFIELDS:
                if field == 'Description':
                    if self.metadata_version in ('1.0', '1.1'):
                        values = values.replace('\n', '\n        ')
                    else:
                        values = values.replace('\n', '\n       |')
                values = [values]

            if field in _LISTTUPLEFIELDS:
                values = [','.join(value) for value in values]

            for value in values:
                self._write_field(fileobject, field, value)

    def update(self, other=None, **kwargs):
        """Set metadata values from the given iterable `other` and kwargs.

        Behavior is like `dict.update`: If `other` has a ``keys`` method,
        they are looped over and ``self[key]`` is assigned ``other[key]``.
        Else, ``other`` is an iterable of ``(key, value)`` iterables.

        Keys that don't match a metadata field or that have an empty value are
        dropped.
        """

        def _set(key, value):
            if key in _ATTR2FIELD and value:
                self.set(self._convert_name(key), value)

        if not other:
            # other is None or empty container
            pass
        elif hasattr(other, 'keys'):
            for k in other.keys():
                _set(k, other[k])
        else:
            for k, v in other:
                _set(k, v)

        if kwargs:
            for k, v in kwargs.items():
                _set(k, v)

    def set(self, name, value):
        """Control then set a metadata field."""
        name = self._convert_name(name)

        if ((name in _ELEMENTSFIELD or name == 'Platform') and not isinstance(value, (list, tuple))):
            if isinstance(value, string_types):
                value = [v.strip() for v in value.split(',')]
            else:
                value = []
        elif (name in _LISTFIELDS and not isinstance(value, (list, tuple))):
            if isinstance(value, string_types):
                value = [value]
            else:
                value = []

        if logger.isEnabledFor(logging.WARNING):
            project_name = self['Name']

            scheme = get_scheme(self.scheme)
            if name in _PREDICATE_FIELDS and value is not None:
                for v in value:
                    # check that the values are valid
                    if not scheme.is_valid_matcher(v.split(';')[0]):
                        logger.warning("'%s': '%s' is not valid (field '%s')", project_name, v, name)
            # FIXME this rejects UNKNOWN, is that right?
            elif name in _VERSIONS_FIELDS and value is not None:
                if not scheme.is_valid_constraint_list(value):
                    logger.warning("'%s': '%s' is not a valid version (field '%s')", project_name, value, name)
            elif name in _VERSION_FIELDS and value is not None:
                if not scheme.is_valid_version(value):
                    logger.warning("'%s': '%s' is not a valid version (field '%s')", project_name, value, name)

        if name in _UNICODEFIELDS:
            if name == 'Description':
                value = self._remove_line_prefix(value)

        self._fields[name] = value

    def get(self, name, default=_MISSING):
        """Get a metadata field."""
        name = self._convert_name(name)
        if name not in self._fields:
            if default is _MISSING:
                default = self._default_value(name)
            return default
        if name in _UNICODEFIELDS:
            value = self._fields[name]
            return value
        elif name in _LISTFIELDS:
            value = self._fields[name]
            if value is None:
                return []
            res = []
            for val in value:
                if name not in _LISTTUPLEFIELDS:
                    res.append(val)
                else:
                    # That's for Project-URL
                    res.append((val[0], val[1]))
            return res

        elif name in _ELEMENTSFIELD:
            value = self._fields[name]
            if isinstance(value, string_types):
                return value.split(',')
        return self._fields[name]

    def check(self, strict=False):
        """Check if the metadata is compliant. If strict is True then raise if
        no Name or Version are provided"""
        self.set_metadata_version()

        # XXX should check the versions (if the file was loaded)
        missing, warnings = [], []

        for attr in ('Name', 'Version'):  # required by PEP 345
            if attr not in self:
                missing.append(attr)

        if strict and missing != []:
            msg = 'missing required metadata: %s' % ', '.join(missing)
            raise MetadataMissingError(msg)

        for attr in ('Home-page', 'Author'):
            if attr not in self:
                missing.append(attr)

        # checking metadata 1.2 (XXX needs to check 1.1, 1.0)
        if self['Metadata-Version'] != '1.2':
            return missing, warnings

        scheme = get_scheme(self.scheme)

        def are_valid_constraints(value):
            for v in value:
                if not scheme.is_valid_matcher(v.split(';')[0]):
                    return False
            return True

        for fields, controller in ((_PREDICATE_FIELDS, are_valid_constraints),
                                   (_VERSIONS_FIELDS, scheme.is_valid_constraint_list), (_VERSION_FIELDS,
                                                                                         scheme.is_valid_version)):
            for field in fields:
                value = self.get(field, None)
                if value is not None and not controller(value):
                    warnings.append("Wrong value for '%s': %s" % (field, value))

        return missing, warnings

    def todict(self, skip_missing=False):
        """Return fields as a dict.

        Field names will be converted to use the underscore-lowercase style
        instead of hyphen-mixed case (i.e. home_page instead of Home-page).
        This is as per https://www.python.org/dev/peps/pep-0566/#id17.
        """
        self.set_metadata_version()

        fields = _version2fieldlist(self['Metadata-Version'])

        data = {}

        for field_name in fields:
            if not skip_missing or field_name in self._fields:
                key = _FIELD2ATTR[field_name]
                if key != 'project_url':
                    data[key] = self[field_name]
                else:
                    data[key] = [','.join(u) for u in self[field_name]]

        return data

    def add_requirements(self, requirements):
        if self['Metadata-Version'] == '1.1':
            # we can't have 1.1 metadata *and* Setuptools requires
            for field in ('Obsoletes', 'Requires', 'Provides'):
                if field in self:
                    del self[field]
        self['Requires-Dist'] += requirements

    # Mapping API
    # TODO could add iter* variants

    def keys(self):
        return list(_version2fieldlist(self['Metadata-Version']))

    def __iter__(self):
        for key in self.keys():
            yield key

    def values(self):
        return [self[key] for key in self.keys()]

    def items(self):
        return [(key, self[key]) for key in self.keys()]

    def __repr__(self):
        return '<%s %s %s>' % (self.__class__.__name__, self.name, self.version)


METADATA_FILENAME = 'pydist.json'
WHEEL_METADATA_FILENAME = 'metadata.json'
LEGACY_METADATA_FILENAME = 'METADATA'


class Metadata(object):
    """
    The metadata of a release. This implementation uses 2.1
    metadata where possible. If not possible, it wraps a LegacyMetadata
    instance which handles the key-value metadata format.
    """

    METADATA_VERSION_MATCHER = re.compile(r'^\d+(\.\d+)*$')

    NAME_MATCHER = re.compile('^[0-9A-Z]([0-9A-Z_.-]*[0-9A-Z])?$', re.I)

    FIELDNAME_MATCHER = re.compile('^[A-Z]([0-9A-Z-]*[0-9A-Z])?$', re.I)

    VERSION_MATCHER = PEP440_VERSION_RE

    SUMMARY_MATCHER = re.compile('.{1,2047}')

    METADATA_VERSION = '2.0'

    GENERATOR = 'distlib (%s)' % __version__

    MANDATORY_KEYS = {
        'name': (),
        'version': (),
        'summary': ('legacy', ),
    }

    INDEX_KEYS = ('name version license summary description author '
                  'author_email keywords platform home_page classifiers '
                  'download_url')

    DEPENDENCY_KEYS = ('extras run_requires test_requires build_requires '
                       'dev_requires provides meta_requires obsoleted_by '
                       'supports_environments')

    SYNTAX_VALIDATORS = {
        'metadata_version': (METADATA_VERSION_MATCHER, ()),
        'name': (NAME_MATCHER, ('legacy', )),
        'version': (VERSION_MATCHER, ('legacy', )),
        'summary': (SUMMARY_MATCHER, ('legacy', )),
        'dynamic': (FIELDNAME_MATCHER, ('legacy', )),
    }

    __slots__ = ('_legacy', '_data', 'scheme')

    def __init__(self, path=None, fileobj=None, mapping=None, scheme='default'):
        if [path, fileobj, mapping].count(None) < 2:
            raise TypeError('path, fileobj and mapping are exclusive')
        self._legacy = None
        self._data = None
        self.scheme = scheme
        # import pdb; pdb.set_trace()
        if mapping is not None:
            try:
                self._validate_mapping(mapping, scheme)
                self._data = mapping
            except MetadataUnrecognizedVersionError:
                self._legacy = LegacyMetadata(mapping=mapping, scheme=scheme)
                self.validate()
        else:
            data = None
            if path:
                with open(path, 'rb') as f:
                    data = f.read()
            elif fileobj:
                data = fileobj.read()
            if data is None:
                # Initialised with no args - to be added
                self._data = {
                    'metadata_version': self.METADATA_VERSION,
                    'generator': self.GENERATOR,
                }
            else:
                if not isinstance(data, text_type):
                    data = data.decode('utf-8')
                try:
                    self._data = json.loads(data)
                    self._validate_mapping(self._data, scheme)
                except ValueError:
                    # Note: MetadataUnrecognizedVersionError does not
                    # inherit from ValueError (it's a DistlibException,
                    # which should not inherit from ValueError).
                    # The ValueError comes from the json.load - if that
                    # succeeds and we get a validation error, we want
                    # that to propagate
                    self._legacy = LegacyMetadata(fileobj=StringIO(data), scheme=scheme)
                    self.validate()

    common_keys = set(('name', 'version', 'license', 'keywords', 'summary'))

    none_list = (None, list)
    none_dict = (None, dict)

    mapped_keys = {
        'run_requires': ('Requires-Dist', list),
        'build_requires': ('Setup-Requires-Dist', list),
        'dev_requires': none_list,
        'test_requires': none_list,
        'meta_requires': none_list,
        'extras': ('Provides-Extra', list),
        'modules': none_list,
        'namespaces': none_list,
        'exports': none_dict,
        'commands': none_dict,
        'classifiers': ('Classifier', list),
        'source_url': ('Download-URL', None),
        'metadata_version': ('Metadata-Version', None),
    }

    del none_list, none_dict

    def __getattribute__(self, key):
        common = object.__getattribute__(self, 'common_keys')
        mapped = object.__getattribute__(self, 'mapped_keys')
        if key in mapped:
            lk, maker = mapped[key]
            if self._legacy:
                if lk is None:
                    result = None if maker is None else maker()
                else:
                    result = self._legacy.get(lk)
            else:
                value = None if maker is None else maker()
                if key not in ('commands', 'exports', 'modules', 'namespaces', 'classifiers'):
                    result = self._data.get(key, value)
                else:
                    # special cases for PEP 459
                    sentinel = object()
                    result = sentinel
                    d = self._data.get('extensions')
                    if d:
                        if key == 'commands':
                            result = d.get('python.commands', value)
                        elif key == 'classifiers':
                            d = d.get('python.details')
                            if d:
                                result = d.get(key, value)
                        else:
                            d = d.get('python.exports')
                            if not d:
                                d = self._data.get('python.exports')
                            if d:
                                result = d.get(key, value)
                    if result is sentinel:
                        result = value
        elif key not in common:
            result = object.__getattribute__(self, key)
        elif self._legacy:
            result = self._legacy.get(key)
        else:
            result = self._data.get(key)
        return result

    def _validate_value(self, key, value, scheme=None):
        if key in self.SYNTAX_VALIDATORS:
            pattern, exclusions = self.SYNTAX_VALIDATORS[key]
            if (scheme or self.scheme) not in exclusions:
                m = pattern.match(value)
                if not m:
                    raise MetadataInvalidError("'%s' is an invalid value for "
                                               "the '%s' property" % (value, key))

    def __setattr__(self, key, value):
        self._validate_value(key, value)
        common = object.__getattribute__(self, 'common_keys')
        mapped = object.__getattribute__(self, 'mapped_keys')
        if key in mapped:
            lk, _ = mapped[key]
            if self._legacy:
                if lk is None:
                    raise NotImplementedError
                self._legacy[lk] = value
            elif key not in ('commands', 'exports', 'modules', 'namespaces', 'classifiers'):
                self._data[key] = value
            else:
                # special cases for PEP 459
                d = self._data.setdefault('extensions', {})
                if key == 'commands':
                    d['python.commands'] = value
                elif key == 'classifiers':
                    d = d.setdefault('python.details', {})
                    d[key] = value
                else:
                    d = d.setdefault('python.exports', {})
                    d[key] = value
        elif key not in common:
            object.__setattr__(self, key, value)
        else:
            if key == 'keywords':
                if isinstance(value, string_types):
                    value = value.strip()
                    if value:
                        value = value.split()
                    else:
                        value = []
            if self._legacy:
                self._legacy[key] = value
            else:
                self._data[key] = value

    @property
    def name_and_version(self):
        return _get_name_and_version(self.name, self.version, True)

    @property
    def provides(self):
        if self._legacy:
            result = self._legacy['Provides-Dist']
        else:
            result = self._data.setdefault('provides', [])
        s = '%s (%s)' % (self.name, self.version)
        if s not in result:
            result.append(s)
        return result

    @provides.setter
    def provides(self, value):
        if self._legacy:
            self._legacy['Provides-Dist'] = value
        else:
            self._data['provides'] = value

    def get_requirements(self, reqts, extras=None, env=None):
        """
        Base method to get dependencies, given a set of extras
        to satisfy and an optional environment context.
        :param reqts: A list of sometimes-wanted dependencies,
                      perhaps dependent on extras and environment.
        :param extras: A list of optional components being requested.
        :param env: An optional environment for marker evaluation.
        """
        if self._legacy:
            result = reqts
        else:
            result = []
            extras = get_extras(extras or [], self.extras)
            for d in reqts:
                if 'extra' not in d and 'environment' not in d:
                    # unconditional
                    include = True
                else:
                    if 'extra' not in d:
                        # Not extra-dependent - only environment-dependent
                        include = True
                    else:
                        include = d.get('extra') in extras
                    if include:
                        # Not excluded because of extras, check environment
                        marker = d.get('environment')
                        if marker:
                            include = interpret(marker, env)
                if include:
                    result.extend(d['requires'])
            for key in ('build', 'dev', 'test'):
                e = ':%s:' % key
                if e in extras:
                    extras.remove(e)
                    # A recursive call, but it should terminate since 'test'
                    # has been removed from the extras
                    reqts = self._data.get('%s_requires' % key, [])
                    result.extend(self.get_requirements(reqts, extras=extras, env=env))
        return result

    @property
    def dictionary(self):
        if self._legacy:
            return self._from_legacy()
        return self._data

    @property
    def dependencies(self):
        if self._legacy:
            raise NotImplementedError
        else:
            return extract_by_key(self._data, self.DEPENDENCY_KEYS)

    @dependencies.setter
    def dependencies(self, value):
        if self._legacy:
            raise NotImplementedError
        else:
            self._data.update(value)

    def _validate_mapping(self, mapping, scheme):
        if mapping.get('metadata_version') != self.METADATA_VERSION:
            raise MetadataUnrecognizedVersionError()
        missing = []
        for key, exclusions in self.MANDATORY_KEYS.items():
            if key not in mapping:
                if scheme not in exclusions:
                    missing.append(key)
        if missing:
            msg = 'Missing metadata items: %s' % ', '.join(missing)
            raise MetadataMissingError(msg)
        for k, v in mapping.items():
            self._validate_value(k, v, scheme)

    def validate(self):
        if self._legacy:
            missing, warnings = self._legacy.check(True)
            if missing or warnings:
                logger.warning('Metadata: missing: %s, warnings: %s', missing, warnings)
        else:
            self._validate_mapping(self._data, self.scheme)

    def todict(self):
        if self._legacy:
            return self._legacy.todict(True)
        else:
            result = extract_by_key(self._data, self.INDEX_KEYS)
            return result

    def _from_legacy(self):
        assert self._legacy and not self._data
        result = {
            'metadata_version': self.METADATA_VERSION,
            'generator': self.GENERATOR,
        }
        lmd = self._legacy.todict(True)  # skip missing ones
        for k in ('name', 'version', 'license', 'summary', 'description', 'classifier'):
            if k in lmd:
                if k == 'classifier':
                    nk = 'classifiers'
                else:
                    nk = k
                result[nk] = lmd[k]
        kw = lmd.get('Keywords', [])
        if kw == ['']:
            kw = []
        result['keywords'] = kw
        keys = (('requires_dist', 'run_requires'), ('setup_requires_dist', 'build_requires'))
        for ok, nk in keys:
            if ok in lmd and lmd[ok]:
                result[nk] = [{'requires': lmd[ok]}]
        result['provides'] = self.provides
        # author = {}
        # maintainer = {}
        return result

    LEGACY_MAPPING = {
        'name': 'Name',
        'version': 'Version',
        ('extensions', 'python.details', 'license'): 'License',
        'summary': 'Summary',
        'description': 'Description',
        ('extensions', 'python.project', 'project_urls', 'Home'): 'Home-page',
        ('extensions', 'python.project', 'contacts', 0, 'name'): 'Author',
        ('extensions', 'python.project', 'contacts', 0, 'email'): 'Author-email',
        'source_url': 'Download-URL',
        ('extensions', 'python.details', 'classifiers'): 'Classifier',
    }

    def _to_legacy(self):

        def process_entries(entries):
            reqts = set()
            for e in entries:
                extra = e.get('extra')
                env = e.get('environment')
                rlist = e['requires']
                for r in rlist:
                    if not env and not extra:
                        reqts.add(r)
                    else:
                        marker = ''
                        if extra:
                            marker = 'extra == "%s"' % extra
                        if env:
                            if marker:
                                marker = '(%s) and %s' % (env, marker)
                            else:
                                marker = env
                        reqts.add(';'.join((r, marker)))
            return reqts

        assert self._data and not self._legacy
        result = LegacyMetadata()
        nmd = self._data
        # import pdb; pdb.set_trace()
        for nk, ok in self.LEGACY_MAPPING.items():
            if not isinstance(nk, tuple):
                if nk in nmd:
                    result[ok] = nmd[nk]
            else:
                d = nmd
                found = True
                for k in nk:
                    try:
                        d = d[k]
                    except (KeyError, IndexError):
                        found = False
                        break
                if found:
                    result[ok] = d
        r1 = process_entries(self.run_requires + self.meta_requires)
        r2 = process_entries(self.build_requires + self.dev_requires)
        if self.extras:
            result['Provides-Extra'] = sorted(self.extras)
        result['Requires-Dist'] = sorted(r1)
        result['Setup-Requires-Dist'] = sorted(r2)
        # TODO: any other fields wanted
        return result

    def write(self, path=None, fileobj=None, legacy=False, skip_unknown=True):
        if [path, fileobj].count(None) != 1:
            raise ValueError('Exactly one of path and fileobj is needed')
        self.validate()
        if legacy:
            if self._legacy:
                legacy_md = self._legacy
            else:
                legacy_md = self._to_legacy()
            if path:
                legacy_md.write(path, skip_unknown=skip_unknown)
            else:
                legacy_md.write_file(fileobj, skip_unknown=skip_unknown)
        else:
            if self._legacy:
                d = self._from_legacy()
            else:
                d = self._data
            if fileobj:
                json.dump(d, fileobj, ensure_ascii=True, indent=2, sort_keys=True)
            else:
                with codecs.open(path, 'w', 'utf-8') as f:
                    json.dump(d, f, ensure_ascii=True, indent=2, sort_keys=True)

    def add_requirements(self, requirements):
        if self._legacy:
            self._legacy.add_requirements(requirements)
        else:
            run_requires = self._data.setdefault('run_requires', [])
            always = None
            for entry in run_requires:
                if 'environment' not in entry and 'extra' not in entry:
                    always = entry
                    break
            if always is None:
                always = {'requires': requirements}
                run_requires.insert(0, always)
            else:
                rset = set(always['requires']) | set(requirements)
                always['requires'] = sorted(rset)

    def __repr__(self):
        name = self.name or '(no name)'
        version = self.version or 'no version'
        return '<%s %s %s (%s)>' % (self.__class__.__name__, self.metadata_version, name, version)

# === NexusCore/myenv\Lib\site-packages\pip\_internal\index\package_finder.py ===
"""Routines related to PyPI, indexes"""

import enum
import functools
import itertools
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, FrozenSet, Iterable, List, Optional, Set, Tuple, Union

from pip._vendor.packaging import specifiers
from pip._vendor.packaging.tags import Tag
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import InvalidVersion, _BaseVersion
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.exceptions import (
    BestVersionAlreadyInstalled,
    DistributionNotFound,
    InvalidWheelFilename,
    UnsupportedWheel,
)
from pip._internal.index.collector import LinkCollector, parse_links
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.format_control import FormatControl
from pip._internal.models.link import Link
from pip._internal.models.search_scope import SearchScope
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.models.target_python import TargetPython
from pip._internal.models.wheel import Wheel
from pip._internal.req import InstallRequirement
from pip._internal.utils._log import getLogger
from pip._internal.utils.filetypes import WHEEL_EXTENSION
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import build_netloc
from pip._internal.utils.packaging import check_requires_python
from pip._internal.utils.unpacking import SUPPORTED_EXTENSIONS

if TYPE_CHECKING:
    from pip._vendor.typing_extensions import TypeGuard

__all__ = ["FormatControl", "BestCandidateResult", "PackageFinder"]


logger = getLogger(__name__)

BuildTag = Union[Tuple[()], Tuple[int, str]]
CandidateSortingKey = Tuple[int, int, int, _BaseVersion, Optional[int], BuildTag]


def _check_link_requires_python(
    link: Link,
    version_info: Tuple[int, int, int],
    ignore_requires_python: bool = False,
) -> bool:
    """
    Return whether the given Python version is compatible with a link's
    "Requires-Python" value.

    :param version_info: A 3-tuple of ints representing the Python
        major-minor-micro version to check.
    :param ignore_requires_python: Whether to ignore the "Requires-Python"
        value if the given Python version isn't compatible.
    """
    try:
        is_compatible = check_requires_python(
            link.requires_python,
            version_info=version_info,
        )
    except specifiers.InvalidSpecifier:
        logger.debug(
            "Ignoring invalid Requires-Python (%r) for link: %s",
            link.requires_python,
            link,
        )
    else:
        if not is_compatible:
            version = ".".join(map(str, version_info))
            if not ignore_requires_python:
                logger.verbose(
                    "Link requires a different Python (%s not in: %r): %s",
                    version,
                    link.requires_python,
                    link,
                )
                return False

            logger.debug(
                "Ignoring failed Requires-Python check (%s not in: %r) for link: %s",
                version,
                link.requires_python,
                link,
            )

    return True


class LinkType(enum.Enum):
    candidate = enum.auto()
    different_project = enum.auto()
    yanked = enum.auto()
    format_unsupported = enum.auto()
    format_invalid = enum.auto()
    platform_mismatch = enum.auto()
    requires_python_mismatch = enum.auto()


class LinkEvaluator:
    """
    Responsible for evaluating links for a particular project.
    """

    _py_version_re = re.compile(r"-py([123]\.?[0-9]?)$")

    # Don't include an allow_yanked default value to make sure each call
    # site considers whether yanked releases are allowed. This also causes
    # that decision to be made explicit in the calling code, which helps
    # people when reading the code.
    def __init__(
        self,
        project_name: str,
        canonical_name: str,
        formats: FrozenSet[str],
        target_python: TargetPython,
        allow_yanked: bool,
        ignore_requires_python: Optional[bool] = None,
    ) -> None:
        """
        :param project_name: The user supplied package name.
        :param canonical_name: The canonical package name.
        :param formats: The formats allowed for this package. Should be a set
            with 'binary' or 'source' or both in it.
        :param target_python: The target Python interpreter to use when
            evaluating link compatibility. This is used, for example, to
            check wheel compatibility, as well as when checking the Python
            version, e.g. the Python version embedded in a link filename
            (or egg fragment) and against an HTML link's optional PEP 503
            "data-requires-python" attribute.
        :param allow_yanked: Whether files marked as yanked (in the sense
            of PEP 592) are permitted to be candidates for install.
        :param ignore_requires_python: Whether to ignore incompatible
            PEP 503 "data-requires-python" values in HTML links. Defaults
            to False.
        """
        if ignore_requires_python is None:
            ignore_requires_python = False

        self._allow_yanked = allow_yanked
        self._canonical_name = canonical_name
        self._ignore_requires_python = ignore_requires_python
        self._formats = formats
        self._target_python = target_python

        self.project_name = project_name

    def evaluate_link(self, link: Link) -> Tuple[LinkType, str]:
        """
        Determine whether a link is a candidate for installation.

        :return: A tuple (result, detail), where *result* is an enum
            representing whether the evaluation found a candidate, or the reason
            why one is not found. If a candidate is found, *detail* will be the
            candidate's version string; if one is not found, it contains the
            reason the link fails to qualify.
        """
        version = None
        if link.is_yanked and not self._allow_yanked:
            reason = link.yanked_reason or "<none given>"
            return (LinkType.yanked, f"yanked for reason: {reason}")

        if link.egg_fragment:
            egg_info = link.egg_fragment
            ext = link.ext
        else:
            egg_info, ext = link.splitext()
            if not ext:
                return (LinkType.format_unsupported, "not a file")
            if ext not in SUPPORTED_EXTENSIONS:
                return (
                    LinkType.format_unsupported,
                    f"unsupported archive format: {ext}",
                )
            if "binary" not in self._formats and ext == WHEEL_EXTENSION:
                reason = f"No binaries permitted for {self.project_name}"
                return (LinkType.format_unsupported, reason)
            if "macosx10" in link.path and ext == ".zip":
                return (LinkType.format_unsupported, "macosx10 one")
            if ext == WHEEL_EXTENSION:
                try:
                    wheel = Wheel(link.filename)
                except InvalidWheelFilename:
                    return (
                        LinkType.format_invalid,
                        "invalid wheel filename",
                    )
                if canonicalize_name(wheel.name) != self._canonical_name:
                    reason = f"wrong project name (not {self.project_name})"
                    return (LinkType.different_project, reason)

                supported_tags = self._target_python.get_unsorted_tags()
                if not wheel.supported(supported_tags):
                    # Include the wheel's tags in the reason string to
                    # simplify troubleshooting compatibility issues.
                    file_tags = ", ".join(wheel.get_formatted_file_tags())
                    reason = (
                        f"none of the wheel's tags ({file_tags}) are compatible "
                        f"(run pip debug --verbose to show compatible tags)"
                    )
                    return (LinkType.platform_mismatch, reason)

                version = wheel.version

        # This should be up by the self.ok_binary check, but see issue 2700.
        if "source" not in self._formats and ext != WHEEL_EXTENSION:
            reason = f"No sources permitted for {self.project_name}"
            return (LinkType.format_unsupported, reason)

        if not version:
            version = _extract_version_from_fragment(
                egg_info,
                self._canonical_name,
            )
        if not version:
            reason = f"Missing project version for {self.project_name}"
            return (LinkType.format_invalid, reason)

        match = self._py_version_re.search(version)
        if match:
            version = version[: match.start()]
            py_version = match.group(1)
            if py_version != self._target_python.py_version:
                return (
                    LinkType.platform_mismatch,
                    "Python version is incorrect",
                )

        supports_python = _check_link_requires_python(
            link,
            version_info=self._target_python.py_version_info,
            ignore_requires_python=self._ignore_requires_python,
        )
        if not supports_python:
            reason = f"{version} Requires-Python {link.requires_python}"
            return (LinkType.requires_python_mismatch, reason)

        logger.debug("Found link %s, version: %s", link, version)

        return (LinkType.candidate, version)


def filter_unallowed_hashes(
    candidates: List[InstallationCandidate],
    hashes: Optional[Hashes],
    project_name: str,
) -> List[InstallationCandidate]:
    """
    Filter out candidates whose hashes aren't allowed, and return a new
    list of candidates.

    If at least one candidate has an allowed hash, then all candidates with
    either an allowed hash or no hash specified are returned.  Otherwise,
    the given candidates are returned.

    Including the candidates with no hash specified when there is a match
    allows a warning to be logged if there is a more preferred candidate
    with no hash specified.  Returning all candidates in the case of no
    matches lets pip report the hash of the candidate that would otherwise
    have been installed (e.g. permitting the user to more easily update
    their requirements file with the desired hash).
    """
    if not hashes:
        logger.debug(
            "Given no hashes to check %s links for project %r: "
            "discarding no candidates",
            len(candidates),
            project_name,
        )
        # Make sure we're not returning back the given value.
        return list(candidates)

    matches_or_no_digest = []
    # Collect the non-matches for logging purposes.
    non_matches = []
    match_count = 0
    for candidate in candidates:
        link = candidate.link
        if not link.has_hash:
            pass
        elif link.is_hash_allowed(hashes=hashes):
            match_count += 1
        else:
            non_matches.append(candidate)
            continue

        matches_or_no_digest.append(candidate)

    if match_count:
        filtered = matches_or_no_digest
    else:
        # Make sure we're not returning back the given value.
        filtered = list(candidates)

    if len(filtered) == len(candidates):
        discard_message = "discarding no candidates"
    else:
        discard_message = "discarding {} non-matches:\n  {}".format(
            len(non_matches),
            "\n  ".join(str(candidate.link) for candidate in non_matches),
        )

    logger.debug(
        "Checked %s links for project %r against %s hashes "
        "(%s matches, %s no digest): %s",
        len(candidates),
        project_name,
        hashes.digest_count,
        match_count,
        len(matches_or_no_digest) - match_count,
        discard_message,
    )

    return filtered


@dataclass
class CandidatePreferences:
    """
    Encapsulates some of the preferences for filtering and sorting
    InstallationCandidate objects.
    """

    prefer_binary: bool = False
    allow_all_prereleases: bool = False


@dataclass(frozen=True)
class BestCandidateResult:
    """A collection of candidates, returned by `PackageFinder.find_best_candidate`.

    This class is only intended to be instantiated by CandidateEvaluator's
    `compute_best_candidate()` method.

    :param all_candidates: A sequence of all available candidates found.
    :param applicable_candidates: The applicable candidates.
    :param best_candidate: The most preferred candidate found, or None
        if no applicable candidates were found.
    """

    all_candidates: List[InstallationCandidate]
    applicable_candidates: List[InstallationCandidate]
    best_candidate: Optional[InstallationCandidate]

    def __post_init__(self) -> None:
        assert set(self.applicable_candidates) <= set(self.all_candidates)

        if self.best_candidate is None:
            assert not self.applicable_candidates
        else:
            assert self.best_candidate in self.applicable_candidates


class CandidateEvaluator:
    """
    Responsible for filtering and sorting candidates for installation based
    on what tags are valid.
    """

    @classmethod
    def create(
        cls,
        project_name: str,
        target_python: Optional[TargetPython] = None,
        prefer_binary: bool = False,
        allow_all_prereleases: bool = False,
        specifier: Optional[specifiers.BaseSpecifier] = None,
        hashes: Optional[Hashes] = None,
    ) -> "CandidateEvaluator":
        """Create a CandidateEvaluator object.

        :param target_python: The target Python interpreter to use when
            checking compatibility. If None (the default), a TargetPython
            object will be constructed from the running Python.
        :param specifier: An optional object implementing `filter`
            (e.g. `packaging.specifiers.SpecifierSet`) to filter applicable
            versions.
        :param hashes: An optional collection of allowed hashes.
        """
        if target_python is None:
            target_python = TargetPython()
        if specifier is None:
            specifier = specifiers.SpecifierSet()

        supported_tags = target_python.get_sorted_tags()

        return cls(
            project_name=project_name,
            supported_tags=supported_tags,
            specifier=specifier,
            prefer_binary=prefer_binary,
            allow_all_prereleases=allow_all_prereleases,
            hashes=hashes,
        )

    def __init__(
        self,
        project_name: str,
        supported_tags: List[Tag],
        specifier: specifiers.BaseSpecifier,
        prefer_binary: bool = False,
        allow_all_prereleases: bool = False,
        hashes: Optional[Hashes] = None,
    ) -> None:
        """
        :param supported_tags: The PEP 425 tags supported by the target
            Python in order of preference (most preferred first).
        """
        self._allow_all_prereleases = allow_all_prereleases
        self._hashes = hashes
        self._prefer_binary = prefer_binary
        self._project_name = project_name
        self._specifier = specifier
        self._supported_tags = supported_tags
        # Since the index of the tag in the _supported_tags list is used
        # as a priority, precompute a map from tag to index/priority to be
        # used in wheel.find_most_preferred_tag.
        self._wheel_tag_preferences = {
            tag: idx for idx, tag in enumerate(supported_tags)
        }

    def get_applicable_candidates(
        self,
        candidates: List[InstallationCandidate],
    ) -> List[InstallationCandidate]:
        """
        Return the applicable candidates from a list of candidates.
        """
        # Using None infers from the specifier instead.
        allow_prereleases = self._allow_all_prereleases or None
        specifier = self._specifier

        # We turn the version object into a str here because otherwise
        # when we're debundled but setuptools isn't, Python will see
        # packaging.version.Version and
        # pkg_resources._vendor.packaging.version.Version as different
        # types. This way we'll use a str as a common data interchange
        # format. If we stop using the pkg_resources provided specifier
        # and start using our own, we can drop the cast to str().
        candidates_and_versions = [(c, str(c.version)) for c in candidates]
        versions = set(
            specifier.filter(
                (v for _, v in candidates_and_versions),
                prereleases=allow_prereleases,
            )
        )

        applicable_candidates = [c for c, v in candidates_and_versions if v in versions]
        filtered_applicable_candidates = filter_unallowed_hashes(
            candidates=applicable_candidates,
            hashes=self._hashes,
            project_name=self._project_name,
        )

        return sorted(filtered_applicable_candidates, key=self._sort_key)

    def _sort_key(self, candidate: InstallationCandidate) -> CandidateSortingKey:
        """
        Function to pass as the `key` argument to a call to sorted() to sort
        InstallationCandidates by preference.

        Returns a tuple such that tuples sorting as greater using Python's
        default comparison operator are more preferred.

        The preference is as follows:

        First and foremost, candidates with allowed (matching) hashes are
        always preferred over candidates without matching hashes. This is
        because e.g. if the only candidate with an allowed hash is yanked,
        we still want to use that candidate.

        Second, excepting hash considerations, candidates that have been
        yanked (in the sense of PEP 592) are always less preferred than
        candidates that haven't been yanked. Then:

        If not finding wheels, they are sorted by version only.
        If finding wheels, then the sort order is by version, then:
          1. existing installs
          2. wheels ordered via Wheel.support_index_min(self._supported_tags)
          3. source archives
        If prefer_binary was set, then all wheels are sorted above sources.

        Note: it was considered to embed this logic into the Link
              comparison operators, but then different sdist links
              with the same version, would have to be considered equal
        """
        valid_tags = self._supported_tags
        support_num = len(valid_tags)
        build_tag: BuildTag = ()
        binary_preference = 0
        link = candidate.link
        if link.is_wheel:
            # can raise InvalidWheelFilename
            wheel = Wheel(link.filename)
            try:
                pri = -(
                    wheel.find_most_preferred_tag(
                        valid_tags, self._wheel_tag_preferences
                    )
                )
            except ValueError:
                raise UnsupportedWheel(
                    f"{wheel.filename} is not a supported wheel for this platform. It "
                    "can't be sorted."
                )
            if self._prefer_binary:
                binary_preference = 1
            if wheel.build_tag is not None:
                match = re.match(r"^(\d+)(.*)$", wheel.build_tag)
                assert match is not None, "guaranteed by filename validation"
                build_tag_groups = match.groups()
                build_tag = (int(build_tag_groups[0]), build_tag_groups[1])
        else:  # sdist
            pri = -(support_num)
        has_allowed_hash = int(link.is_hash_allowed(self._hashes))
        yank_value = -1 * int(link.is_yanked)  # -1 for yanked.
        return (
            has_allowed_hash,
            yank_value,
            binary_preference,
            candidate.version,
            pri,
            build_tag,
        )

    def sort_best_candidate(
        self,
        candidates: List[InstallationCandidate],
    ) -> Optional[InstallationCandidate]:
        """
        Return the best candidate per the instance's sort order, or None if
        no candidate is acceptable.
        """
        if not candidates:
            return None
        best_candidate = max(candidates, key=self._sort_key)
        return best_candidate

    def compute_best_candidate(
        self,
        candidates: List[InstallationCandidate],
    ) -> BestCandidateResult:
        """
        Compute and return a `BestCandidateResult` instance.
        """
        applicable_candidates = self.get_applicable_candidates(candidates)

        best_candidate = self.sort_best_candidate(applicable_candidates)

        return BestCandidateResult(
            candidates,
            applicable_candidates=applicable_candidates,
            best_candidate=best_candidate,
        )


class PackageFinder:
    """This finds packages.

    This is meant to match easy_install's technique for looking for
    packages, by reading pages and looking for appropriate links.
    """

    def __init__(
        self,
        link_collector: LinkCollector,
        target_python: TargetPython,
        allow_yanked: bool,
        format_control: Optional[FormatControl] = None,
        candidate_prefs: Optional[CandidatePreferences] = None,
        ignore_requires_python: Optional[bool] = None,
    ) -> None:
        """
        This constructor is primarily meant to be used by the create() class
        method and from tests.

        :param format_control: A FormatControl object, used to control
            the selection of source packages / binary packages when consulting
            the index and links.
        :param candidate_prefs: Options to use when creating a
            CandidateEvaluator object.
        """
        if candidate_prefs is None:
            candidate_prefs = CandidatePreferences()

        format_control = format_control or FormatControl(set(), set())

        self._allow_yanked = allow_yanked
        self._candidate_prefs = candidate_prefs
        self._ignore_requires_python = ignore_requires_python
        self._link_collector = link_collector
        self._target_python = target_python

        self.format_control = format_control

        # These are boring links that have already been logged somehow.
        self._logged_links: Set[Tuple[Link, LinkType, str]] = set()

    # Don't include an allow_yanked default value to make sure each call
    # site considers whether yanked releases are allowed. This also causes
    # that decision to be made explicit in the calling code, which helps
    # people when reading the code.
    @classmethod
    def create(
        cls,
        link_collector: LinkCollector,
        selection_prefs: SelectionPreferences,
        target_python: Optional[TargetPython] = None,
    ) -> "PackageFinder":
        """Create a PackageFinder.

        :param selection_prefs: The candidate selection preferences, as a
            SelectionPreferences object.
        :param target_python: The target Python interpreter to use when
            checking compatibility. If None (the default), a TargetPython
            object will be constructed from the running Python.
        """
        if target_python is None:
            target_python = TargetPython()

        candidate_prefs = CandidatePreferences(
            prefer_binary=selection_prefs.prefer_binary,
            allow_all_prereleases=selection_prefs.allow_all_prereleases,
        )

        return cls(
            candidate_prefs=candidate_prefs,
            link_collector=link_collector,
            target_python=target_python,
            allow_yanked=selection_prefs.allow_yanked,
            format_control=selection_prefs.format_control,
            ignore_requires_python=selection_prefs.ignore_requires_python,
        )

    @property
    def target_python(self) -> TargetPython:
        return self._target_python

    @property
    def search_scope(self) -> SearchScope:
        return self._link_collector.search_scope

    @search_scope.setter
    def search_scope(self, search_scope: SearchScope) -> None:
        self._link_collector.search_scope = search_scope

    @property
    def find_links(self) -> List[str]:
        return self._link_collector.find_links

    @property
    def index_urls(self) -> List[str]:
        return self.search_scope.index_urls

    @property
    def proxy(self) -> Optional[str]:
        return self._link_collector.session.pip_proxy

    @property
    def trusted_hosts(self) -> Iterable[str]:
        for host_port in self._link_collector.session.pip_trusted_origins:
            yield build_netloc(*host_port)

    @property
    def custom_cert(self) -> Optional[str]:
        # session.verify is either a boolean (use default bundle/no SSL
        # verification) or a string path to a custom CA bundle to use. We only
        # care about the latter.
        verify = self._link_collector.session.verify
        return verify if isinstance(verify, str) else None

    @property
    def client_cert(self) -> Optional[str]:
        cert = self._link_collector.session.cert
        assert not isinstance(cert, tuple), "pip only supports PEM client certs"
        return cert

    @property
    def allow_all_prereleases(self) -> bool:
        return self._candidate_prefs.allow_all_prereleases

    def set_allow_all_prereleases(self) -> None:
        self._candidate_prefs.allow_all_prereleases = True

    @property
    def prefer_binary(self) -> bool:
        return self._candidate_prefs.prefer_binary

    def set_prefer_binary(self) -> None:
        self._candidate_prefs.prefer_binary = True

    def requires_python_skipped_reasons(self) -> List[str]:
        reasons = {
            detail
            for _, result, detail in self._logged_links
            if result == LinkType.requires_python_mismatch
        }
        return sorted(reasons)

    def make_link_evaluator(self, project_name: str) -> LinkEvaluator:
        canonical_name = canonicalize_name(project_name)
        formats = self.format_control.get_allowed_formats(canonical_name)

        return LinkEvaluator(
            project_name=project_name,
            canonical_name=canonical_name,
            formats=formats,
            target_python=self._target_python,
            allow_yanked=self._allow_yanked,
            ignore_requires_python=self._ignore_requires_python,
        )

    def _sort_links(self, links: Iterable[Link]) -> List[Link]:
        """
        Returns elements of links in order, non-egg links first, egg links
        second, while eliminating duplicates
        """
        eggs, no_eggs = [], []
        seen: Set[Link] = set()
        for link in links:
            if link not in seen:
                seen.add(link)
                if link.egg_fragment:
                    eggs.append(link)
                else:
                    no_eggs.append(link)
        return no_eggs + eggs

    def _log_skipped_link(self, link: Link, result: LinkType, detail: str) -> None:
        # This is a hot method so don't waste time hashing links unless we're
        # actually going to log 'em.
        if not logger.isEnabledFor(logging.DEBUG):
            return

        entry = (link, result, detail)
        if entry not in self._logged_links:
            # Put the link at the end so the reason is more visible and because
            # the link string is usually very long.
            logger.debug("Skipping link: %s: %s", detail, link)
            self._logged_links.add(entry)

    def get_install_candidate(
        self, link_evaluator: LinkEvaluator, link: Link
    ) -> Optional[InstallationCandidate]:
        """
        If the link is a candidate for install, convert it to an
        InstallationCandidate and return it. Otherwise, return None.
        """
        result, detail = link_evaluator.evaluate_link(link)
        if result != LinkType.candidate:
            self._log_skipped_link(link, result, detail)
            return None

        try:
            return InstallationCandidate(
                name=link_evaluator.project_name,
                link=link,
                version=detail,
            )
        except InvalidVersion:
            return None

    def evaluate_links(
        self, link_evaluator: LinkEvaluator, links: Iterable[Link]
    ) -> List[InstallationCandidate]:
        """
        Convert links that are candidates to InstallationCandidate objects.
        """
        candidates = []
        for link in self._sort_links(links):
            candidate = self.get_install_candidate(link_evaluator, link)
            if candidate is not None:
                candidates.append(candidate)

        return candidates

    def process_project_url(
        self, project_url: Link, link_evaluator: LinkEvaluator
    ) -> List[InstallationCandidate]:
        logger.debug(
            "Fetching project page and analyzing links: %s",
            project_url,
        )
        index_response = self._link_collector.fetch_response(project_url)
        if index_response is None:
            return []

        page_links = list(parse_links(index_response))

        with indent_log():
            package_links = self.evaluate_links(
                link_evaluator,
                links=page_links,
            )

        return package_links

    @functools.lru_cache(maxsize=None)
    def find_all_candidates(self, project_name: str) -> List[InstallationCandidate]:
        """Find all available InstallationCandidate for project_name

        This checks index_urls and find_links.
        All versions found are returned as an InstallationCandidate list.

        See LinkEvaluator.evaluate_link() for details on which files
        are accepted.
        """
        link_evaluator = self.make_link_evaluator(project_name)

        collected_sources = self._link_collector.collect_sources(
            project_name=project_name,
            candidates_from_page=functools.partial(
                self.process_project_url,
                link_evaluator=link_evaluator,
            ),
        )

        page_candidates_it = itertools.chain.from_iterable(
            source.page_candidates()
            for sources in collected_sources
            for source in sources
            if source is not None
        )
        page_candidates = list(page_candidates_it)

        file_links_it = itertools.chain.from_iterable(
            source.file_links()
            for sources in collected_sources
            for source in sources
            if source is not None
        )
        file_candidates = self.evaluate_links(
            link_evaluator,
            sorted(file_links_it, reverse=True),
        )

        if logger.isEnabledFor(logging.DEBUG) and file_candidates:
            paths = []
            for candidate in file_candidates:
                assert candidate.link.url  # we need to have a URL
                try:
                    paths.append(candidate.link.file_path)
                except Exception:
                    paths.append(candidate.link.url)  # it's not a local file

            logger.debug("Local files found: %s", ", ".join(paths))

        # This is an intentional priority ordering
        return file_candidates + page_candidates

    def make_candidate_evaluator(
        self,
        project_name: str,
        specifier: Optional[specifiers.BaseSpecifier] = None,
        hashes: Optional[Hashes] = None,
    ) -> CandidateEvaluator:
        """Create a CandidateEvaluator object to use."""
        candidate_prefs = self._candidate_prefs
        return CandidateEvaluator.create(
            project_name=project_name,
            target_python=self._target_python,
            prefer_binary=candidate_prefs.prefer_binary,
            allow_all_prereleases=candidate_prefs.allow_all_prereleases,
            specifier=specifier,
            hashes=hashes,
        )

    @functools.lru_cache(maxsize=None)
    def find_best_candidate(
        self,
        project_name: str,
        specifier: Optional[specifiers.BaseSpecifier] = None,
        hashes: Optional[Hashes] = None,
    ) -> BestCandidateResult:
        """Find matches for the given project and specifier.

        :param specifier: An optional object implementing `filter`
            (e.g. `packaging.specifiers.SpecifierSet`) to filter applicable
            versions.

        :return: A `BestCandidateResult` instance.
        """
        candidates = self.find_all_candidates(project_name)
        candidate_evaluator = self.make_candidate_evaluator(
            project_name=project_name,
            specifier=specifier,
            hashes=hashes,
        )
        return candidate_evaluator.compute_best_candidate(candidates)

    def find_requirement(
        self, req: InstallRequirement, upgrade: bool
    ) -> Optional[InstallationCandidate]:
        """Try to find a Link matching req

        Expects req, an InstallRequirement and upgrade, a boolean
        Returns a InstallationCandidate if found,
        Raises DistributionNotFound or BestVersionAlreadyInstalled otherwise
        """
        hashes = req.hashes(trust_internet=False)
        best_candidate_result = self.find_best_candidate(
            req.name,
            specifier=req.specifier,
            hashes=hashes,
        )
        best_candidate = best_candidate_result.best_candidate

        installed_version: Optional[_BaseVersion] = None
        if req.satisfied_by is not None:
            installed_version = req.satisfied_by.version

        def _format_versions(cand_iter: Iterable[InstallationCandidate]) -> str:
            # This repeated parse_version and str() conversion is needed to
            # handle different vendoring sources from pip and pkg_resources.
            # If we stop using the pkg_resources provided specifier and start
            # using our own, we can drop the cast to str().
            return (
                ", ".join(
                    sorted(
                        {str(c.version) for c in cand_iter},
                        key=parse_version,
                    )
                )
                or "none"
            )

        if installed_version is None and best_candidate is None:
            logger.critical(
                "Could not find a version that satisfies the requirement %s "
                "(from versions: %s)",
                req,
                _format_versions(best_candidate_result.all_candidates),
            )

            raise DistributionNotFound(f"No matching distribution found for {req}")

        def _should_install_candidate(
            candidate: Optional[InstallationCandidate],
        ) -> "TypeGuard[InstallationCandidate]":
            if installed_version is None:
                return True
            if best_candidate is None:
                return False
            return best_candidate.version > installed_version

        if not upgrade and installed_version is not None:
            if _should_install_candidate(best_candidate):
                logger.debug(
                    "Existing installed version (%s) satisfies requirement "
                    "(most up-to-date version is %s)",
                    installed_version,
                    best_candidate.version,
                )
            else:
                logger.debug(
                    "Existing installed version (%s) is most up-to-date and "
                    "satisfies requirement",
                    installed_version,
                )
            return None

        if _should_install_candidate(best_candidate):
            logger.debug(
                "Using version %s (newest of versions: %s)",
                best_candidate.version,
                _format_versions(best_candidate_result.applicable_candidates),
            )
            return best_candidate

        # We have an existing version, and its the best version
        logger.debug(
            "Installed version (%s) is most up-to-date (past versions: %s)",
            installed_version,
            _format_versions(best_candidate_result.applicable_candidates),
        )
        raise BestVersionAlreadyInstalled


def _find_name_version_sep(fragment: str, canonical_name: str) -> int:
    """Find the separator's index based on the package's canonical name.

    :param fragment: A <package>+<version> filename "fragment" (stem) or
        egg fragment.
    :param canonical_name: The package's canonical name.

    This function is needed since the canonicalized name does not necessarily
    have the same length as the egg info's name part. An example::

    >>> fragment = 'foo__bar-1.0'
    >>> canonical_name = 'foo-bar'
    >>> _find_name_version_sep(fragment, canonical_name)
    8
    """
    # Project name and version must be separated by one single dash. Find all
    # occurrences of dashes; if the string in front of it matches the canonical
    # name, this is the one separating the name and version parts.
    for i, c in enumerate(fragment):
        if c != "-":
            continue
        if canonicalize_name(fragment[:i]) == canonical_name:
            return i
    raise ValueError(f"{fragment} does not match {canonical_name}")


def _extract_version_from_fragment(fragment: str, canonical_name: str) -> Optional[str]:
    """Parse the version string from a <package>+<version> filename
    "fragment" (stem) or egg fragment.

    :param fragment: The string to parse. E.g. foo-2.1
    :param canonical_name: The canonicalized name of the package this
        belongs to.
    """
    try:
        version_start = _find_name_version_sep(fragment, canonical_name) + 1
    except ValueError:
        return None
    version = fragment[version_start:]
    if not version:
        return None
    return version

# === NexusCore/openenv\Lib\site-packages\pip\_internal\index\package_finder.py ===
"""Routines related to PyPI, indexes"""

import enum
import functools
import itertools
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, FrozenSet, Iterable, List, Optional, Set, Tuple, Union

from pip._vendor.packaging import specifiers
from pip._vendor.packaging.tags import Tag
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import InvalidVersion, _BaseVersion
from pip._vendor.packaging.version import parse as parse_version

from pip._internal.exceptions import (
    BestVersionAlreadyInstalled,
    DistributionNotFound,
    InvalidWheelFilename,
    UnsupportedWheel,
)
from pip._internal.index.collector import LinkCollector, parse_links
from pip._internal.models.candidate import InstallationCandidate
from pip._internal.models.format_control import FormatControl
from pip._internal.models.link import Link
from pip._internal.models.search_scope import SearchScope
from pip._internal.models.selection_prefs import SelectionPreferences
from pip._internal.models.target_python import TargetPython
from pip._internal.models.wheel import Wheel
from pip._internal.req import InstallRequirement
from pip._internal.utils._log import getLogger
from pip._internal.utils.filetypes import WHEEL_EXTENSION
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.logging import indent_log
from pip._internal.utils.misc import build_netloc
from pip._internal.utils.packaging import check_requires_python
from pip._internal.utils.unpacking import SUPPORTED_EXTENSIONS

if TYPE_CHECKING:
    from pip._vendor.typing_extensions import TypeGuard

__all__ = ["FormatControl", "BestCandidateResult", "PackageFinder"]


logger = getLogger(__name__)

BuildTag = Union[Tuple[()], Tuple[int, str]]
CandidateSortingKey = Tuple[int, int, int, _BaseVersion, Optional[int], BuildTag]


def _check_link_requires_python(
    link: Link,
    version_info: Tuple[int, int, int],
    ignore_requires_python: bool = False,
) -> bool:
    """
    Return whether the given Python version is compatible with a link's
    "Requires-Python" value.

    :param version_info: A 3-tuple of ints representing the Python
        major-minor-micro version to check.
    :param ignore_requires_python: Whether to ignore the "Requires-Python"
        value if the given Python version isn't compatible.
    """
    try:
        is_compatible = check_requires_python(
            link.requires_python,
            version_info=version_info,
        )
    except specifiers.InvalidSpecifier:
        logger.debug(
            "Ignoring invalid Requires-Python (%r) for link: %s",
            link.requires_python,
            link,
        )
    else:
        if not is_compatible:
            version = ".".join(map(str, version_info))
            if not ignore_requires_python:
                logger.verbose(
                    "Link requires a different Python (%s not in: %r): %s",
                    version,
                    link.requires_python,
                    link,
                )
                return False

            logger.debug(
                "Ignoring failed Requires-Python check (%s not in: %r) for link: %s",
                version,
                link.requires_python,
                link,
            )

    return True


class LinkType(enum.Enum):
    candidate = enum.auto()
    different_project = enum.auto()
    yanked = enum.auto()
    format_unsupported = enum.auto()
    format_invalid = enum.auto()
    platform_mismatch = enum.auto()
    requires_python_mismatch = enum.auto()


class LinkEvaluator:
    """
    Responsible for evaluating links for a particular project.
    """

    _py_version_re = re.compile(r"-py([123]\.?[0-9]?)$")

    # Don't include an allow_yanked default value to make sure each call
    # site considers whether yanked releases are allowed. This also causes
    # that decision to be made explicit in the calling code, which helps
    # people when reading the code.
    def __init__(
        self,
        project_name: str,
        canonical_name: str,
        formats: FrozenSet[str],
        target_python: TargetPython,
        allow_yanked: bool,
        ignore_requires_python: Optional[bool] = None,
    ) -> None:
        """
        :param project_name: The user supplied package name.
        :param canonical_name: The canonical package name.
        :param formats: The formats allowed for this package. Should be a set
            with 'binary' or 'source' or both in it.
        :param target_python: The target Python interpreter to use when
            evaluating link compatibility. This is used, for example, to
            check wheel compatibility, as well as when checking the Python
            version, e.g. the Python version embedded in a link filename
            (or egg fragment) and against an HTML link's optional PEP 503
            "data-requires-python" attribute.
        :param allow_yanked: Whether files marked as yanked (in the sense
            of PEP 592) are permitted to be candidates for install.
        :param ignore_requires_python: Whether to ignore incompatible
            PEP 503 "data-requires-python" values in HTML links. Defaults
            to False.
        """
        if ignore_requires_python is None:
            ignore_requires_python = False

        self._allow_yanked = allow_yanked
        self._canonical_name = canonical_name
        self._ignore_requires_python = ignore_requires_python
        self._formats = formats
        self._target_python = target_python

        self.project_name = project_name

    def evaluate_link(self, link: Link) -> Tuple[LinkType, str]:
        """
        Determine whether a link is a candidate for installation.

        :return: A tuple (result, detail), where *result* is an enum
            representing whether the evaluation found a candidate, or the reason
            why one is not found. If a candidate is found, *detail* will be the
            candidate's version string; if one is not found, it contains the
            reason the link fails to qualify.
        """
        version = None
        if link.is_yanked and not self._allow_yanked:
            reason = link.yanked_reason or "<none given>"
            return (LinkType.yanked, f"yanked for reason: {reason}")

        if link.egg_fragment:
            egg_info = link.egg_fragment
            ext = link.ext
        else:
            egg_info, ext = link.splitext()
            if not ext:
                return (LinkType.format_unsupported, "not a file")
            if ext not in SUPPORTED_EXTENSIONS:
                return (
                    LinkType.format_unsupported,
                    f"unsupported archive format: {ext}",
                )
            if "binary" not in self._formats and ext == WHEEL_EXTENSION:
                reason = f"No binaries permitted for {self.project_name}"
                return (LinkType.format_unsupported, reason)
            if "macosx10" in link.path and ext == ".zip":
                return (LinkType.format_unsupported, "macosx10 one")
            if ext == WHEEL_EXTENSION:
                try:
                    wheel = Wheel(link.filename)
                except InvalidWheelFilename:
                    return (
                        LinkType.format_invalid,
                        "invalid wheel filename",
                    )
                if canonicalize_name(wheel.name) != self._canonical_name:
                    reason = f"wrong project name (not {self.project_name})"
                    return (LinkType.different_project, reason)

                supported_tags = self._target_python.get_unsorted_tags()
                if not wheel.supported(supported_tags):
                    # Include the wheel's tags in the reason string to
                    # simplify troubleshooting compatibility issues.
                    file_tags = ", ".join(wheel.get_formatted_file_tags())
                    reason = (
                        f"none of the wheel's tags ({file_tags}) are compatible "
                        f"(run pip debug --verbose to show compatible tags)"
                    )
                    return (LinkType.platform_mismatch, reason)

                version = wheel.version

        # This should be up by the self.ok_binary check, but see issue 2700.
        if "source" not in self._formats and ext != WHEEL_EXTENSION:
            reason = f"No sources permitted for {self.project_name}"
            return (LinkType.format_unsupported, reason)

        if not version:
            version = _extract_version_from_fragment(
                egg_info,
                self._canonical_name,
            )
        if not version:
            reason = f"Missing project version for {self.project_name}"
            return (LinkType.format_invalid, reason)

        match = self._py_version_re.search(version)
        if match:
            version = version[: match.start()]
            py_version = match.group(1)
            if py_version != self._target_python.py_version:
                return (
                    LinkType.platform_mismatch,
                    "Python version is incorrect",
                )

        supports_python = _check_link_requires_python(
            link,
            version_info=self._target_python.py_version_info,
            ignore_requires_python=self._ignore_requires_python,
        )
        if not supports_python:
            reason = f"{version} Requires-Python {link.requires_python}"
            return (LinkType.requires_python_mismatch, reason)

        logger.debug("Found link %s, version: %s", link, version)

        return (LinkType.candidate, version)


def filter_unallowed_hashes(
    candidates: List[InstallationCandidate],
    hashes: Optional[Hashes],
    project_name: str,
) -> List[InstallationCandidate]:
    """
    Filter out candidates whose hashes aren't allowed, and return a new
    list of candidates.

    If at least one candidate has an allowed hash, then all candidates with
    either an allowed hash or no hash specified are returned.  Otherwise,
    the given candidates are returned.

    Including the candidates with no hash specified when there is a match
    allows a warning to be logged if there is a more preferred candidate
    with no hash specified.  Returning all candidates in the case of no
    matches lets pip report the hash of the candidate that would otherwise
    have been installed (e.g. permitting the user to more easily update
    their requirements file with the desired hash).
    """
    if not hashes:
        logger.debug(
            "Given no hashes to check %s links for project %r: "
            "discarding no candidates",
            len(candidates),
            project_name,
        )
        # Make sure we're not returning back the given value.
        return list(candidates)

    matches_or_no_digest = []
    # Collect the non-matches for logging purposes.
    non_matches = []
    match_count = 0
    for candidate in candidates:
        link = candidate.link
        if not link.has_hash:
            pass
        elif link.is_hash_allowed(hashes=hashes):
            match_count += 1
        else:
            non_matches.append(candidate)
            continue

        matches_or_no_digest.append(candidate)

    if match_count:
        filtered = matches_or_no_digest
    else:
        # Make sure we're not returning back the given value.
        filtered = list(candidates)

    if len(filtered) == len(candidates):
        discard_message = "discarding no candidates"
    else:
        discard_message = "discarding {} non-matches:\n  {}".format(
            len(non_matches),
            "\n  ".join(str(candidate.link) for candidate in non_matches),
        )

    logger.debug(
        "Checked %s links for project %r against %s hashes "
        "(%s matches, %s no digest): %s",
        len(candidates),
        project_name,
        hashes.digest_count,
        match_count,
        len(matches_or_no_digest) - match_count,
        discard_message,
    )

    return filtered


@dataclass
class CandidatePreferences:
    """
    Encapsulates some of the preferences for filtering and sorting
    InstallationCandidate objects.
    """

    prefer_binary: bool = False
    allow_all_prereleases: bool = False


@dataclass(frozen=True)
class BestCandidateResult:
    """A collection of candidates, returned by `PackageFinder.find_best_candidate`.

    This class is only intended to be instantiated by CandidateEvaluator's
    `compute_best_candidate()` method.

    :param all_candidates: A sequence of all available candidates found.
    :param applicable_candidates: The applicable candidates.
    :param best_candidate: The most preferred candidate found, or None
        if no applicable candidates were found.
    """

    all_candidates: List[InstallationCandidate]
    applicable_candidates: List[InstallationCandidate]
    best_candidate: Optional[InstallationCandidate]

    def __post_init__(self) -> None:
        assert set(self.applicable_candidates) <= set(self.all_candidates)

        if self.best_candidate is None:
            assert not self.applicable_candidates
        else:
            assert self.best_candidate in self.applicable_candidates


class CandidateEvaluator:
    """
    Responsible for filtering and sorting candidates for installation based
    on what tags are valid.
    """

    @classmethod
    def create(
        cls,
        project_name: str,
        target_python: Optional[TargetPython] = None,
        prefer_binary: bool = False,
        allow_all_prereleases: bool = False,
        specifier: Optional[specifiers.BaseSpecifier] = None,
        hashes: Optional[Hashes] = None,
    ) -> "CandidateEvaluator":
        """Create a CandidateEvaluator object.

        :param target_python: The target Python interpreter to use when
            checking compatibility. If None (the default), a TargetPython
            object will be constructed from the running Python.
        :param specifier: An optional object implementing `filter`
            (e.g. `packaging.specifiers.SpecifierSet`) to filter applicable
            versions.
        :param hashes: An optional collection of allowed hashes.
        """
        if target_python is None:
            target_python = TargetPython()
        if specifier is None:
            specifier = specifiers.SpecifierSet()

        supported_tags = target_python.get_sorted_tags()

        return cls(
            project_name=project_name,
            supported_tags=supported_tags,
            specifier=specifier,
            prefer_binary=prefer_binary,
            allow_all_prereleases=allow_all_prereleases,
            hashes=hashes,
        )

    def __init__(
        self,
        project_name: str,
        supported_tags: List[Tag],
        specifier: specifiers.BaseSpecifier,
        prefer_binary: bool = False,
        allow_all_prereleases: bool = False,
        hashes: Optional[Hashes] = None,
    ) -> None:
        """
        :param supported_tags: The PEP 425 tags supported by the target
            Python in order of preference (most preferred first).
        """
        self._allow_all_prereleases = allow_all_prereleases
        self._hashes = hashes
        self._prefer_binary = prefer_binary
        self._project_name = project_name
        self._specifier = specifier
        self._supported_tags = supported_tags
        # Since the index of the tag in the _supported_tags list is used
        # as a priority, precompute a map from tag to index/priority to be
        # used in wheel.find_most_preferred_tag.
        self._wheel_tag_preferences = {
            tag: idx for idx, tag in enumerate(supported_tags)
        }

    def get_applicable_candidates(
        self,
        candidates: List[InstallationCandidate],
    ) -> List[InstallationCandidate]:
        """
        Return the applicable candidates from a list of candidates.
        """
        # Using None infers from the specifier instead.
        allow_prereleases = self._allow_all_prereleases or None
        specifier = self._specifier

        # We turn the version object into a str here because otherwise
        # when we're debundled but setuptools isn't, Python will see
        # packaging.version.Version and
        # pkg_resources._vendor.packaging.version.Version as different
        # types. This way we'll use a str as a common data interchange
        # format. If we stop using the pkg_resources provided specifier
        # and start using our own, we can drop the cast to str().
        candidates_and_versions = [(c, str(c.version)) for c in candidates]
        versions = set(
            specifier.filter(
                (v for _, v in candidates_and_versions),
                prereleases=allow_prereleases,
            )
        )

        applicable_candidates = [c for c, v in candidates_and_versions if v in versions]
        filtered_applicable_candidates = filter_unallowed_hashes(
            candidates=applicable_candidates,
            hashes=self._hashes,
            project_name=self._project_name,
        )

        return sorted(filtered_applicable_candidates, key=self._sort_key)

    def _sort_key(self, candidate: InstallationCandidate) -> CandidateSortingKey:
        """
        Function to pass as the `key` argument to a call to sorted() to sort
        InstallationCandidates by preference.

        Returns a tuple such that tuples sorting as greater using Python's
        default comparison operator are more preferred.

        The preference is as follows:

        First and foremost, candidates with allowed (matching) hashes are
        always preferred over candidates without matching hashes. This is
        because e.g. if the only candidate with an allowed hash is yanked,
        we still want to use that candidate.

        Second, excepting hash considerations, candidates that have been
        yanked (in the sense of PEP 592) are always less preferred than
        candidates that haven't been yanked. Then:

        If not finding wheels, they are sorted by version only.
        If finding wheels, then the sort order is by version, then:
          1. existing installs
          2. wheels ordered via Wheel.support_index_min(self._supported_tags)
          3. source archives
        If prefer_binary was set, then all wheels are sorted above sources.

        Note: it was considered to embed this logic into the Link
              comparison operators, but then different sdist links
              with the same version, would have to be considered equal
        """
        valid_tags = self._supported_tags
        support_num = len(valid_tags)
        build_tag: BuildTag = ()
        binary_preference = 0
        link = candidate.link
        if link.is_wheel:
            # can raise InvalidWheelFilename
            wheel = Wheel(link.filename)
            try:
                pri = -(
                    wheel.find_most_preferred_tag(
                        valid_tags, self._wheel_tag_preferences
                    )
                )
            except ValueError:
                raise UnsupportedWheel(
                    f"{wheel.filename} is not a supported wheel for this platform. It "
                    "can't be sorted."
                )
            if self._prefer_binary:
                binary_preference = 1
            if wheel.build_tag is not None:
                match = re.match(r"^(\d+)(.*)$", wheel.build_tag)
                assert match is not None, "guaranteed by filename validation"
                build_tag_groups = match.groups()
                build_tag = (int(build_tag_groups[0]), build_tag_groups[1])
        else:  # sdist
            pri = -(support_num)
        has_allowed_hash = int(link.is_hash_allowed(self._hashes))
        yank_value = -1 * int(link.is_yanked)  # -1 for yanked.
        return (
            has_allowed_hash,
            yank_value,
            binary_preference,
            candidate.version,
            pri,
            build_tag,
        )

    def sort_best_candidate(
        self,
        candidates: List[InstallationCandidate],
    ) -> Optional[InstallationCandidate]:
        """
        Return the best candidate per the instance's sort order, or None if
        no candidate is acceptable.
        """
        if not candidates:
            return None
        best_candidate = max(candidates, key=self._sort_key)
        return best_candidate

    def compute_best_candidate(
        self,
        candidates: List[InstallationCandidate],
    ) -> BestCandidateResult:
        """
        Compute and return a `BestCandidateResult` instance.
        """
        applicable_candidates = self.get_applicable_candidates(candidates)

        best_candidate = self.sort_best_candidate(applicable_candidates)

        return BestCandidateResult(
            candidates,
            applicable_candidates=applicable_candidates,
            best_candidate=best_candidate,
        )


class PackageFinder:
    """This finds packages.

    This is meant to match easy_install's technique for looking for
    packages, by reading pages and looking for appropriate links.
    """

    def __init__(
        self,
        link_collector: LinkCollector,
        target_python: TargetPython,
        allow_yanked: bool,
        format_control: Optional[FormatControl] = None,
        candidate_prefs: Optional[CandidatePreferences] = None,
        ignore_requires_python: Optional[bool] = None,
    ) -> None:
        """
        This constructor is primarily meant to be used by the create() class
        method and from tests.

        :param format_control: A FormatControl object, used to control
            the selection of source packages / binary packages when consulting
            the index and links.
        :param candidate_prefs: Options to use when creating a
            CandidateEvaluator object.
        """
        if candidate_prefs is None:
            candidate_prefs = CandidatePreferences()

        format_control = format_control or FormatControl(set(), set())

        self._allow_yanked = allow_yanked
        self._candidate_prefs = candidate_prefs
        self._ignore_requires_python = ignore_requires_python
        self._link_collector = link_collector
        self._target_python = target_python

        self.format_control = format_control

        # These are boring links that have already been logged somehow.
        self._logged_links: Set[Tuple[Link, LinkType, str]] = set()

    # Don't include an allow_yanked default value to make sure each call
    # site considers whether yanked releases are allowed. This also causes
    # that decision to be made explicit in the calling code, which helps
    # people when reading the code.
    @classmethod
    def create(
        cls,
        link_collector: LinkCollector,
        selection_prefs: SelectionPreferences,
        target_python: Optional[TargetPython] = None,
    ) -> "PackageFinder":
        """Create a PackageFinder.

        :param selection_prefs: The candidate selection preferences, as a
            SelectionPreferences object.
        :param target_python: The target Python interpreter to use when
            checking compatibility. If None (the default), a TargetPython
            object will be constructed from the running Python.
        """
        if target_python is None:
            target_python = TargetPython()

        candidate_prefs = CandidatePreferences(
            prefer_binary=selection_prefs.prefer_binary,
            allow_all_prereleases=selection_prefs.allow_all_prereleases,
        )

        return cls(
            candidate_prefs=candidate_prefs,
            link_collector=link_collector,
            target_python=target_python,
            allow_yanked=selection_prefs.allow_yanked,
            format_control=selection_prefs.format_control,
            ignore_requires_python=selection_prefs.ignore_requires_python,
        )

    @property
    def target_python(self) -> TargetPython:
        return self._target_python

    @property
    def search_scope(self) -> SearchScope:
        return self._link_collector.search_scope

    @search_scope.setter
    def search_scope(self, search_scope: SearchScope) -> None:
        self._link_collector.search_scope = search_scope

    @property
    def find_links(self) -> List[str]:
        return self._link_collector.find_links

    @property
    def index_urls(self) -> List[str]:
        return self.search_scope.index_urls

    @property
    def proxy(self) -> Optional[str]:
        return self._link_collector.session.pip_proxy

    @property
    def trusted_hosts(self) -> Iterable[str]:
        for host_port in self._link_collector.session.pip_trusted_origins:
            yield build_netloc(*host_port)

    @property
    def custom_cert(self) -> Optional[str]:
        # session.verify is either a boolean (use default bundle/no SSL
        # verification) or a string path to a custom CA bundle to use. We only
        # care about the latter.
        verify = self._link_collector.session.verify
        return verify if isinstance(verify, str) else None

    @property
    def client_cert(self) -> Optional[str]:
        cert = self._link_collector.session.cert
        assert not isinstance(cert, tuple), "pip only supports PEM client certs"
        return cert

    @property
    def allow_all_prereleases(self) -> bool:
        return self._candidate_prefs.allow_all_prereleases

    def set_allow_all_prereleases(self) -> None:
        self._candidate_prefs.allow_all_prereleases = True

    @property
    def prefer_binary(self) -> bool:
        return self._candidate_prefs.prefer_binary

    def set_prefer_binary(self) -> None:
        self._candidate_prefs.prefer_binary = True

    def requires_python_skipped_reasons(self) -> List[str]:
        reasons = {
            detail
            for _, result, detail in self._logged_links
            if result == LinkType.requires_python_mismatch
        }
        return sorted(reasons)

    def make_link_evaluator(self, project_name: str) -> LinkEvaluator:
        canonical_name = canonicalize_name(project_name)
        formats = self.format_control.get_allowed_formats(canonical_name)

        return LinkEvaluator(
            project_name=project_name,
            canonical_name=canonical_name,
            formats=formats,
            target_python=self._target_python,
            allow_yanked=self._allow_yanked,
            ignore_requires_python=self._ignore_requires_python,
        )

    def _sort_links(self, links: Iterable[Link]) -> List[Link]:
        """
        Returns elements of links in order, non-egg links first, egg links
        second, while eliminating duplicates
        """
        eggs, no_eggs = [], []
        seen: Set[Link] = set()
        for link in links:
            if link not in seen:
                seen.add(link)
                if link.egg_fragment:
                    eggs.append(link)
                else:
                    no_eggs.append(link)
        return no_eggs + eggs

    def _log_skipped_link(self, link: Link, result: LinkType, detail: str) -> None:
        # This is a hot method so don't waste time hashing links unless we're
        # actually going to log 'em.
        if not logger.isEnabledFor(logging.DEBUG):
            return

        entry = (link, result, detail)
        if entry not in self._logged_links:
            # Put the link at the end so the reason is more visible and because
            # the link string is usually very long.
            logger.debug("Skipping link: %s: %s", detail, link)
            self._logged_links.add(entry)

    def get_install_candidate(
        self, link_evaluator: LinkEvaluator, link: Link
    ) -> Optional[InstallationCandidate]:
        """
        If the link is a candidate for install, convert it to an
        InstallationCandidate and return it. Otherwise, return None.
        """
        result, detail = link_evaluator.evaluate_link(link)
        if result != LinkType.candidate:
            self._log_skipped_link(link, result, detail)
            return None

        try:
            return InstallationCandidate(
                name=link_evaluator.project_name,
                link=link,
                version=detail,
            )
        except InvalidVersion:
            return None

    def evaluate_links(
        self, link_evaluator: LinkEvaluator, links: Iterable[Link]
    ) -> List[InstallationCandidate]:
        """
        Convert links that are candidates to InstallationCandidate objects.
        """
        candidates = []
        for link in self._sort_links(links):
            candidate = self.get_install_candidate(link_evaluator, link)
            if candidate is not None:
                candidates.append(candidate)

        return candidates

    def process_project_url(
        self, project_url: Link, link_evaluator: LinkEvaluator
    ) -> List[InstallationCandidate]:
        logger.debug(
            "Fetching project page and analyzing links: %s",
            project_url,
        )
        index_response = self._link_collector.fetch_response(project_url)
        if index_response is None:
            return []

        page_links = list(parse_links(index_response))

        with indent_log():
            package_links = self.evaluate_links(
                link_evaluator,
                links=page_links,
            )

        return package_links

    @functools.lru_cache(maxsize=None)
    def find_all_candidates(self, project_name: str) -> List[InstallationCandidate]:
        """Find all available InstallationCandidate for project_name

        This checks index_urls and find_links.
        All versions found are returned as an InstallationCandidate list.

        See LinkEvaluator.evaluate_link() for details on which files
        are accepted.
        """
        link_evaluator = self.make_link_evaluator(project_name)

        collected_sources = self._link_collector.collect_sources(
            project_name=project_name,
            candidates_from_page=functools.partial(
                self.process_project_url,
                link_evaluator=link_evaluator,
            ),
        )

        page_candidates_it = itertools.chain.from_iterable(
            source.page_candidates()
            for sources in collected_sources
            for source in sources
            if source is not None
        )
        page_candidates = list(page_candidates_it)

        file_links_it = itertools.chain.from_iterable(
            source.file_links()
            for sources in collected_sources
            for source in sources
            if source is not None
        )
        file_candidates = self.evaluate_links(
            link_evaluator,
            sorted(file_links_it, reverse=True),
        )

        if logger.isEnabledFor(logging.DEBUG) and file_candidates:
            paths = []
            for candidate in file_candidates:
                assert candidate.link.url  # we need to have a URL
                try:
                    paths.append(candidate.link.file_path)
                except Exception:
                    paths.append(candidate.link.url)  # it's not a local file

            logger.debug("Local files found: %s", ", ".join(paths))

        # This is an intentional priority ordering
        return file_candidates + page_candidates

    def make_candidate_evaluator(
        self,
        project_name: str,
        specifier: Optional[specifiers.BaseSpecifier] = None,
        hashes: Optional[Hashes] = None,
    ) -> CandidateEvaluator:
        """Create a CandidateEvaluator object to use."""
        candidate_prefs = self._candidate_prefs
        return CandidateEvaluator.create(
            project_name=project_name,
            target_python=self._target_python,
            prefer_binary=candidate_prefs.prefer_binary,
            allow_all_prereleases=candidate_prefs.allow_all_prereleases,
            specifier=specifier,
            hashes=hashes,
        )

    @functools.lru_cache(maxsize=None)
    def find_best_candidate(
        self,
        project_name: str,
        specifier: Optional[specifiers.BaseSpecifier] = None,
        hashes: Optional[Hashes] = None,
    ) -> BestCandidateResult:
        """Find matches for the given project and specifier.

        :param specifier: An optional object implementing `filter`
            (e.g. `packaging.specifiers.SpecifierSet`) to filter applicable
            versions.

        :return: A `BestCandidateResult` instance.
        """
        candidates = self.find_all_candidates(project_name)
        candidate_evaluator = self.make_candidate_evaluator(
            project_name=project_name,
            specifier=specifier,
            hashes=hashes,
        )
        return candidate_evaluator.compute_best_candidate(candidates)

    def find_requirement(
        self, req: InstallRequirement, upgrade: bool
    ) -> Optional[InstallationCandidate]:
        """Try to find a Link matching req

        Expects req, an InstallRequirement and upgrade, a boolean
        Returns a InstallationCandidate if found,
        Raises DistributionNotFound or BestVersionAlreadyInstalled otherwise
        """
        hashes = req.hashes(trust_internet=False)
        best_candidate_result = self.find_best_candidate(
            req.name,
            specifier=req.specifier,
            hashes=hashes,
        )
        best_candidate = best_candidate_result.best_candidate

        installed_version: Optional[_BaseVersion] = None
        if req.satisfied_by is not None:
            installed_version = req.satisfied_by.version

        def _format_versions(cand_iter: Iterable[InstallationCandidate]) -> str:
            # This repeated parse_version and str() conversion is needed to
            # handle different vendoring sources from pip and pkg_resources.
            # If we stop using the pkg_resources provided specifier and start
            # using our own, we can drop the cast to str().
            return (
                ", ".join(
                    sorted(
                        {str(c.version) for c in cand_iter},
                        key=parse_version,
                    )
                )
                or "none"
            )

        if installed_version is None and best_candidate is None:
            logger.critical(
                "Could not find a version that satisfies the requirement %s "
                "(from versions: %s)",
                req,
                _format_versions(best_candidate_result.all_candidates),
            )

            raise DistributionNotFound(f"No matching distribution found for {req}")

        def _should_install_candidate(
            candidate: Optional[InstallationCandidate],
        ) -> "TypeGuard[InstallationCandidate]":
            if installed_version is None:
                return True
            if best_candidate is None:
                return False
            return best_candidate.version > installed_version

        if not upgrade and installed_version is not None:
            if _should_install_candidate(best_candidate):
                logger.debug(
                    "Existing installed version (%s) satisfies requirement "
                    "(most up-to-date version is %s)",
                    installed_version,
                    best_candidate.version,
                )
            else:
                logger.debug(
                    "Existing installed version (%s) is most up-to-date and "
                    "satisfies requirement",
                    installed_version,
                )
            return None

        if _should_install_candidate(best_candidate):
            logger.debug(
                "Using version %s (newest of versions: %s)",
                best_candidate.version,
                _format_versions(best_candidate_result.applicable_candidates),
            )
            return best_candidate

        # We have an existing version, and its the best version
        logger.debug(
            "Installed version (%s) is most up-to-date (past versions: %s)",
            installed_version,
            _format_versions(best_candidate_result.applicable_candidates),
        )
        raise BestVersionAlreadyInstalled


def _find_name_version_sep(fragment: str, canonical_name: str) -> int:
    """Find the separator's index based on the package's canonical name.

    :param fragment: A <package>+<version> filename "fragment" (stem) or
        egg fragment.
    :param canonical_name: The package's canonical name.

    This function is needed since the canonicalized name does not necessarily
    have the same length as the egg info's name part. An example::

    >>> fragment = 'foo__bar-1.0'
    >>> canonical_name = 'foo-bar'
    >>> _find_name_version_sep(fragment, canonical_name)
    8
    """
    # Project name and version must be separated by one single dash. Find all
    # occurrences of dashes; if the string in front of it matches the canonical
    # name, this is the one separating the name and version parts.
    for i, c in enumerate(fragment):
        if c != "-":
            continue
        if canonicalize_name(fragment[:i]) == canonical_name:
            return i
    raise ValueError(f"{fragment} does not match {canonical_name}")


def _extract_version_from_fragment(fragment: str, canonical_name: str) -> Optional[str]:
    """Parse the version string from a <package>+<version> filename
    "fragment" (stem) or egg fragment.

    :param fragment: The string to parse. E.g. foo-2.1
    :param canonical_name: The canonicalized name of the package this
        belongs to.
    """
    try:
        version_start = _find_name_version_sep(fragment, canonical_name) + 1
    except ValueError:
        return None
    version = fragment[version_start:]
    if not version:
        return None
    return version

# === NexusCore/openenv\Lib\site-packages\litellm\llms\bedrock\chat\converse_transformation.py ===
"""
Translating between OpenAI's `/chat/completion` format and Amazon's `/converse` format
"""

import copy
import time
import types
from typing import List, Literal, Optional, Tuple, Union, cast, overload

import httpx

import litellm
from litellm.litellm_core_utils.core_helpers import map_finish_reason
from litellm.litellm_core_utils.litellm_logging import Logging
from litellm.litellm_core_utils.llm_response_utils.convert_dict_to_response import (
    _parse_content_for_reasoning,
)
from litellm.litellm_core_utils.prompt_templates.factory import (
    BedrockConverseMessagesProcessor,
    _bedrock_converse_messages_pt,
    _bedrock_tools_pt,
)
from litellm.llms.anthropic.chat.transformation import AnthropicConfig
from litellm.llms.base_llm.chat.transformation import BaseConfig, BaseLLMException
from litellm.types.llms.bedrock import *
from litellm.types.llms.openai import (
    AllMessageValues,
    ChatCompletionRedactedThinkingBlock,
    ChatCompletionResponseMessage,
    ChatCompletionSystemMessage,
    ChatCompletionThinkingBlock,
    ChatCompletionToolCallChunk,
    ChatCompletionToolCallFunctionChunk,
    ChatCompletionToolParam,
    ChatCompletionToolParamFunctionChunk,
    ChatCompletionUserMessage,
    OpenAIChatCompletionToolParam,
    OpenAIMessageContentListBlock,
)
from litellm.types.utils import (
    ChatCompletionMessageToolCall,
    Function,
    Message,
    ModelResponse,
    PromptTokensDetailsWrapper,
    Usage,
)
from litellm.utils import add_dummy_tool, has_tool_call_blocks, supports_reasoning

from ..common_utils import BedrockError, BedrockModelInfo, get_bedrock_tool_name


class AmazonConverseConfig(BaseConfig):
    """
    Reference - https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_Converse.html
    #2 - https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference.html#conversation-inference-supported-models-features
    """

    maxTokens: Optional[int]
    stopSequences: Optional[List[str]]
    temperature: Optional[int]
    topP: Optional[int]
    topK: Optional[int]

    def __init__(
        self,
        maxTokens: Optional[int] = None,
        stopSequences: Optional[List[str]] = None,
        temperature: Optional[int] = None,
        topP: Optional[int] = None,
        topK: Optional[int] = None,
    ) -> None:
        locals_ = locals().copy()
        for key, value in locals_.items():
            if key != "self" and value is not None:
                setattr(self.__class__, key, value)

    @property
    def custom_llm_provider(self) -> Optional[str]:
        return "bedrock_converse"

    @classmethod
    def get_config_blocks(cls) -> dict:
        return {
            "guardrailConfig": GuardrailConfigBlock,
            "performanceConfig": PerformanceConfigBlock,
        }

    @classmethod
    def get_config(cls):
        return {
            k: v
            for k, v in cls.__dict__.items()
            if not k.startswith("__")
            and not isinstance(
                v,
                (
                    types.FunctionType,
                    types.BuiltinFunctionType,
                    classmethod,
                    staticmethod,
                ),
            )
            and v is not None
        }

    def get_supported_openai_params(self, model: str) -> List[str]:
        from litellm.utils import supports_function_calling

        supported_params = [
            "max_tokens",
            "max_completion_tokens",
            "stream",
            "stream_options",
            "stop",
            "temperature",
            "top_p",
            "extra_headers",
            "response_format",
        ]

        if (
            "arn" in model
        ):  # we can't infer the model from the arn, so just add all params
            supported_params.append("tools")
            supported_params.append("tool_choice")
            supported_params.append("thinking")
            supported_params.append("reasoning_effort")
            return supported_params

        ## Filter out 'cross-region' from model name
        base_model = BedrockModelInfo.get_base_model(model)

        if (
            base_model.startswith("anthropic")
            or base_model.startswith("mistral")
            or base_model.startswith("cohere")
            or base_model.startswith("meta.llama3-1")
            or base_model.startswith("meta.llama3-2")
            or base_model.startswith("meta.llama3-3")
            or base_model.startswith("amazon.nova")
            or supports_function_calling(
                model=model, custom_llm_provider=self.custom_llm_provider
            )
        ):
            supported_params.append("tools")

        if litellm.utils.supports_tool_choice(
            model=model, custom_llm_provider=self.custom_llm_provider
        ):
            # only anthropic and mistral support tool choice config. otherwise (E.g. cohere) will fail the call - https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolChoice.html
            supported_params.append("tool_choice")

        if (
            "claude-3-7" in model
            or "claude-sonnet-4" in model
            or "claude-opus-4" in model
            or supports_reasoning(
                model=model,
                custom_llm_provider=self.custom_llm_provider,
            )
        ):
            supported_params.append("thinking")
            supported_params.append("reasoning_effort")
        return supported_params

    def map_tool_choice_values(
        self, model: str, tool_choice: Union[str, dict], drop_params: bool
    ) -> Optional[ToolChoiceValuesBlock]:
        if tool_choice == "none":
            if litellm.drop_params is True or drop_params is True:
                return None
            else:
                raise litellm.utils.UnsupportedParamsError(
                    message="Bedrock doesn't support tool_choice={}. To drop it from the call, set `litellm.drop_params = True.".format(
                        tool_choice
                    ),
                    status_code=400,
                )
        elif tool_choice == "required":
            return ToolChoiceValuesBlock(any={})
        elif tool_choice == "auto":
            return ToolChoiceValuesBlock(auto={})
        elif isinstance(tool_choice, dict):
            # only supported for anthropic + mistral models - https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ToolChoice.html
            specific_tool = SpecificToolChoiceBlock(
                name=tool_choice.get("function", {}).get("name", "")
            )
            return ToolChoiceValuesBlock(tool=specific_tool)
        else:
            raise litellm.utils.UnsupportedParamsError(
                message="Bedrock doesn't support tool_choice={}. Supported tool_choice values=['auto', 'required', json object]. To drop it from the call, set `litellm.drop_params = True.".format(
                    tool_choice
                ),
                status_code=400,
            )

    def get_supported_image_types(self) -> List[str]:
        return ["png", "jpeg", "gif", "webp"]

    def get_supported_document_types(self) -> List[str]:
        return ["pdf", "csv", "doc", "docx", "xls", "xlsx", "html", "txt", "md"]

    def get_supported_video_types(self) -> List[str]:
        return ["mp4", "mov", "mkv", "webm", "flv", "mpeg", "mpg", "wmv", "3gp"]

    def get_all_supported_content_types(self) -> List[str]:
        return (
            self.get_supported_image_types()
            + self.get_supported_document_types()
            + self.get_supported_video_types()
        )

    def _create_json_tool_call_for_response_format(
        self,
        json_schema: Optional[dict] = None,
        schema_name: str = "json_tool_call",
        description: Optional[str] = None,
    ) -> ChatCompletionToolParam:
        """
        Handles creating a tool call for getting responses in JSON format.

        Args:
            json_schema (Optional[dict]): The JSON schema the response should be in

        Returns:
            AnthropicMessagesTool: The tool call to send to Anthropic API to get responses in JSON format
        """

        if json_schema is None:
            # Anthropic raises a 400 BadRequest error if properties is passed as None
            # see usage with additionalProperties (Example 5) https://github.com/anthropics/anthropic-cookbook/blob/main/tool_use/extracting_structured_json.ipynb
            _input_schema = {
                "type": "object",
                "additionalProperties": True,
                "properties": {},
            }
        else:
            _input_schema = json_schema

        tool_param_function_chunk = ChatCompletionToolParamFunctionChunk(
            name=schema_name, parameters=_input_schema
        )
        if description:
            tool_param_function_chunk["description"] = description

        _tool = ChatCompletionToolParam(
            type="function",
            function=tool_param_function_chunk,
        )
        return _tool

    def _apply_tool_call_transformation(
        self,
        tools: List[OpenAIChatCompletionToolParam],
        model: str,
        non_default_params: dict,
        optional_params: dict,
    ):
        optional_params = self._add_tools_to_optional_params(
            optional_params=optional_params, tools=tools
        )

        if (
            "meta.llama3-3-70b-instruct-v1:0" in model
            and non_default_params.get("stream", False) is True
        ):
            optional_params["fake_stream"] = True

    def map_openai_params(
        self,
        non_default_params: dict,
        optional_params: dict,
        model: str,
        drop_params: bool,
    ) -> dict:
        is_thinking_enabled = self.is_thinking_enabled(non_default_params)

        for param, value in non_default_params.items():
            if param == "response_format" and isinstance(value, dict):
                ignore_response_format_types = ["text"]
                if value["type"] in ignore_response_format_types:  # value is a no-op
                    continue

                json_schema: Optional[dict] = None
                schema_name: str = ""
                description: Optional[str] = None
                if "response_schema" in value:
                    json_schema = value["response_schema"]
                    schema_name = "json_tool_call"
                elif "json_schema" in value:
                    json_schema = value["json_schema"]["schema"]
                    schema_name = value["json_schema"]["name"]
                    description = value["json_schema"].get("description")

                if "type" in value and value["type"] == "text":
                    continue

                """
                Follow similar approach to anthropic - translate to a single tool call. 

                When using tools in this way: - https://docs.anthropic.com/en/docs/build-with-claude/tool-use#json-mode
                - You usually want to provide a single tool
                - You should set tool_choice (see Forcing tool use) to instruct the model to explicitly use that tool
                - Remember that the model will pass the input to the tool, so the name of the tool and description should be from the model’s perspective.
                """
                _tool = self._create_json_tool_call_for_response_format(
                    json_schema=json_schema,
                    schema_name=schema_name if schema_name != "" else "json_tool_call",
                    description=description,
                )
                optional_params = self._add_tools_to_optional_params(
                    optional_params=optional_params, tools=[_tool]
                )
                if (
                    litellm.utils.supports_tool_choice(
                        model=model, custom_llm_provider=self.custom_llm_provider
                    )
                    and not is_thinking_enabled
                ):
                    optional_params["tool_choice"] = ToolChoiceValuesBlock(
                        tool=SpecificToolChoiceBlock(
                            name=schema_name if schema_name != "" else "json_tool_call"
                        )
                    )
                optional_params["json_mode"] = True
                if non_default_params.get("stream", False) is True:
                    optional_params["fake_stream"] = True
            if param == "max_tokens" or param == "max_completion_tokens":
                optional_params["maxTokens"] = value
            if param == "stream":
                optional_params["stream"] = value
            if param == "stop":
                if isinstance(value, str):
                    if len(value) == 0:  # converse raises error for empty strings
                        continue
                    value = [value]
                optional_params["stopSequences"] = value
            if param == "temperature":
                optional_params["temperature"] = value
            if param == "top_p":
                optional_params["topP"] = value
            if param == "tools" and isinstance(value, list):
                self._apply_tool_call_transformation(
                    tools=cast(List[OpenAIChatCompletionToolParam], value),
                    model=model,
                    non_default_params=non_default_params,
                    optional_params=optional_params,
                )
            if param == "tool_choice":
                _tool_choice_value = self.map_tool_choice_values(
                    model=model, tool_choice=value, drop_params=drop_params  # type: ignore
                )
                if _tool_choice_value is not None:
                    optional_params["tool_choice"] = _tool_choice_value
            if param == "thinking":
                optional_params["thinking"] = value
            elif param == "reasoning_effort" and isinstance(value, str):
                optional_params["thinking"] = AnthropicConfig._map_reasoning_effort(
                    value
                )

        self.update_optional_params_with_thinking_tokens(
            non_default_params=non_default_params, optional_params=optional_params
        )

        return optional_params

    def update_optional_params_with_thinking_tokens(
        self, non_default_params: dict, optional_params: dict
    ):
        """
        Handles scenario where max tokens is not specified. For anthropic models (anthropic api/bedrock/vertex ai), this requires having the max tokens being set and being greater than the thinking token budget.

        Checks 'non_default_params' for 'thinking' and 'max_tokens'

        if 'thinking' is enabled and 'max_tokens' is not specified, set 'max_tokens' to the thinking token budget + DEFAULT_MAX_TOKENS
        """
        from litellm.constants import DEFAULT_MAX_TOKENS

        is_thinking_enabled = self.is_thinking_enabled(optional_params)
        is_max_tokens_in_request = self.is_max_tokens_in_request(non_default_params)
        if is_thinking_enabled and not is_max_tokens_in_request:
            thinking_token_budget = cast(dict, optional_params["thinking"]).get(
                "budget_tokens", None
            )
            if thinking_token_budget is not None:
                optional_params["maxTokens"] = (
                    thinking_token_budget + DEFAULT_MAX_TOKENS
                )

    @overload
    def _get_cache_point_block(
        self,
        message_block: Union[
            OpenAIMessageContentListBlock,
            ChatCompletionUserMessage,
            ChatCompletionSystemMessage,
        ],
        block_type: Literal["system"],
    ) -> Optional[SystemContentBlock]:
        pass

    @overload
    def _get_cache_point_block(
        self,
        message_block: Union[
            OpenAIMessageContentListBlock,
            ChatCompletionUserMessage,
            ChatCompletionSystemMessage,
        ],
        block_type: Literal["content_block"],
    ) -> Optional[ContentBlock]:
        pass

    def _get_cache_point_block(
        self,
        message_block: Union[
            OpenAIMessageContentListBlock,
            ChatCompletionUserMessage,
            ChatCompletionSystemMessage,
        ],
        block_type: Literal["system", "content_block"],
    ) -> Optional[Union[SystemContentBlock, ContentBlock]]:
        if message_block.get("cache_control", None) is None:
            return None
        if block_type == "system":
            return SystemContentBlock(cachePoint=CachePointBlock(type="default"))
        else:
            return ContentBlock(cachePoint=CachePointBlock(type="default"))

    def _transform_system_message(
        self, messages: List[AllMessageValues]
    ) -> Tuple[List[AllMessageValues], List[SystemContentBlock]]:
        system_prompt_indices = []
        system_content_blocks: List[SystemContentBlock] = []
        for idx, message in enumerate(messages):
            if message["role"] == "system":
                system_prompt_indices.append(idx)
                if isinstance(message["content"], str) and message["content"]:
                    system_content_blocks.append(
                        SystemContentBlock(text=message["content"])
                    )
                    cache_block = self._get_cache_point_block(
                        message, block_type="system"
                    )
                    if cache_block:
                        system_content_blocks.append(cache_block)
                elif isinstance(message["content"], list):
                    for m in message["content"]:
                        if m.get("type") == "text" and m.get("text"):
                            system_content_blocks.append(
                                SystemContentBlock(text=m["text"])
                            )
                            cache_block = self._get_cache_point_block(
                                m, block_type="system"
                            )
                            if cache_block:
                                system_content_blocks.append(cache_block)
        if len(system_prompt_indices) > 0:
            for idx in reversed(system_prompt_indices):
                messages.pop(idx)
        return messages, system_content_blocks

    def _transform_inference_params(self, inference_params: dict) -> InferenceConfig:
        if "top_k" in inference_params:
            inference_params["topK"] = inference_params.pop("top_k")
        return InferenceConfig(**inference_params)

    def _handle_top_k_value(self, model: str, inference_params: dict) -> dict:
        base_model = BedrockModelInfo.get_base_model(model)

        val_top_k = None
        if "topK" in inference_params:
            val_top_k = inference_params.pop("topK")
        elif "top_k" in inference_params:
            val_top_k = inference_params.pop("top_k")

        if val_top_k:
            if base_model.startswith("anthropic"):
                return {"top_k": val_top_k}
            if base_model.startswith("amazon.nova"):
                return {"inferenceConfig": {"topK": val_top_k}}

        return {}

    def _transform_request_helper(
        self,
        model: str,
        system_content_blocks: List[SystemContentBlock],
        optional_params: dict,
        messages: Optional[List[AllMessageValues]] = None,
    ) -> CommonRequestObject:
        ## VALIDATE REQUEST
        """
        Bedrock doesn't support tool calling without `tools=` param specified.
        """
        if (
            "tools" not in optional_params
            and messages is not None
            and has_tool_call_blocks(messages)
        ):
            if litellm.modify_params:
                optional_params["tools"] = add_dummy_tool(
                    custom_llm_provider="bedrock_converse"
                )
            else:
                raise litellm.UnsupportedParamsError(
                    message="Bedrock doesn't support tool calling without `tools=` param specified. Pass `tools=` param OR set `litellm.modify_params = True` // `litellm_settings::modify_params: True` to add dummy tool to the request.",
                    model="",
                    llm_provider="bedrock",
                )

        inference_params = copy.deepcopy(optional_params)
        supported_converse_params = list(
            AmazonConverseConfig.__annotations__.keys()
        ) + ["top_k"]
        supported_tool_call_params = ["tools", "tool_choice"]
        supported_config_params = list(self.get_config_blocks().keys())
        total_supported_params = (
            supported_converse_params
            + supported_tool_call_params
            + supported_config_params
        )
        inference_params.pop("json_mode", None)  # used for handling json_schema

        # keep supported params in 'inference_params', and set all model-specific params in 'additional_request_params'
        additional_request_params = {
            k: v for k, v in inference_params.items() if k not in total_supported_params
        }
        inference_params = {
            k: v for k, v in inference_params.items() if k in total_supported_params
        }

        # Only set the topK value in for models that support it
        additional_request_params.update(
            self._handle_top_k_value(model, inference_params)
        )

        bedrock_tools: List[ToolBlock] = _bedrock_tools_pt(
            inference_params.pop("tools", [])
        )
        bedrock_tool_config: Optional[ToolConfigBlock] = None
        if len(bedrock_tools) > 0:
            tool_choice_values: ToolChoiceValuesBlock = inference_params.pop(
                "tool_choice", None
            )
            bedrock_tool_config = ToolConfigBlock(
                tools=bedrock_tools,
            )
            if tool_choice_values is not None:
                bedrock_tool_config["toolChoice"] = tool_choice_values

        data: CommonRequestObject = {
            "additionalModelRequestFields": additional_request_params,
            "system": system_content_blocks,
            "inferenceConfig": self._transform_inference_params(
                inference_params=inference_params
            ),
        }

        # Handle all config blocks
        for config_name, config_class in self.get_config_blocks().items():
            config_value = inference_params.pop(config_name, None)
            if config_value is not None:
                data[config_name] = config_class(**config_value)  # type: ignore

        # Tool Config
        if bedrock_tool_config is not None:
            data["toolConfig"] = bedrock_tool_config

        return data

    async def _async_transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
    ) -> RequestObject:
        messages, system_content_blocks = self._transform_system_message(messages)
        ## TRANSFORMATION ##

        _data: CommonRequestObject = self._transform_request_helper(
            model=model,
            system_content_blocks=system_content_blocks,
            optional_params=optional_params,
            messages=messages,
        )

        bedrock_messages = (
            await BedrockConverseMessagesProcessor._bedrock_converse_messages_pt_async(
                messages=messages,
                model=model,
                llm_provider="bedrock_converse",
                user_continue_message=litellm_params.pop("user_continue_message", None),
            )
        )

        data: RequestObject = {"messages": bedrock_messages, **_data}

        return data

    def transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        headers: dict,
    ) -> dict:
        return cast(
            dict,
            self._transform_request(
                model=model,
                messages=messages,
                optional_params=optional_params,
                litellm_params=litellm_params,
            ),
        )

    def _transform_request(
        self,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
    ) -> RequestObject:
        messages, system_content_blocks = self._transform_system_message(messages)

        _data: CommonRequestObject = self._transform_request_helper(
            model=model,
            system_content_blocks=system_content_blocks,
            optional_params=optional_params,
            messages=messages,
        )

        ## TRANSFORMATION ##
        bedrock_messages: List[MessageBlock] = _bedrock_converse_messages_pt(
            messages=messages,
            model=model,
            llm_provider="bedrock_converse",
            user_continue_message=litellm_params.pop("user_continue_message", None),
        )

        data: RequestObject = {"messages": bedrock_messages, **_data}

        return data

    def transform_response(
        self,
        model: str,
        raw_response: httpx.Response,
        model_response: ModelResponse,
        logging_obj: Logging,
        request_data: dict,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        encoding: Any,
        api_key: Optional[str] = None,
        json_mode: Optional[bool] = None,
    ) -> ModelResponse:
        return self._transform_response(
            model=model,
            response=raw_response,
            model_response=model_response,
            stream=optional_params.get("stream", False),
            logging_obj=logging_obj,
            optional_params=optional_params,
            api_key=api_key,
            data=request_data,
            messages=messages,
            encoding=encoding,
        )

    def _transform_reasoning_content(
        self, reasoning_content_blocks: List[BedrockConverseReasoningContentBlock]
    ) -> str:
        """
        Extract the reasoning text from the reasoning content blocks

        Ensures deepseek reasoning content compatible output.
        """
        reasoning_content_str = ""
        for block in reasoning_content_blocks:
            if "reasoningText" in block:
                reasoning_content_str += block["reasoningText"]["text"]
        return reasoning_content_str

    def _transform_thinking_blocks(
        self, thinking_blocks: List[BedrockConverseReasoningContentBlock]
    ) -> List[Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]]:
        """Return a consistent format for thinking blocks between Anthropic and Bedrock."""
        thinking_blocks_list: List[
            Union[ChatCompletionThinkingBlock, ChatCompletionRedactedThinkingBlock]
        ] = []
        for block in thinking_blocks:
            if "reasoningText" in block:
                _thinking_block = ChatCompletionThinkingBlock(type="thinking")
                _text = block["reasoningText"].get("text")
                _signature = block["reasoningText"].get("signature")
                if _text is not None:
                    _thinking_block["thinking"] = _text
                if _signature is not None:
                    _thinking_block["signature"] = _signature
                thinking_blocks_list.append(_thinking_block)
            elif "redactedContent" in block:
                _redacted_block = ChatCompletionRedactedThinkingBlock(
                    type="redacted_thinking", data=block["redactedContent"]
                )
                thinking_blocks_list.append(_redacted_block)
        return thinking_blocks_list

    def _transform_usage(self, usage: ConverseTokenUsageBlock) -> Usage:
        input_tokens = usage["inputTokens"]
        output_tokens = usage["outputTokens"]
        total_tokens = usage["totalTokens"]
        cache_creation_input_tokens: int = 0
        cache_read_input_tokens: int = 0

        if "cacheReadInputTokens" in usage:
            cache_read_input_tokens = usage["cacheReadInputTokens"]
            input_tokens += cache_read_input_tokens
        if "cacheWriteInputTokens" in usage:
            """
            Do not increment prompt_tokens with cacheWriteInputTokens
            """
            cache_creation_input_tokens = usage["cacheWriteInputTokens"]

        prompt_tokens_details = PromptTokensDetailsWrapper(
            cached_tokens=cache_read_input_tokens
        )
        openai_usage = Usage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=total_tokens,
            prompt_tokens_details=prompt_tokens_details,
            cache_creation_input_tokens=cache_creation_input_tokens,
            cache_read_input_tokens=cache_read_input_tokens,
        )
        return openai_usage

    def get_tool_call_names(
        self,
        tools: Optional[
            Union[List[ToolBlock], List[OpenAIChatCompletionToolParam]]
        ] = None,
    ) -> List[str]:
        if tools is None:
            return []
        tool_set: set[str] = set()
        for tool in tools:
            tool_spec = tool.get("toolSpec")
            function = tool.get("function")
            if tool_spec is not None:
                _name = cast(dict, tool_spec).get("name")
                if _name is not None and isinstance(_name, str):
                    tool_set.add(_name)
            if function is not None:
                _name = cast(dict, function).get("name")
                if _name is not None and isinstance(_name, str):
                    tool_set.add(_name)
        return list(tool_set)

    def apply_tool_call_transformation_if_needed(
        self,
        message: Message,
        tools: Optional[List[ToolBlock]] = None,
        initial_finish_reason: Optional[str] = None,
    ) -> Tuple[Message, Optional[str]]:
        """
        Apply tool call transformation to a message.

        LLM providers (e.g. Bedrock, Vertex AI) sometimes return tool call in the response content.

        If the response content is a JSON object, we can parse it and return the tool call in the tool_calls field.
        """
        returned_finish_reason = initial_finish_reason
        if tools is None:
            return message, returned_finish_reason

        if message.content is not None:
            try:
                tool_call_names = self.get_tool_call_names(tools)
                json_content = json.loads(message.content)
                if (
                    json_content.get("type") == "function"
                    and json_content.get("name") in tool_call_names
                ):
                    tool_calls = [
                        ChatCompletionMessageToolCall(function=Function(**json_content))
                    ]

                    message.tool_calls = tool_calls
                    message.content = None
                    returned_finish_reason = "tool_calls"
            except Exception:
                pass

        return message, returned_finish_reason

    def _translate_message_content(
        self, content_blocks: List[ContentBlock]
    ) -> Tuple[
        str,
        List[ChatCompletionToolCallChunk],
        Optional[List[BedrockConverseReasoningContentBlock]],
    ]:
        """
        Translate the message content to a string and a list of tool calls and reasoning content blocks

        Returns:
            content_str: str
            tools: List[ChatCompletionToolCallChunk]
            reasoningContentBlocks: Optional[List[BedrockConverseReasoningContentBlock]]
        """
        content_str = ""
        tools: List[ChatCompletionToolCallChunk] = []
        reasoningContentBlocks: Optional[
            List[BedrockConverseReasoningContentBlock]
        ] = None
        for idx, content in enumerate(content_blocks):
            """
            - Content is either a tool response or text
            """
            extracted_reasoning_content_str: Optional[str] = None
            if "text" in content:
                (
                    extracted_reasoning_content_str,
                    _content_str,
                ) = _parse_content_for_reasoning(content["text"])
                if _content_str is not None:
                    content_str += _content_str
            if "toolUse" in content:
                ## check tool name was formatted by litellm
                _response_tool_name = content["toolUse"]["name"]
                response_tool_name = get_bedrock_tool_name(
                    response_tool_name=_response_tool_name
                )
                _function_chunk = ChatCompletionToolCallFunctionChunk(
                    name=response_tool_name,
                    arguments=json.dumps(content["toolUse"]["input"]),
                )

                _tool_response_chunk = ChatCompletionToolCallChunk(
                    id=content["toolUse"]["toolUseId"],
                    type="function",
                    function=_function_chunk,
                    index=idx,
                )
                tools.append(_tool_response_chunk)
            if extracted_reasoning_content_str is not None:
                if reasoningContentBlocks is None:
                    reasoningContentBlocks = []
                reasoningContentBlocks.append(
                    BedrockConverseReasoningContentBlock(
                        reasoningText=BedrockConverseReasoningTextBlock(
                            text=extracted_reasoning_content_str,
                        )
                    )
                )
            if "reasoningContent" in content:
                if reasoningContentBlocks is None:
                    reasoningContentBlocks = []
                reasoningContentBlocks.append(content["reasoningContent"])

        return content_str, tools, reasoningContentBlocks

    def _transform_response(
        self,
        model: str,
        response: httpx.Response,
        model_response: ModelResponse,
        stream: bool,
        logging_obj: Optional[Logging],
        optional_params: dict,
        api_key: Optional[str],
        data: Union[dict, str],
        messages: List,
        encoding,
    ) -> ModelResponse:
        ## LOGGING
        if logging_obj is not None:
            logging_obj.post_call(
                input=messages,
                api_key=api_key,
                original_response=response.text,
                additional_args={"complete_input_dict": data},
            )

        json_mode: Optional[bool] = optional_params.pop("json_mode", None)
        ## RESPONSE OBJECT
        try:
            completion_response = ConverseResponseBlock(**response.json())  # type: ignore
        except Exception as e:
            raise BedrockError(
                message="Received={}, Error converting to valid response block={}. File an issue if litellm error - https://github.com/BerriAI/litellm/issues".format(
                    response.text, str(e)
                ),
                status_code=422,
            )

        """
        Bedrock Response Object has optional message block 

        completion_response["output"].get("message", None)

        A message block looks like this (Example 1): 
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "text": "Is there anything else you'd like to talk about? Perhaps I can help with some economic questions or provide some information about economic concepts?"
                    }
                ]
            }
        },
        (Example 2):
        "output": {
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "tooluse_hbTgdi0CSLq_hM4P8csZJA",
                            "name": "top_song",
                            "input": {
                                "sign": "WZPZ"
                            }
                        }
                    }
                ]
            }
        }

        """
        message: Optional[MessageBlock] = completion_response["output"]["message"]
        chat_completion_message: ChatCompletionResponseMessage = {"role": "assistant"}
        content_str = ""
        tools: List[ChatCompletionToolCallChunk] = []
        reasoningContentBlocks: Optional[
            List[BedrockConverseReasoningContentBlock]
        ] = None

        if message is not None:
            (
                content_str,
                tools,
                reasoningContentBlocks,
            ) = self._translate_message_content(message["content"])

        if reasoningContentBlocks is not None:
            chat_completion_message["provider_specific_fields"] = {
                "reasoningContentBlocks": reasoningContentBlocks,
            }
            chat_completion_message[
                "reasoning_content"
            ] = self._transform_reasoning_content(reasoningContentBlocks)
            chat_completion_message[
                "thinking_blocks"
            ] = self._transform_thinking_blocks(reasoningContentBlocks)
        chat_completion_message["content"] = content_str
        if json_mode is True and tools is not None and len(tools) == 1:
            # to support 'json_schema' logic on bedrock models
            json_mode_content_str: Optional[str] = tools[0]["function"].get("arguments")
            if json_mode_content_str is not None:
                chat_completion_message["content"] = json_mode_content_str
        else:
            chat_completion_message["tool_calls"] = tools

        ## CALCULATING USAGE - bedrock returns usage in the headers
        usage = self._transform_usage(completion_response["usage"])

        ## HANDLE TOOL CALLS
        _message = Message(**chat_completion_message)
        initial_finish_reason = map_finish_reason(completion_response["stopReason"])

        (
            returned_message,
            returned_finish_reason,
        ) = self.apply_tool_call_transformation_if_needed(
            message=_message,
            tools=optional_params.get("tools"),
            initial_finish_reason=initial_finish_reason,
        )
        model_response.choices = [
            litellm.Choices(
                finish_reason=returned_finish_reason,
                index=0,
                message=returned_message,
            )
        ]
        model_response.created = int(time.time())
        model_response.model = model

        setattr(model_response, "usage", usage)

        # Add "trace" from Bedrock guardrails - if user has opted in to returning it
        if "trace" in completion_response:
            setattr(model_response, "trace", completion_response["trace"])

        return model_response

    def get_error_class(
        self, error_message: str, status_code: int, headers: Union[dict, httpx.Headers]
    ) -> BaseLLMException:
        return BedrockError(
            message=error_message,
            status_code=status_code,
            headers=headers,
        )

    def validate_environment(
        self,
        headers: dict,
        model: str,
        messages: List[AllMessageValues],
        optional_params: dict,
        litellm_params: dict,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
    ) -> dict:
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

# === NexusCore/openenv\Lib\site-packages\litellm\llms\azure\assistants.py ===
from typing import Any, Coroutine, Dict, Iterable, Literal, Optional, Union

import httpx
from openai import AsyncAzureOpenAI, AzureOpenAI
from typing_extensions import overload

from ...types.llms.openai import (
    Assistant,
    AssistantEventHandler,
    AssistantStreamManager,
    AssistantToolParam,
    AsyncAssistantEventHandler,
    AsyncAssistantStreamManager,
    AsyncCursorPage,
    OpenAICreateThreadParamsMessage,
    OpenAIMessage,
    Run,
    SyncCursorPage,
    Thread,
)
from .common_utils import BaseAzureLLM


class AzureAssistantsAPI(BaseAzureLLM):
    def __init__(self) -> None:
        super().__init__()

    def get_azure_client(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AzureOpenAI] = None,
        litellm_params: Optional[dict] = None,
    ) -> AzureOpenAI:
        if client is None:
            azure_client_params = self.initialize_azure_sdk_client(
                litellm_params=litellm_params or {},
                api_key=api_key,
                api_base=api_base,
                model_name="",
                api_version=api_version,
                is_async=False,
            )
            azure_openai_client = AzureOpenAI(**azure_client_params)  # type: ignore
        else:
            azure_openai_client = client

        return azure_openai_client

    def async_get_azure_client(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI] = None,
        litellm_params: Optional[dict] = None,
    ) -> AsyncAzureOpenAI:
        if client is None:
            azure_client_params = self.initialize_azure_sdk_client(
                litellm_params=litellm_params or {},
                api_key=api_key,
                api_base=api_base,
                model_name="",
                api_version=api_version,
                is_async=True,
            )

            azure_openai_client = AsyncAzureOpenAI(**azure_client_params)
            # azure_openai_client = AsyncAzureOpenAI(**data)  # type: ignore
        else:
            azure_openai_client = client

        return azure_openai_client

    ### ASSISTANTS ###

    async def async_get_assistants(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        litellm_params: Optional[dict] = None,
    ) -> AsyncCursorPage[Assistant]:
        azure_openai_client = self.async_get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = await azure_openai_client.beta.assistants.list()

        return response

    # fmt: off

    @overload
    def get_assistants(
        self, 
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        aget_assistants: Literal[True], 
    ) -> Coroutine[None, None, AsyncCursorPage[Assistant]]:
        ...

    @overload
    def get_assistants(
        self, 
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AzureOpenAI],
        aget_assistants: Optional[Literal[False]], 
    ) -> SyncCursorPage[Assistant]: 
        ...

    # fmt: on

    def get_assistants(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client=None,
        aget_assistants=None,
        litellm_params: Optional[dict] = None,
    ):
        if aget_assistants is not None and aget_assistants is True:
            return self.async_get_assistants(
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
                litellm_params=litellm_params,
            )
        azure_openai_client = self.get_azure_client(
            api_key=api_key,
            api_base=api_base,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            api_version=api_version,
            litellm_params=litellm_params,
        )

        response = azure_openai_client.beta.assistants.list()

        return response

    ### MESSAGES ###

    async def a_add_message(
        self,
        thread_id: str,
        message_data: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI] = None,
        litellm_params: Optional[dict] = None,
    ) -> OpenAIMessage:
        openai_client = self.async_get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        thread_message: OpenAIMessage = await openai_client.beta.threads.messages.create(  # type: ignore
            thread_id, **message_data  # type: ignore
        )

        response_obj: Optional[OpenAIMessage] = None
        if getattr(thread_message, "status", None) is None:
            thread_message.status = "completed"
            response_obj = OpenAIMessage(**thread_message.dict())
        else:
            response_obj = OpenAIMessage(**thread_message.dict())
        return response_obj

    # fmt: off

    @overload
    def add_message(
        self,
        thread_id: str,
        message_data: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        a_add_message: Literal[True],
        litellm_params: Optional[dict] = None,
    ) -> Coroutine[None, None, OpenAIMessage]:
        ...

    @overload
    def add_message(
        self,
        thread_id: str,
        message_data: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AzureOpenAI],
        a_add_message: Optional[Literal[False]],
        litellm_params: Optional[dict] = None,
    ) -> OpenAIMessage:
        ...

    # fmt: on

    def add_message(
        self,
        thread_id: str,
        message_data: dict,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client=None,
        a_add_message: Optional[bool] = None,
        litellm_params: Optional[dict] = None,
    ):
        if a_add_message is not None and a_add_message is True:
            return self.a_add_message(
                thread_id=thread_id,
                message_data=message_data,
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
                litellm_params=litellm_params,
            )
        openai_client = self.get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        thread_message: OpenAIMessage = openai_client.beta.threads.messages.create(  # type: ignore
            thread_id, **message_data  # type: ignore
        )

        response_obj: Optional[OpenAIMessage] = None
        if getattr(thread_message, "status", None) is None:
            thread_message.status = "completed"
            response_obj = OpenAIMessage(**thread_message.dict())
        else:
            response_obj = OpenAIMessage(**thread_message.dict())
        return response_obj

    async def async_get_messages(
        self,
        thread_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI] = None,
        litellm_params: Optional[dict] = None,
    ) -> AsyncCursorPage[OpenAIMessage]:
        openai_client = self.async_get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = await openai_client.beta.threads.messages.list(thread_id=thread_id)

        return response

    # fmt: off

    @overload
    def get_messages(
        self,
        thread_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        aget_messages: Literal[True],
        litellm_params: Optional[dict] = None,
    ) -> Coroutine[None, None, AsyncCursorPage[OpenAIMessage]]:
        ...

    @overload
    def get_messages(
        self,
        thread_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AzureOpenAI],
        aget_messages: Optional[Literal[False]],
        litellm_params: Optional[dict] = None,
    ) -> SyncCursorPage[OpenAIMessage]:
        ...

    # fmt: on

    def get_messages(
        self,
        thread_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client=None,
        aget_messages=None,
        litellm_params: Optional[dict] = None,
    ):
        if aget_messages is not None and aget_messages is True:
            return self.async_get_messages(
                thread_id=thread_id,
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
                litellm_params=litellm_params,
            )
        openai_client = self.get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = openai_client.beta.threads.messages.list(thread_id=thread_id)

        return response

    ### THREADS ###

    async def async_create_thread(
        self,
        metadata: Optional[dict],
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        messages: Optional[Iterable[OpenAICreateThreadParamsMessage]],
        litellm_params: Optional[dict] = None,
    ) -> Thread:
        openai_client = self.async_get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        data = {}
        if messages is not None:
            data["messages"] = messages  # type: ignore
        if metadata is not None:
            data["metadata"] = metadata  # type: ignore

        message_thread = await openai_client.beta.threads.create(**data)  # type: ignore

        return Thread(**message_thread.dict())

    # fmt: off

    @overload
    def create_thread(
        self,
        metadata: Optional[dict],
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        messages: Optional[Iterable[OpenAICreateThreadParamsMessage]],
        client: Optional[AsyncAzureOpenAI],
        acreate_thread: Literal[True],
        litellm_params: Optional[dict] = None,
    ) -> Coroutine[None, None, Thread]:
        ...

    @overload
    def create_thread(
        self,
        metadata: Optional[dict],
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        messages: Optional[Iterable[OpenAICreateThreadParamsMessage]],
        client: Optional[AzureOpenAI],
        acreate_thread: Optional[Literal[False]],
        litellm_params: Optional[dict] = None,
    ) -> Thread:
        ...

    # fmt: on

    def create_thread(
        self,
        metadata: Optional[dict],
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        messages: Optional[Iterable[OpenAICreateThreadParamsMessage]],
        client=None,
        acreate_thread=None,
        litellm_params: Optional[dict] = None,
    ):
        """
        Here's an example:
        ```
        from litellm.llms.openai.openai import OpenAIAssistantsAPI, MessageData

        # create thread
        message: MessageData = {"role": "user", "content": "Hey, how's it going?"}
        openai_api.create_thread(messages=[message])
        ```
        """
        if acreate_thread is not None and acreate_thread is True:
            return self.async_create_thread(
                metadata=metadata,
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
                messages=messages,
                litellm_params=litellm_params,
            )
        azure_openai_client = self.get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        data = {}
        if messages is not None:
            data["messages"] = messages  # type: ignore
        if metadata is not None:
            data["metadata"] = metadata  # type: ignore

        message_thread = azure_openai_client.beta.threads.create(**data)  # type: ignore

        return Thread(**message_thread.dict())

    async def async_get_thread(
        self,
        thread_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        litellm_params: Optional[dict] = None,
    ) -> Thread:
        openai_client = self.async_get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = await openai_client.beta.threads.retrieve(thread_id=thread_id)

        return Thread(**response.dict())

    # fmt: off

    @overload
    def get_thread(
        self,
        thread_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        aget_thread: Literal[True],
        litellm_params: Optional[dict] = None,
    ) -> Coroutine[None, None, Thread]:
        ...

    @overload
    def get_thread(
        self,
        thread_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AzureOpenAI],
        aget_thread: Optional[Literal[False]],
        litellm_params: Optional[dict] = None,
    ) -> Thread:
        ...

    # fmt: on

    def get_thread(
        self,
        thread_id: str,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client=None,
        aget_thread=None,
        litellm_params: Optional[dict] = None,
    ):
        if aget_thread is not None and aget_thread is True:
            return self.async_get_thread(
                thread_id=thread_id,
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
                litellm_params=litellm_params,
            )
        openai_client = self.get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = openai_client.beta.threads.retrieve(thread_id=thread_id)

        return Thread(**response.dict())

    # def delete_thread(self):
    #     pass

    ### RUNS ###

    async def arun_thread(
        self,
        thread_id: str,
        assistant_id: str,
        additional_instructions: Optional[str],
        instructions: Optional[str],
        metadata: Optional[Dict],
        model: Optional[str],
        stream: Optional[bool],
        tools: Optional[Iterable[AssistantToolParam]],
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        litellm_params: Optional[dict] = None,
    ) -> Run:
        openai_client = self.async_get_azure_client(
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            max_retries=max_retries,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            client=client,
            litellm_params=litellm_params,
        )

        response = await openai_client.beta.threads.runs.create_and_poll(  # type: ignore
            thread_id=thread_id,
            assistant_id=assistant_id,
            additional_instructions=additional_instructions,
            instructions=instructions,
            metadata=metadata,  # type: ignore
            model=model,
            tools=tools,
        )

        return response

    def async_run_thread_stream(
        self,
        client: AsyncAzureOpenAI,
        thread_id: str,
        assistant_id: str,
        additional_instructions: Optional[str],
        instructions: Optional[str],
        metadata: Optional[Dict],
        model: Optional[str],
        tools: Optional[Iterable[AssistantToolParam]],
        event_handler: Optional[AssistantEventHandler],
        litellm_params: Optional[dict] = None,
    ) -> AsyncAssistantStreamManager[AsyncAssistantEventHandler]:
        data: Dict[str, Any] = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "additional_instructions": additional_instructions,
            "instructions": instructions,
            "metadata": metadata,
            "model": model,
            "tools": tools,
        }
        if event_handler is not None:
            data["event_handler"] = event_handler
        return client.beta.threads.runs.stream(**data)  # type: ignore

    def run_thread_stream(
        self,
        client: AzureOpenAI,
        thread_id: str,
        assistant_id: str,
        additional_instructions: Optional[str],
        instructions: Optional[str],
        metadata: Optional[Dict],
        model: Optional[str],
        tools: Optional[Iterable[AssistantToolParam]],
        event_handler: Optional[AssistantEventHandler],
        litellm_params: Optional[dict] = None,
    ) -> AssistantStreamManager[AssistantEventHandler]:
        data: Dict[str, Any] = {
            "thread_id": thread_id,
            "assistant_id": assistant_id,
            "additional_instructions": additional_instructions,
            "instructions": instructions,
            "metadata": metadata,
            "model": model,
            "tools": tools,
        }
        if event_handler is not None:
            data["event_handler"] = event_handler
        return client.beta.threads.runs.stream(**data)  # type: ignore

    # fmt: off

    @overload
    def run_thread(
        self,
        thread_id: str,
        assistant_id: str,
        additional_instructions: Optional[str],
        instructions: Optional[str],
        metadata: Optional[Dict],
        model: Optional[str],
        stream: Optional[bool],
        tools: Optional[Iterable[AssistantToolParam]],
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        arun_thread: Literal[True],
    ) -> Coroutine[None, None, Run]:
        ...

    @overload
    def run_thread(
        self,
        thread_id: str,
        assistant_id: str,
        additional_instructions: Optional[str],
        instructions: Optional[str],
        metadata: Optional[Dict],
        model: Optional[str],
        stream: Optional[bool],
        tools: Optional[Iterable[AssistantToolParam]],
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AzureOpenAI],
        arun_thread: Optional[Literal[False]],
    ) -> Run:
        ...

    # fmt: on

    def run_thread(
        self,
        thread_id: str,
        assistant_id: str,
        additional_instructions: Optional[str],
        instructions: Optional[str],
        metadata: Optional[Dict],
        model: Optional[str],
        stream: Optional[bool],
        tools: Optional[Iterable[AssistantToolParam]],
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client=None,
        arun_thread=None,
        event_handler: Optional[AssistantEventHandler] = None,
        litellm_params: Optional[dict] = None,
    ):
        if arun_thread is not None and arun_thread is True:
            if stream is not None and stream is True:
                azure_client = self.async_get_azure_client(
                    api_key=api_key,
                    api_base=api_base,
                    api_version=api_version,
                    azure_ad_token=azure_ad_token,
                    timeout=timeout,
                    max_retries=max_retries,
                    client=client,
                    litellm_params=litellm_params,
                )
                return self.async_run_thread_stream(
                    client=azure_client,
                    thread_id=thread_id,
                    assistant_id=assistant_id,
                    additional_instructions=additional_instructions,
                    instructions=instructions,
                    metadata=metadata,
                    model=model,
                    tools=tools,
                    event_handler=event_handler,
                    litellm_params=litellm_params,
                )
            return self.arun_thread(
                thread_id=thread_id,
                assistant_id=assistant_id,
                additional_instructions=additional_instructions,
                instructions=instructions,
                metadata=metadata,  # type: ignore
                model=model,
                stream=stream,
                tools=tools,
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
                litellm_params=litellm_params,
            )
        openai_client = self.get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        if stream is not None and stream is True:
            return self.run_thread_stream(
                client=openai_client,
                thread_id=thread_id,
                assistant_id=assistant_id,
                additional_instructions=additional_instructions,
                instructions=instructions,
                metadata=metadata,
                model=model,
                tools=tools,
                event_handler=event_handler,
                litellm_params=litellm_params,
            )

        response = openai_client.beta.threads.runs.create_and_poll(  # type: ignore
            thread_id=thread_id,
            assistant_id=assistant_id,
            additional_instructions=additional_instructions,
            instructions=instructions,
            metadata=metadata,  # type: ignore
            model=model,
            tools=tools,
        )

        return response

    # Create Assistant
    async def async_create_assistants(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        create_assistant_data: dict,
        litellm_params: Optional[dict] = None,
    ) -> Assistant:
        azure_openai_client = self.async_get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = await azure_openai_client.beta.assistants.create(
            **create_assistant_data
        )
        return response

    def create_assistants(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        create_assistant_data: dict,
        client=None,
        async_create_assistants=None,
        litellm_params: Optional[dict] = None,
    ):
        if async_create_assistants is not None and async_create_assistants is True:
            return self.async_create_assistants(
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
                create_assistant_data=create_assistant_data,
                litellm_params=litellm_params,
            )
        azure_openai_client = self.get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = azure_openai_client.beta.assistants.create(**create_assistant_data)
        return response

    # Delete Assistant
    async def async_delete_assistant(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        client: Optional[AsyncAzureOpenAI],
        assistant_id: str,
        litellm_params: Optional[dict] = None,
    ):
        azure_openai_client = self.async_get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = await azure_openai_client.beta.assistants.delete(
            assistant_id=assistant_id
        )
        return response

    def delete_assistant(
        self,
        api_key: Optional[str],
        api_base: Optional[str],
        api_version: Optional[str],
        azure_ad_token: Optional[str],
        timeout: Union[float, httpx.Timeout],
        max_retries: Optional[int],
        assistant_id: str,
        async_delete_assistants: Optional[bool] = None,
        client=None,
        litellm_params: Optional[dict] = None,
    ):
        if async_delete_assistants is not None and async_delete_assistants is True:
            return self.async_delete_assistant(
                api_key=api_key,
                api_base=api_base,
                api_version=api_version,
                azure_ad_token=azure_ad_token,
                timeout=timeout,
                max_retries=max_retries,
                client=client,
                assistant_id=assistant_id,
                litellm_params=litellm_params,
            )
        azure_openai_client = self.get_azure_client(
            api_key=api_key,
            api_base=api_base,
            api_version=api_version,
            azure_ad_token=azure_ad_token,
            timeout=timeout,
            max_retries=max_retries,
            client=client,
            litellm_params=litellm_params,
        )

        response = azure_openai_client.beta.assistants.delete(assistant_id=assistant_id)
        return response

# === NexusCore/src\__init__.py ===

# === NexusCore/exported_projects\app_20250703_223016\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_m73owrzi\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_xb_l70t8\app\routes\__init__.py ===

# === NexusCore/exported_projects\project_export_y7xxp1v8\app\routes\__init__.py ===

# === NexusCore/healing_sandbox\app\__init__.py ===

# === NexusCore/healing_sandbox\src\__init__.py ===

# === NexusCore/healing_sandbox\src\agents\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\win32comext\mapi\mapitags.py ===
MV_FLAG = 4096  # Multi-value flag

PT_UNSPECIFIED = 0
PT_NULL = 1
PT_I2 = 2
PT_LONG = 3
PT_R4 = 4
PT_DOUBLE = 5
PT_CURRENCY = 6
PT_APPTIME = 7
PT_ERROR = 10
PT_BOOLEAN = 11
PT_OBJECT = 13
PT_I8 = 20
PT_STRING8 = 30
PT_UNICODE = 31
PT_SYSTIME = 64
PT_CLSID = 72
PT_BINARY = 258

PT_SHORT = PT_I2
PT_I4 = PT_LONG
PT_FLOAT = PT_R4
PT_R8 = PT_DOUBLE
PT_LONGLONG = PT_I8

PT_MV_I2 = MV_FLAG | PT_I2
PT_MV_LONG = MV_FLAG | PT_LONG
PT_MV_R4 = MV_FLAG | PT_R4
PT_MV_DOUBLE = MV_FLAG | PT_DOUBLE
PT_MV_CURRENCY = MV_FLAG | PT_CURRENCY
PT_MV_APPTIME = MV_FLAG | PT_APPTIME
PT_MV_SYSTIME = MV_FLAG | PT_SYSTIME
PT_MV_STRING8 = MV_FLAG | PT_STRING8
PT_MV_BINARY = MV_FLAG | PT_BINARY
PT_MV_UNICODE = MV_FLAG | PT_UNICODE
PT_MV_CLSID = MV_FLAG | PT_CLSID
PT_MV_I8 = MV_FLAG | PT_I8

PT_MV_SHORT = PT_MV_I2
PT_MV_I4 = PT_MV_LONG
PT_MV_FLOAT = PT_MV_R4
PT_MV_R8 = PT_MV_DOUBLE
PT_MV_LONGLONG = PT_MV_I8

PT_TSTRING = PT_UNICODE  # ???
PT_MV_TSTRING = MV_FLAG | PT_UNICODE


PROP_TYPE_MASK = 65535  # Mask for Property type


def PROP_TYPE(ulPropTag):
    return ulPropTag & PROP_TYPE_MASK


def PROP_ID(ulPropTag):
    return ulPropTag >> 16


def PROP_TAG(ulPropType, ulPropID):
    return (ulPropID << 16) | (ulPropType)


PROP_ID_NULL = 0
PROP_ID_INVALID = 65535
PR_NULL = PROP_TAG(PT_NULL, PROP_ID_NULL)


PR_ACKNOWLEDGEMENT_MODE = PROP_TAG(PT_LONG, 1)
PR_ALTERNATE_RECIPIENT_ALLOWED = PROP_TAG(PT_BOOLEAN, 2)
PR_AUTHORIZING_USERS = PROP_TAG(PT_BINARY, 3)
PR_AUTO_FORWARD_COMMENT = PROP_TAG(PT_TSTRING, 4)
PR_AUTO_FORWARD_COMMENT_W = PROP_TAG(PT_UNICODE, 4)
PR_AUTO_FORWARD_COMMENT_A = PROP_TAG(PT_STRING8, 4)
PR_AUTO_FORWARDED = PROP_TAG(PT_BOOLEAN, 5)
PR_CONTENT_CONFIDENTIALITY_ALGORITHM_ID = PROP_TAG(PT_BINARY, 6)
PR_CONTENT_CORRELATOR = PROP_TAG(PT_BINARY, 7)
PR_CONTENT_IDENTIFIER = PROP_TAG(PT_TSTRING, 8)
PR_CONTENT_IDENTIFIER_W = PROP_TAG(PT_UNICODE, 8)
PR_CONTENT_IDENTIFIER_A = PROP_TAG(PT_STRING8, 8)
PR_CONTENT_LENGTH = PROP_TAG(PT_LONG, 9)
PR_CONTENT_RETURN_REQUESTED = PROP_TAG(PT_BOOLEAN, 10)
PR_CONVERSATION_KEY = PROP_TAG(PT_BINARY, 11)
PR_CONVERSION_EITS = PROP_TAG(PT_BINARY, 12)
PR_CONVERSION_WITH_LOSS_PROHIBITED = PROP_TAG(PT_BOOLEAN, 13)
PR_CONVERTED_EITS = PROP_TAG(PT_BINARY, 14)
PR_DEFERRED_DELIVERY_TIME = PROP_TAG(PT_SYSTIME, 15)
PR_DELIVER_TIME = PROP_TAG(PT_SYSTIME, 16)
PR_DISCARD_REASON = PROP_TAG(PT_LONG, 17)
PR_DISCLOSURE_OF_RECIPIENTS = PROP_TAG(PT_BOOLEAN, 18)
PR_DL_EXPANSION_HISTORY = PROP_TAG(PT_BINARY, 19)
PR_DL_EXPANSION_PROHIBITED = PROP_TAG(PT_BOOLEAN, 20)
PR_EXPIRY_TIME = PROP_TAG(PT_SYSTIME, 21)
PR_IMPLICIT_CONVERSION_PROHIBITED = PROP_TAG(PT_BOOLEAN, 22)
PR_IMPORTANCE = PROP_TAG(PT_LONG, 23)
PR_IPM_ID = PROP_TAG(PT_BINARY, 24)
PR_LATEST_DELIVERY_TIME = PROP_TAG(PT_SYSTIME, 25)
PR_MESSAGE_CLASS = PROP_TAG(PT_TSTRING, 26)
PR_MESSAGE_CLASS_W = PROP_TAG(PT_UNICODE, 26)
PR_MESSAGE_CLASS_A = PROP_TAG(PT_STRING8, 26)
PR_MESSAGE_DELIVERY_ID = PROP_TAG(PT_BINARY, 27)
PR_MESSAGE_SECURITY_LABEL = PROP_TAG(PT_BINARY, 30)
PR_OBSOLETED_IPMS = PROP_TAG(PT_BINARY, 31)
PR_ORIGINALLY_INTENDED_RECIPIENT_NAME = PROP_TAG(PT_BINARY, 32)
PR_ORIGINAL_EITS = PROP_TAG(PT_BINARY, 33)
PR_ORIGINATOR_CERTIFICATE = PROP_TAG(PT_BINARY, 34)
PR_ORIGINATOR_DELIVERY_REPORT_REQUESTED = PROP_TAG(PT_BOOLEAN, 35)
PR_ORIGINATOR_RETURN_ADDRESS = PROP_TAG(PT_BINARY, 36)
PR_PARENT_KEY = PROP_TAG(PT_BINARY, 37)
PR_PRIORITY = PROP_TAG(PT_LONG, 38)
PR_ORIGIN_CHECK = PROP_TAG(PT_BINARY, 39)
PR_PROOF_OF_SUBMISSION_REQUESTED = PROP_TAG(PT_BOOLEAN, 40)
PR_READ_RECEIPT_REQUESTED = PROP_TAG(PT_BOOLEAN, 41)
PR_RECEIPT_TIME = PROP_TAG(PT_SYSTIME, 42)
PR_RECIPIENT_REASSIGNMENT_PROHIBITED = PROP_TAG(PT_BOOLEAN, 43)
PR_REDIRECTION_HISTORY = PROP_TAG(PT_BINARY, 44)
PR_RELATED_IPMS = PROP_TAG(PT_BINARY, 45)
PR_ORIGINAL_SENSITIVITY = PROP_TAG(PT_LONG, 46)
PR_LANGUAGES = PROP_TAG(PT_TSTRING, 47)
PR_LANGUAGES_W = PROP_TAG(PT_UNICODE, 47)
PR_LANGUAGES_A = PROP_TAG(PT_STRING8, 47)
PR_REPLY_TIME = PROP_TAG(PT_SYSTIME, 48)
PR_REPORT_TAG = PROP_TAG(PT_BINARY, 49)
PR_REPORT_TIME = PROP_TAG(PT_SYSTIME, 50)
PR_RETURNED_IPM = PROP_TAG(PT_BOOLEAN, 51)
PR_SECURITY = PROP_TAG(PT_LONG, 52)
PR_INCOMPLETE_COPY = PROP_TAG(PT_BOOLEAN, 53)
PR_SENSITIVITY = PROP_TAG(PT_LONG, 54)
PR_SUBJECT = PROP_TAG(PT_TSTRING, 55)
PR_SUBJECT_W = PROP_TAG(PT_UNICODE, 55)
PR_SUBJECT_A = PROP_TAG(PT_STRING8, 55)
PR_SUBJECT_IPM = PROP_TAG(PT_BINARY, 56)
PR_CLIENT_SUBMIT_TIME = PROP_TAG(PT_SYSTIME, 57)
PR_REPORT_NAME = PROP_TAG(PT_TSTRING, 58)
PR_REPORT_NAME_W = PROP_TAG(PT_UNICODE, 58)
PR_REPORT_NAME_A = PROP_TAG(PT_STRING8, 58)
PR_SENT_REPRESENTING_SEARCH_KEY = PROP_TAG(PT_BINARY, 59)
PR_X400_CONTENT_TYPE = PROP_TAG(PT_BINARY, 60)
PR_SUBJECT_PREFIX = PROP_TAG(PT_TSTRING, 61)
PR_SUBJECT_PREFIX_W = PROP_TAG(PT_UNICODE, 61)
PR_SUBJECT_PREFIX_A = PROP_TAG(PT_STRING8, 61)
PR_NON_RECEIPT_REASON = PROP_TAG(PT_LONG, 62)
PR_RECEIVED_BY_ENTRYID = PROP_TAG(PT_BINARY, 63)
PR_RECEIVED_BY_NAME = PROP_TAG(PT_TSTRING, 64)
PR_RECEIVED_BY_NAME_W = PROP_TAG(PT_UNICODE, 64)
PR_RECEIVED_BY_NAME_A = PROP_TAG(PT_STRING8, 64)
PR_SENT_REPRESENTING_ENTRYID = PROP_TAG(PT_BINARY, 65)
PR_SENT_REPRESENTING_NAME = PROP_TAG(PT_TSTRING, 66)
PR_SENT_REPRESENTING_NAME_W = PROP_TAG(PT_UNICODE, 66)
PR_SENT_REPRESENTING_NAME_A = PROP_TAG(PT_STRING8, 66)
PR_RCVD_REPRESENTING_ENTRYID = PROP_TAG(PT_BINARY, 67)
PR_RCVD_REPRESENTING_NAME = PROP_TAG(PT_TSTRING, 68)
PR_RCVD_REPRESENTING_NAME_W = PROP_TAG(PT_UNICODE, 68)
PR_RCVD_REPRESENTING_NAME_A = PROP_TAG(PT_STRING8, 68)
PR_REPORT_ENTRYID = PROP_TAG(PT_BINARY, 69)
PR_READ_RECEIPT_ENTRYID = PROP_TAG(PT_BINARY, 70)
PR_MESSAGE_SUBMISSION_ID = PROP_TAG(PT_BINARY, 71)
PR_PROVIDER_SUBMIT_TIME = PROP_TAG(PT_SYSTIME, 72)
PR_ORIGINAL_SUBJECT = PROP_TAG(PT_TSTRING, 73)
PR_ORIGINAL_SUBJECT_W = PROP_TAG(PT_UNICODE, 73)
PR_ORIGINAL_SUBJECT_A = PROP_TAG(PT_STRING8, 73)
PR_DISC_VAL = PROP_TAG(PT_BOOLEAN, 74)
PR_ORIG_MESSAGE_CLASS = PROP_TAG(PT_TSTRING, 75)
PR_ORIG_MESSAGE_CLASS_W = PROP_TAG(PT_UNICODE, 75)
PR_ORIG_MESSAGE_CLASS_A = PROP_TAG(PT_STRING8, 75)
PR_ORIGINAL_AUTHOR_ENTRYID = PROP_TAG(PT_BINARY, 76)
PR_ORIGINAL_AUTHOR_NAME = PROP_TAG(PT_TSTRING, 77)
PR_ORIGINAL_AUTHOR_NAME_W = PROP_TAG(PT_UNICODE, 77)
PR_ORIGINAL_AUTHOR_NAME_A = PROP_TAG(PT_STRING8, 77)
PR_ORIGINAL_SUBMIT_TIME = PROP_TAG(PT_SYSTIME, 78)
PR_REPLY_RECIPIENT_ENTRIES = PROP_TAG(PT_BINARY, 79)
PR_REPLY_RECIPIENT_NAMES = PROP_TAG(PT_TSTRING, 80)
PR_REPLY_RECIPIENT_NAMES_W = PROP_TAG(PT_UNICODE, 80)
PR_REPLY_RECIPIENT_NAMES_A = PROP_TAG(PT_STRING8, 80)
PR_RECEIVED_BY_SEARCH_KEY = PROP_TAG(PT_BINARY, 81)
PR_RCVD_REPRESENTING_SEARCH_KEY = PROP_TAG(PT_BINARY, 82)
PR_READ_RECEIPT_SEARCH_KEY = PROP_TAG(PT_BINARY, 83)
PR_REPORT_SEARCH_KEY = PROP_TAG(PT_BINARY, 84)
PR_ORIGINAL_DELIVERY_TIME = PROP_TAG(PT_SYSTIME, 85)
PR_ORIGINAL_AUTHOR_SEARCH_KEY = PROP_TAG(PT_BINARY, 86)
PR_MESSAGE_TO_ME = PROP_TAG(PT_BOOLEAN, 87)
PR_MESSAGE_CC_ME = PROP_TAG(PT_BOOLEAN, 88)
PR_MESSAGE_RECIP_ME = PROP_TAG(PT_BOOLEAN, 89)
PR_ORIGINAL_SENDER_NAME = PROP_TAG(PT_TSTRING, 90)
PR_ORIGINAL_SENDER_NAME_W = PROP_TAG(PT_UNICODE, 90)
PR_ORIGINAL_SENDER_NAME_A = PROP_TAG(PT_STRING8, 90)
PR_ORIGINAL_SENDER_ENTRYID = PROP_TAG(PT_BINARY, 91)
PR_ORIGINAL_SENDER_SEARCH_KEY = PROP_TAG(PT_BINARY, 92)
PR_ORIGINAL_SENT_REPRESENTING_NAME = PROP_TAG(PT_TSTRING, 93)
PR_ORIGINAL_SENT_REPRESENTING_NAME_W = PROP_TAG(PT_UNICODE, 93)
PR_ORIGINAL_SENT_REPRESENTING_NAME_A = PROP_TAG(PT_STRING8, 93)
PR_ORIGINAL_SENT_REPRESENTING_ENTRYID = PROP_TAG(PT_BINARY, 94)
PR_ORIGINAL_SENT_REPRESENTING_SEARCH_KEY = PROP_TAG(PT_BINARY, 95)
PR_START_DATE = PROP_TAG(PT_SYSTIME, 96)
PR_END_DATE = PROP_TAG(PT_SYSTIME, 97)
PR_OWNER_APPT_ID = PROP_TAG(PT_LONG, 98)
PR_RESPONSE_REQUESTED = PROP_TAG(PT_BOOLEAN, 99)
PR_SENT_REPRESENTING_ADDRTYPE = PROP_TAG(PT_TSTRING, 100)
PR_SENT_REPRESENTING_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 100)
PR_SENT_REPRESENTING_ADDRTYPE_A = PROP_TAG(PT_STRING8, 100)
PR_SENT_REPRESENTING_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 101)
PR_SENT_REPRESENTING_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 101)
PR_SENT_REPRESENTING_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 101)
PR_ORIGINAL_SENDER_ADDRTYPE = PROP_TAG(PT_TSTRING, 102)
PR_ORIGINAL_SENDER_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 102)
PR_ORIGINAL_SENDER_ADDRTYPE_A = PROP_TAG(PT_STRING8, 102)
PR_ORIGINAL_SENDER_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 103)
PR_ORIGINAL_SENDER_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 103)
PR_ORIGINAL_SENDER_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 103)
PR_ORIGINAL_SENT_REPRESENTING_ADDRTYPE = PROP_TAG(PT_TSTRING, 104)
PR_ORIGINAL_SENT_REPRESENTING_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 104)
PR_ORIGINAL_SENT_REPRESENTING_ADDRTYPE_A = PROP_TAG(PT_STRING8, 104)
PR_ORIGINAL_SENT_REPRESENTING_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 105)
PR_ORIGINAL_SENT_REPRESENTING_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 105)
PR_ORIGINAL_SENT_REPRESENTING_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 105)
PR_CONVERSATION_TOPIC = PROP_TAG(PT_TSTRING, 112)
PR_CONVERSATION_TOPIC_W = PROP_TAG(PT_UNICODE, 112)
PR_CONVERSATION_TOPIC_A = PROP_TAG(PT_STRING8, 112)
PR_CONVERSATION_INDEX = PROP_TAG(PT_BINARY, 113)
PR_ORIGINAL_DISPLAY_BCC = PROP_TAG(PT_TSTRING, 114)
PR_ORIGINAL_DISPLAY_BCC_W = PROP_TAG(PT_UNICODE, 114)
PR_ORIGINAL_DISPLAY_BCC_A = PROP_TAG(PT_STRING8, 114)
PR_ORIGINAL_DISPLAY_CC = PROP_TAG(PT_TSTRING, 115)
PR_ORIGINAL_DISPLAY_CC_W = PROP_TAG(PT_UNICODE, 115)
PR_ORIGINAL_DISPLAY_CC_A = PROP_TAG(PT_STRING8, 115)
PR_ORIGINAL_DISPLAY_TO = PROP_TAG(PT_TSTRING, 116)
PR_ORIGINAL_DISPLAY_TO_W = PROP_TAG(PT_UNICODE, 116)
PR_ORIGINAL_DISPLAY_TO_A = PROP_TAG(PT_STRING8, 116)
PR_RECEIVED_BY_ADDRTYPE = PROP_TAG(PT_TSTRING, 117)
PR_RECEIVED_BY_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 117)
PR_RECEIVED_BY_ADDRTYPE_A = PROP_TAG(PT_STRING8, 117)
PR_RECEIVED_BY_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 118)
PR_RECEIVED_BY_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 118)
PR_RECEIVED_BY_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 118)
PR_RCVD_REPRESENTING_ADDRTYPE = PROP_TAG(PT_TSTRING, 119)
PR_RCVD_REPRESENTING_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 119)
PR_RCVD_REPRESENTING_ADDRTYPE_A = PROP_TAG(PT_STRING8, 119)
PR_RCVD_REPRESENTING_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 120)
PR_RCVD_REPRESENTING_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 120)
PR_RCVD_REPRESENTING_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 120)
PR_ORIGINAL_AUTHOR_ADDRTYPE = PROP_TAG(PT_TSTRING, 121)
PR_ORIGINAL_AUTHOR_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 121)
PR_ORIGINAL_AUTHOR_ADDRTYPE_A = PROP_TAG(PT_STRING8, 121)
PR_ORIGINAL_AUTHOR_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 122)
PR_ORIGINAL_AUTHOR_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 122)
PR_ORIGINAL_AUTHOR_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 122)
PR_ORIGINALLY_INTENDED_RECIP_ADDRTYPE = PROP_TAG(PT_TSTRING, 123)
PR_ORIGINALLY_INTENDED_RECIP_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 123)
PR_ORIGINALLY_INTENDED_RECIP_ADDRTYPE_A = PROP_TAG(PT_STRING8, 123)
PR_ORIGINALLY_INTENDED_RECIP_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 124)
PR_ORIGINALLY_INTENDED_RECIP_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 124)
PR_ORIGINALLY_INTENDED_RECIP_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 124)
PR_TRANSPORT_MESSAGE_HEADERS = PROP_TAG(PT_TSTRING, 125)
PR_TRANSPORT_MESSAGE_HEADERS_W = PROP_TAG(PT_UNICODE, 125)
PR_TRANSPORT_MESSAGE_HEADERS_A = PROP_TAG(PT_STRING8, 125)
PR_DELEGATION = PROP_TAG(PT_BINARY, 126)
PR_TNEF_CORRELATION_KEY = PROP_TAG(PT_BINARY, 127)
PR_BODY = PROP_TAG(PT_TSTRING, 4096)
PR_BODY_W = PROP_TAG(PT_UNICODE, 4096)
PR_BODY_A = PROP_TAG(PT_STRING8, 4096)
PR_BODY_HTML = PROP_TAG(PT_TSTRING, 4115)
PR_BODY_HTML_W = PROP_TAG(PT_UNICODE, 4115)
PR_BODY_HTML_A = PROP_TAG(PT_STRING8, 4115)
PR_REPORT_TEXT = PROP_TAG(PT_TSTRING, 4097)
PR_REPORT_TEXT_W = PROP_TAG(PT_UNICODE, 4097)
PR_REPORT_TEXT_A = PROP_TAG(PT_STRING8, 4097)
PR_ORIGINATOR_AND_DL_EXPANSION_HISTORY = PROP_TAG(PT_BINARY, 4098)
PR_REPORTING_DL_NAME = PROP_TAG(PT_BINARY, 4099)
PR_REPORTING_MTA_CERTIFICATE = PROP_TAG(PT_BINARY, 4100)
PR_RTF_SYNC_BODY_CRC = PROP_TAG(PT_LONG, 4102)
PR_RTF_SYNC_BODY_COUNT = PROP_TAG(PT_LONG, 4103)
PR_RTF_SYNC_BODY_TAG = PROP_TAG(PT_TSTRING, 4104)
PR_RTF_SYNC_BODY_TAG_W = PROP_TAG(PT_UNICODE, 4104)
PR_RTF_SYNC_BODY_TAG_A = PROP_TAG(PT_STRING8, 4104)
PR_RTF_COMPRESSED = PROP_TAG(PT_BINARY, 4105)
PR_RTF_SYNC_PREFIX_COUNT = PROP_TAG(PT_LONG, 4112)
PR_RTF_SYNC_TRAILING_COUNT = PROP_TAG(PT_LONG, 4113)
PR_ORIGINALLY_INTENDED_RECIP_ENTRYID = PROP_TAG(PT_BINARY, 4114)
PR_CONTENT_INTEGRITY_CHECK = PROP_TAG(PT_BINARY, 3072)
PR_EXPLICIT_CONVERSION = PROP_TAG(PT_LONG, 3073)
PR_IPM_RETURN_REQUESTED = PROP_TAG(PT_BOOLEAN, 3074)
PR_MESSAGE_TOKEN = PROP_TAG(PT_BINARY, 3075)
PR_NDR_REASON_CODE = PROP_TAG(PT_LONG, 3076)
PR_NDR_DIAG_CODE = PROP_TAG(PT_LONG, 3077)
PR_NON_RECEIPT_NOTIFICATION_REQUESTED = PROP_TAG(PT_BOOLEAN, 3078)
PR_DELIVERY_POINT = PROP_TAG(PT_LONG, 3079)
PR_ORIGINATOR_NON_DELIVERY_REPORT_REQUESTED = PROP_TAG(PT_BOOLEAN, 3080)
PR_ORIGINATOR_REQUESTED_ALTERNATE_RECIPIENT = PROP_TAG(PT_BINARY, 3081)
PR_PHYSICAL_DELIVERY_BUREAU_FAX_DELIVERY = PROP_TAG(PT_BOOLEAN, 3082)
PR_PHYSICAL_DELIVERY_MODE = PROP_TAG(PT_LONG, 3083)
PR_PHYSICAL_DELIVERY_REPORT_REQUEST = PROP_TAG(PT_LONG, 3084)
PR_PHYSICAL_FORWARDING_ADDRESS = PROP_TAG(PT_BINARY, 3085)
PR_PHYSICAL_FORWARDING_ADDRESS_REQUESTED = PROP_TAG(PT_BOOLEAN, 3086)
PR_PHYSICAL_FORWARDING_PROHIBITED = PROP_TAG(PT_BOOLEAN, 3087)
PR_PHYSICAL_RENDITION_ATTRIBUTES = PROP_TAG(PT_BINARY, 3088)
PR_PROOF_OF_DELIVERY = PROP_TAG(PT_BINARY, 3089)
PR_PROOF_OF_DELIVERY_REQUESTED = PROP_TAG(PT_BOOLEAN, 3090)
PR_RECIPIENT_CERTIFICATE = PROP_TAG(PT_BINARY, 3091)
PR_RECIPIENT_NUMBER_FOR_ADVICE = PROP_TAG(PT_TSTRING, 3092)
PR_RECIPIENT_NUMBER_FOR_ADVICE_W = PROP_TAG(PT_UNICODE, 3092)
PR_RECIPIENT_NUMBER_FOR_ADVICE_A = PROP_TAG(PT_STRING8, 3092)
PR_RECIPIENT_TYPE = PROP_TAG(PT_LONG, 3093)
PR_REGISTERED_MAIL_TYPE = PROP_TAG(PT_LONG, 3094)
PR_REPLY_REQUESTED = PROP_TAG(PT_BOOLEAN, 3095)
PR_REQUESTED_DELIVERY_METHOD = PROP_TAG(PT_LONG, 3096)
PR_SENDER_ENTRYID = PROP_TAG(PT_BINARY, 3097)
PR_SENDER_NAME = PROP_TAG(PT_TSTRING, 3098)
PR_SENDER_NAME_W = PROP_TAG(PT_UNICODE, 3098)
PR_SENDER_NAME_A = PROP_TAG(PT_STRING8, 3098)
PR_SUPPLEMENTARY_INFO = PROP_TAG(PT_TSTRING, 3099)
PR_SUPPLEMENTARY_INFO_W = PROP_TAG(PT_UNICODE, 3099)
PR_SUPPLEMENTARY_INFO_A = PROP_TAG(PT_STRING8, 3099)
PR_TYPE_OF_MTS_USER = PROP_TAG(PT_LONG, 3100)
PR_SENDER_SEARCH_KEY = PROP_TAG(PT_BINARY, 3101)
PR_SENDER_ADDRTYPE = PROP_TAG(PT_TSTRING, 3102)
PR_SENDER_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 3102)
PR_SENDER_ADDRTYPE_A = PROP_TAG(PT_STRING8, 3102)
PR_SENDER_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 3103)
PR_SENDER_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 3103)
PR_SENDER_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 3103)
PR_CURRENT_VERSION = PROP_TAG(PT_I8, 3584)
PR_DELETE_AFTER_SUBMIT = PROP_TAG(PT_BOOLEAN, 3585)
PR_DISPLAY_BCC = PROP_TAG(PT_TSTRING, 3586)
PR_DISPLAY_BCC_W = PROP_TAG(PT_UNICODE, 3586)
PR_DISPLAY_BCC_A = PROP_TAG(PT_STRING8, 3586)
PR_DISPLAY_CC = PROP_TAG(PT_TSTRING, 3587)
PR_DISPLAY_CC_W = PROP_TAG(PT_UNICODE, 3587)
PR_DISPLAY_CC_A = PROP_TAG(PT_STRING8, 3587)
PR_DISPLAY_TO = PROP_TAG(PT_TSTRING, 3588)
PR_DISPLAY_TO_W = PROP_TAG(PT_UNICODE, 3588)
PR_DISPLAY_TO_A = PROP_TAG(PT_STRING8, 3588)
PR_PARENT_DISPLAY = PROP_TAG(PT_TSTRING, 3589)
PR_PARENT_DISPLAY_W = PROP_TAG(PT_UNICODE, 3589)
PR_PARENT_DISPLAY_A = PROP_TAG(PT_STRING8, 3589)
PR_MESSAGE_DELIVERY_TIME = PROP_TAG(PT_SYSTIME, 3590)
PR_MESSAGE_FLAGS = PROP_TAG(PT_LONG, 3591)
PR_MESSAGE_SIZE = PROP_TAG(PT_LONG, 3592)
PR_PARENT_ENTRYID = PROP_TAG(PT_BINARY, 3593)
PR_SENTMAIL_ENTRYID = PROP_TAG(PT_BINARY, 3594)
PR_CORRELATE = PROP_TAG(PT_BOOLEAN, 3596)
PR_CORRELATE_MTSID = PROP_TAG(PT_BINARY, 3597)
PR_DISCRETE_VALUES = PROP_TAG(PT_BOOLEAN, 3598)
PR_RESPONSIBILITY = PROP_TAG(PT_BOOLEAN, 3599)
PR_SPOOLER_STATUS = PROP_TAG(PT_LONG, 3600)
PR_TRANSPORT_STATUS = PROP_TAG(PT_LONG, 3601)
PR_MESSAGE_RECIPIENTS = PROP_TAG(PT_OBJECT, 3602)
PR_MESSAGE_ATTACHMENTS = PROP_TAG(PT_OBJECT, 3603)
PR_SUBMIT_FLAGS = PROP_TAG(PT_LONG, 3604)
PR_RECIPIENT_STATUS = PROP_TAG(PT_LONG, 3605)
PR_TRANSPORT_KEY = PROP_TAG(PT_LONG, 3606)
PR_MSG_STATUS = PROP_TAG(PT_LONG, 3607)
PR_MESSAGE_DOWNLOAD_TIME = PROP_TAG(PT_LONG, 3608)
PR_CREATION_VERSION = PROP_TAG(PT_I8, 3609)
PR_MODIFY_VERSION = PROP_TAG(PT_I8, 3610)
PR_HASATTACH = PROP_TAG(PT_BOOLEAN, 3611)
PR_BODY_CRC = PROP_TAG(PT_LONG, 3612)
PR_NORMALIZED_SUBJECT = PROP_TAG(PT_TSTRING, 3613)
PR_NORMALIZED_SUBJECT_W = PROP_TAG(PT_UNICODE, 3613)
PR_NORMALIZED_SUBJECT_A = PROP_TAG(PT_STRING8, 3613)
PR_RTF_IN_SYNC = PROP_TAG(PT_BOOLEAN, 3615)
PR_ATTACH_SIZE = PROP_TAG(PT_LONG, 3616)
PR_ATTACH_NUM = PROP_TAG(PT_LONG, 3617)
PR_PREPROCESS = PROP_TAG(PT_BOOLEAN, 3618)
PR_ORIGINATING_MTA_CERTIFICATE = PROP_TAG(PT_BINARY, 3621)
PR_PROOF_OF_SUBMISSION = PROP_TAG(PT_BINARY, 3622)
PR_ENTRYID = PROP_TAG(PT_BINARY, 4095)
PR_OBJECT_TYPE = PROP_TAG(PT_LONG, 4094)
PR_ICON = PROP_TAG(PT_BINARY, 4093)
PR_MINI_ICON = PROP_TAG(PT_BINARY, 4092)
PR_STORE_ENTRYID = PROP_TAG(PT_BINARY, 4091)
PR_STORE_RECORD_KEY = PROP_TAG(PT_BINARY, 4090)
PR_RECORD_KEY = PROP_TAG(PT_BINARY, 4089)
PR_MAPPING_SIGNATURE = PROP_TAG(PT_BINARY, 4088)
PR_ACCESS_LEVEL = PROP_TAG(PT_LONG, 4087)
PR_INSTANCE_KEY = PROP_TAG(PT_BINARY, 4086)
PR_ROW_TYPE = PROP_TAG(PT_LONG, 4085)
PR_ACCESS = PROP_TAG(PT_LONG, 4084)
PR_ROWID = PROP_TAG(PT_LONG, 12288)
PR_DISPLAY_NAME = PROP_TAG(PT_TSTRING, 12289)
PR_DISPLAY_NAME_W = PROP_TAG(PT_UNICODE, 12289)
PR_DISPLAY_NAME_A = PROP_TAG(PT_STRING8, 12289)
PR_ADDRTYPE = PROP_TAG(PT_TSTRING, 12290)
PR_ADDRTYPE_W = PROP_TAG(PT_UNICODE, 12290)
PR_ADDRTYPE_A = PROP_TAG(PT_STRING8, 12290)
PR_EMAIL_ADDRESS = PROP_TAG(PT_TSTRING, 12291)
PR_EMAIL_ADDRESS_W = PROP_TAG(PT_UNICODE, 12291)
PR_EMAIL_ADDRESS_A = PROP_TAG(PT_STRING8, 12291)
PR_COMMENT = PROP_TAG(PT_TSTRING, 12292)
PR_COMMENT_W = PROP_TAG(PT_UNICODE, 12292)
PR_COMMENT_A = PROP_TAG(PT_STRING8, 12292)
PR_DEPTH = PROP_TAG(PT_LONG, 12293)
PR_PROVIDER_DISPLAY = PROP_TAG(PT_TSTRING, 12294)
PR_PROVIDER_DISPLAY_W = PROP_TAG(PT_UNICODE, 12294)
PR_PROVIDER_DISPLAY_A = PROP_TAG(PT_STRING8, 12294)
PR_CREATION_TIME = PROP_TAG(PT_SYSTIME, 12295)
PR_LAST_MODIFICATION_TIME = PROP_TAG(PT_SYSTIME, 12296)
PR_RESOURCE_FLAGS = PROP_TAG(PT_LONG, 12297)
PR_PROVIDER_DLL_NAME = PROP_TAG(PT_TSTRING, 12298)
PR_PROVIDER_DLL_NAME_W = PROP_TAG(PT_UNICODE, 12298)
PR_PROVIDER_DLL_NAME_A = PROP_TAG(PT_STRING8, 12298)
PR_SEARCH_KEY = PROP_TAG(PT_BINARY, 12299)
PR_PROVIDER_UID = PROP_TAG(PT_BINARY, 12300)
PR_PROVIDER_ORDINAL = PROP_TAG(PT_LONG, 12301)
PR_FORM_VERSION = PROP_TAG(PT_TSTRING, 13057)
PR_FORM_VERSION_W = PROP_TAG(PT_UNICODE, 13057)
PR_FORM_VERSION_A = PROP_TAG(PT_STRING8, 13057)
PR_FORM_CLSID = PROP_TAG(PT_CLSID, 13058)
PR_FORM_CONTACT_NAME = PROP_TAG(PT_TSTRING, 13059)
PR_FORM_CONTACT_NAME_W = PROP_TAG(PT_UNICODE, 13059)
PR_FORM_CONTACT_NAME_A = PROP_TAG(PT_STRING8, 13059)
PR_FORM_CATEGORY = PROP_TAG(PT_TSTRING, 13060)
PR_FORM_CATEGORY_W = PROP_TAG(PT_UNICODE, 13060)
PR_FORM_CATEGORY_A = PROP_TAG(PT_STRING8, 13060)
PR_FORM_CATEGORY_SUB = PROP_TAG(PT_TSTRING, 13061)
PR_FORM_CATEGORY_SUB_W = PROP_TAG(PT_UNICODE, 13061)
PR_FORM_CATEGORY_SUB_A = PROP_TAG(PT_STRING8, 13061)
PR_FORM_HOST_MAP = PROP_TAG(PT_MV_LONG, 13062)
PR_FORM_HIDDEN = PROP_TAG(PT_BOOLEAN, 13063)
PR_FORM_DESIGNER_NAME = PROP_TAG(PT_TSTRING, 13064)
PR_FORM_DESIGNER_NAME_W = PROP_TAG(PT_UNICODE, 13064)
PR_FORM_DESIGNER_NAME_A = PROP_TAG(PT_STRING8, 13064)
PR_FORM_DESIGNER_GUID = PROP_TAG(PT_CLSID, 13065)
PR_FORM_MESSAGE_BEHAVIOR = PROP_TAG(PT_LONG, 13066)
PR_DEFAULT_STORE = PROP_TAG(PT_BOOLEAN, 13312)
PR_STORE_SUPPORT_MASK = PROP_TAG(PT_LONG, 13325)
PR_STORE_STATE = PROP_TAG(PT_LONG, 13326)
PR_IPM_SUBTREE_SEARCH_KEY = PROP_TAG(PT_BINARY, 13328)
PR_IPM_OUTBOX_SEARCH_KEY = PROP_TAG(PT_BINARY, 13329)
PR_IPM_WASTEBASKET_SEARCH_KEY = PROP_TAG(PT_BINARY, 13330)
PR_IPM_SENTMAIL_SEARCH_KEY = PROP_TAG(PT_BINARY, 13331)
PR_MDB_PROVIDER = PROP_TAG(PT_BINARY, 13332)
PR_RECEIVE_FOLDER_SETTINGS = PROP_TAG(PT_OBJECT, 13333)
PR_VALID_FOLDER_MASK = PROP_TAG(PT_LONG, 13791)
PR_IPM_SUBTREE_ENTRYID = PROP_TAG(PT_BINARY, 13792)
PR_IPM_OUTBOX_ENTRYID = PROP_TAG(PT_BINARY, 13794)
PR_IPM_WASTEBASKET_ENTRYID = PROP_TAG(PT_BINARY, 13795)
PR_IPM_SENTMAIL_ENTRYID = PROP_TAG(PT_BINARY, 13796)
PR_VIEWS_ENTRYID = PROP_TAG(PT_BINARY, 13797)
PR_COMMON_VIEWS_ENTRYID = PROP_TAG(PT_BINARY, 13798)
PR_FINDER_ENTRYID = PROP_TAG(PT_BINARY, 13799)
PR_CONTAINER_FLAGS = PROP_TAG(PT_LONG, 13824)
PR_FOLDER_TYPE = PROP_TAG(PT_LONG, 13825)
PR_CONTENT_COUNT = PROP_TAG(PT_LONG, 13826)
PR_CONTENT_UNREAD = PROP_TAG(PT_LONG, 13827)
PR_CREATE_TEMPLATES = PROP_TAG(PT_OBJECT, 13828)
PR_DETAILS_TABLE = PROP_TAG(PT_OBJECT, 13829)
PR_SEARCH = PROP_TAG(PT_OBJECT, 13831)
PR_SELECTABLE = PROP_TAG(PT_BOOLEAN, 13833)
PR_SUBFOLDERS = PROP_TAG(PT_BOOLEAN, 13834)
PR_STATUS = PROP_TAG(PT_LONG, 13835)
PR_ANR = PROP_TAG(PT_TSTRING, 13836)
PR_ANR_W = PROP_TAG(PT_UNICODE, 13836)
PR_ANR_A = PROP_TAG(PT_STRING8, 13836)
PR_CONTENTS_SORT_ORDER = PROP_TAG(PT_MV_LONG, 13837)
PR_CONTAINER_HIERARCHY = PROP_TAG(PT_OBJECT, 13838)
PR_CONTAINER_CONTENTS = PROP_TAG(PT_OBJECT, 13839)
PR_FOLDER_ASSOCIATED_CONTENTS = PROP_TAG(PT_OBJECT, 13840)
PR_DEF_CREATE_DL = PROP_TAG(PT_BINARY, 13841)
PR_DEF_CREATE_MAILUSER = PROP_TAG(PT_BINARY, 13842)
PR_CONTAINER_CLASS = PROP_TAG(PT_TSTRING, 13843)
PR_CONTAINER_CLASS_W = PROP_TAG(PT_UNICODE, 13843)
PR_CONTAINER_CLASS_A = PROP_TAG(PT_STRING8, 13843)
PR_CONTAINER_MODIFY_VERSION = PROP_TAG(PT_I8, 13844)
PR_AB_PROVIDER_ID = PROP_TAG(PT_BINARY, 13845)
PR_DEFAULT_VIEW_ENTRYID = PROP_TAG(PT_BINARY, 13846)
PR_ASSOC_CONTENT_COUNT = PROP_TAG(PT_LONG, 13847)
PR_ATTACHMENT_X400_PARAMETERS = PROP_TAG(PT_BINARY, 14080)
PR_ATTACH_DATA_OBJ = PROP_TAG(PT_OBJECT, 14081)
PR_ATTACH_DATA_BIN = PROP_TAG(PT_BINARY, 14081)
PR_ATTACH_ENCODING = PROP_TAG(PT_BINARY, 14082)
PR_ATTACH_EXTENSION = PROP_TAG(PT_TSTRING, 14083)
PR_ATTACH_EXTENSION_W = PROP_TAG(PT_UNICODE, 14083)
PR_ATTACH_EXTENSION_A = PROP_TAG(PT_STRING8, 14083)
PR_ATTACH_FILENAME = PROP_TAG(PT_TSTRING, 14084)
PR_ATTACH_FILENAME_W = PROP_TAG(PT_UNICODE, 14084)
PR_ATTACH_FILENAME_A = PROP_TAG(PT_STRING8, 14084)
PR_ATTACH_METHOD = PROP_TAG(PT_LONG, 14085)
PR_ATTACH_LONG_FILENAME = PROP_TAG(PT_TSTRING, 14087)
PR_ATTACH_LONG_FILENAME_W = PROP_TAG(PT_UNICODE, 14087)
PR_ATTACH_LONG_FILENAME_A = PROP_TAG(PT_STRING8, 14087)
PR_ATTACH_PATHNAME = PROP_TAG(PT_TSTRING, 14088)
PR_ATTACH_PATHNAME_W = PROP_TAG(PT_UNICODE, 14088)
PR_ATTACH_PATHNAME_A = PROP_TAG(PT_STRING8, 14088)
PR_ATTACH_RENDERING = PROP_TAG(PT_BINARY, 14089)
PR_ATTACH_TAG = PROP_TAG(PT_BINARY, 14090)
PR_RENDERING_POSITION = PROP_TAG(PT_LONG, 14091)
PR_ATTACH_TRANSPORT_NAME = PROP_TAG(PT_TSTRING, 14092)
PR_ATTACH_TRANSPORT_NAME_W = PROP_TAG(PT_UNICODE, 14092)
PR_ATTACH_TRANSPORT_NAME_A = PROP_TAG(PT_STRING8, 14092)
PR_ATTACH_LONG_PATHNAME = PROP_TAG(PT_TSTRING, 14093)
PR_ATTACH_LONG_PATHNAME_W = PROP_TAG(PT_UNICODE, 14093)
PR_ATTACH_LONG_PATHNAME_A = PROP_TAG(PT_STRING8, 14093)
PR_ATTACH_MIME_TAG = PROP_TAG(PT_TSTRING, 14094)
PR_ATTACH_MIME_TAG_W = PROP_TAG(PT_UNICODE, 14094)
PR_ATTACH_MIME_TAG_A = PROP_TAG(PT_STRING8, 14094)
PR_ATTACH_ADDITIONAL_INFO = PROP_TAG(PT_BINARY, 14095)
PR_DISPLAY_TYPE = PROP_TAG(PT_LONG, 14592)
PR_TEMPLATEID = PROP_TAG(PT_BINARY, 14594)
PR_PRIMARY_CAPABILITY = PROP_TAG(PT_BINARY, 14596)
PR_7BIT_DISPLAY_NAME = PROP_TAG(PT_STRING8, 14847)
PR_ACCOUNT = PROP_TAG(PT_TSTRING, 14848)
PR_ACCOUNT_W = PROP_TAG(PT_UNICODE, 14848)
PR_ACCOUNT_A = PROP_TAG(PT_STRING8, 14848)
PR_ALTERNATE_RECIPIENT = PROP_TAG(PT_BINARY, 14849)
PR_CALLBACK_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14850)
PR_CALLBACK_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14850)
PR_CALLBACK_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14850)
PR_CONVERSION_PROHIBITED = PROP_TAG(PT_BOOLEAN, 14851)
PR_DISCLOSE_RECIPIENTS = PROP_TAG(PT_BOOLEAN, 14852)
PR_GENERATION = PROP_TAG(PT_TSTRING, 14853)
PR_GENERATION_W = PROP_TAG(PT_UNICODE, 14853)
PR_GENERATION_A = PROP_TAG(PT_STRING8, 14853)
PR_GIVEN_NAME = PROP_TAG(PT_TSTRING, 14854)
PR_GIVEN_NAME_W = PROP_TAG(PT_UNICODE, 14854)
PR_GIVEN_NAME_A = PROP_TAG(PT_STRING8, 14854)
PR_GOVERNMENT_ID_NUMBER = PROP_TAG(PT_TSTRING, 14855)
PR_GOVERNMENT_ID_NUMBER_W = PROP_TAG(PT_UNICODE, 14855)
PR_GOVERNMENT_ID_NUMBER_A = PROP_TAG(PT_STRING8, 14855)
PR_BUSINESS_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14856)
PR_BUSINESS_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14856)
PR_BUSINESS_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14856)
PR_OFFICE_TELEPHONE_NUMBER = PR_BUSINESS_TELEPHONE_NUMBER
PR_OFFICE_TELEPHONE_NUMBER_W = PR_BUSINESS_TELEPHONE_NUMBER_W
PR_OFFICE_TELEPHONE_NUMBER_A = PR_BUSINESS_TELEPHONE_NUMBER_A
PR_HOME_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14857)
PR_HOME_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14857)
PR_HOME_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14857)
PR_INITIALS = PROP_TAG(PT_TSTRING, 14858)
PR_INITIALS_W = PROP_TAG(PT_UNICODE, 14858)
PR_INITIALS_A = PROP_TAG(PT_STRING8, 14858)
PR_KEYWORD = PROP_TAG(PT_TSTRING, 14859)
PR_KEYWORD_W = PROP_TAG(PT_UNICODE, 14859)
PR_KEYWORD_A = PROP_TAG(PT_STRING8, 14859)
PR_LANGUAGE = PROP_TAG(PT_TSTRING, 14860)
PR_LANGUAGE_W = PROP_TAG(PT_UNICODE, 14860)
PR_LANGUAGE_A = PROP_TAG(PT_STRING8, 14860)
PR_LOCATION = PROP_TAG(PT_TSTRING, 14861)
PR_LOCATION_W = PROP_TAG(PT_UNICODE, 14861)
PR_LOCATION_A = PROP_TAG(PT_STRING8, 14861)
PR_MAIL_PERMISSION = PROP_TAG(PT_BOOLEAN, 14862)
PR_MHS_COMMON_NAME = PROP_TAG(PT_TSTRING, 14863)
PR_MHS_COMMON_NAME_W = PROP_TAG(PT_UNICODE, 14863)
PR_MHS_COMMON_NAME_A = PROP_TAG(PT_STRING8, 14863)
PR_ORGANIZATIONAL_ID_NUMBER = PROP_TAG(PT_TSTRING, 14864)
PR_ORGANIZATIONAL_ID_NUMBER_W = PROP_TAG(PT_UNICODE, 14864)
PR_ORGANIZATIONAL_ID_NUMBER_A = PROP_TAG(PT_STRING8, 14864)
PR_SURNAME = PROP_TAG(PT_TSTRING, 14865)
PR_SURNAME_W = PROP_TAG(PT_UNICODE, 14865)
PR_SURNAME_A = PROP_TAG(PT_STRING8, 14865)
PR_ORIGINAL_ENTRYID = PROP_TAG(PT_BINARY, 14866)
PR_ORIGINAL_DISPLAY_NAME = PROP_TAG(PT_TSTRING, 14867)
PR_ORIGINAL_DISPLAY_NAME_W = PROP_TAG(PT_UNICODE, 14867)
PR_ORIGINAL_DISPLAY_NAME_A = PROP_TAG(PT_STRING8, 14867)
PR_ORIGINAL_SEARCH_KEY = PROP_TAG(PT_BINARY, 14868)
PR_POSTAL_ADDRESS = PROP_TAG(PT_TSTRING, 14869)
PR_POSTAL_ADDRESS_W = PROP_TAG(PT_UNICODE, 14869)
PR_POSTAL_ADDRESS_A = PROP_TAG(PT_STRING8, 14869)
PR_COMPANY_NAME = PROP_TAG(PT_TSTRING, 14870)
PR_COMPANY_NAME_W = PROP_TAG(PT_UNICODE, 14870)
PR_COMPANY_NAME_A = PROP_TAG(PT_STRING8, 14870)
PR_TITLE = PROP_TAG(PT_TSTRING, 14871)
PR_TITLE_W = PROP_TAG(PT_UNICODE, 14871)
PR_TITLE_A = PROP_TAG(PT_STRING8, 14871)
PR_DEPARTMENT_NAME = PROP_TAG(PT_TSTRING, 14872)
PR_DEPARTMENT_NAME_W = PROP_TAG(PT_UNICODE, 14872)
PR_DEPARTMENT_NAME_A = PROP_TAG(PT_STRING8, 14872)
PR_OFFICE_LOCATION = PROP_TAG(PT_TSTRING, 14873)
PR_OFFICE_LOCATION_W = PROP_TAG(PT_UNICODE, 14873)
PR_OFFICE_LOCATION_A = PROP_TAG(PT_STRING8, 14873)
PR_PRIMARY_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14874)
PR_PRIMARY_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14874)
PR_PRIMARY_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14874)
PR_BUSINESS2_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14875)
PR_BUSINESS2_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14875)
PR_BUSINESS2_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14875)
PR_OFFICE2_TELEPHONE_NUMBER = PR_BUSINESS2_TELEPHONE_NUMBER
PR_OFFICE2_TELEPHONE_NUMBER_W = PR_BUSINESS2_TELEPHONE_NUMBER_W
PR_OFFICE2_TELEPHONE_NUMBER_A = PR_BUSINESS2_TELEPHONE_NUMBER_A
PR_MOBILE_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14876)
PR_MOBILE_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14876)
PR_MOBILE_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14876)
PR_CELLULAR_TELEPHONE_NUMBER = PR_MOBILE_TELEPHONE_NUMBER
PR_CELLULAR_TELEPHONE_NUMBER_W = PR_MOBILE_TELEPHONE_NUMBER_W
PR_CELLULAR_TELEPHONE_NUMBER_A = PR_MOBILE_TELEPHONE_NUMBER_A
PR_RADIO_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14877)
PR_RADIO_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14877)
PR_RADIO_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14877)
PR_CAR_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14878)
PR_CAR_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14878)
PR_CAR_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14878)
PR_OTHER_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14879)
PR_OTHER_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14879)
PR_OTHER_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14879)
PR_TRANSMITABLE_DISPLAY_NAME = PROP_TAG(PT_TSTRING, 14880)
PR_TRANSMITABLE_DISPLAY_NAME_W = PROP_TAG(PT_UNICODE, 14880)
PR_TRANSMITABLE_DISPLAY_NAME_A = PROP_TAG(PT_STRING8, 14880)
PR_PAGER_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14881)
PR_PAGER_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14881)
PR_PAGER_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14881)
PR_BEEPER_TELEPHONE_NUMBER = PR_PAGER_TELEPHONE_NUMBER
PR_BEEPER_TELEPHONE_NUMBER_W = PR_PAGER_TELEPHONE_NUMBER_W
PR_BEEPER_TELEPHONE_NUMBER_A = PR_PAGER_TELEPHONE_NUMBER_A
PR_USER_CERTIFICATE = PROP_TAG(PT_BINARY, 14882)
PR_PRIMARY_FAX_NUMBER = PROP_TAG(PT_TSTRING, 14883)
PR_PRIMARY_FAX_NUMBER_W = PROP_TAG(PT_UNICODE, 14883)
PR_PRIMARY_FAX_NUMBER_A = PROP_TAG(PT_STRING8, 14883)
PR_BUSINESS_FAX_NUMBER = PROP_TAG(PT_TSTRING, 14884)
PR_BUSINESS_FAX_NUMBER_W = PROP_TAG(PT_UNICODE, 14884)
PR_BUSINESS_FAX_NUMBER_A = PROP_TAG(PT_STRING8, 14884)
PR_HOME_FAX_NUMBER = PROP_TAG(PT_TSTRING, 14885)
PR_HOME_FAX_NUMBER_W = PROP_TAG(PT_UNICODE, 14885)
PR_HOME_FAX_NUMBER_A = PROP_TAG(PT_STRING8, 14885)
PR_COUNTRY = PROP_TAG(PT_TSTRING, 14886)
PR_COUNTRY_W = PROP_TAG(PT_UNICODE, 14886)
PR_COUNTRY_A = PROP_TAG(PT_STRING8, 14886)
PR_BUSINESS_ADDRESS_COUNTRY = PR_COUNTRY
PR_BUSINESS_ADDRESS_COUNTRY_W = PR_COUNTRY_W
PR_BUSINESS_ADDRESS_COUNTRY_A = PR_COUNTRY_A
PR_LOCALITY = PROP_TAG(PT_TSTRING, 14887)
PR_LOCALITY_W = PROP_TAG(PT_UNICODE, 14887)
PR_LOCALITY_A = PROP_TAG(PT_STRING8, 14887)
PR_BUSINESS_ADDRESS_CITY = PR_LOCALITY
PR_BUSINESS_ADDRESS_CITY_W = PR_LOCALITY_W
PR_BUSINESS_ADDRESS_CITY_A = PR_LOCALITY_A
PR_STATE_OR_PROVINCE = PROP_TAG(PT_TSTRING, 14888)
PR_STATE_OR_PROVINCE_W = PROP_TAG(PT_UNICODE, 14888)
PR_STATE_OR_PROVINCE_A = PROP_TAG(PT_STRING8, 14888)
PR_BUSINESS_ADDRESS_STATE_OR_PROVINCE = PR_STATE_OR_PROVINCE
PR_BUSINESS_ADDRESS_STATE_OR_PROVINCE_W = PR_STATE_OR_PROVINCE_W
PR_BUSINESS_ADDRESS_STATE_OR_PROVINCE_A = PR_STATE_OR_PROVINCE_A
PR_STREET_ADDRESS = PROP_TAG(PT_TSTRING, 14889)
PR_STREET_ADDRESS_W = PROP_TAG(PT_UNICODE, 14889)
PR_STREET_ADDRESS_A = PROP_TAG(PT_STRING8, 14889)
PR_BUSINESS_ADDRESS_STREET = PR_STREET_ADDRESS
PR_BUSINESS_ADDRESS_STREET_W = PR_STREET_ADDRESS_W
PR_BUSINESS_ADDRESS_STREET_A = PR_STREET_ADDRESS_A
PR_POSTAL_CODE = PROP_TAG(PT_TSTRING, 14890)
PR_POSTAL_CODE_W = PROP_TAG(PT_UNICODE, 14890)
PR_POSTAL_CODE_A = PROP_TAG(PT_STRING8, 14890)
PR_BUSINESS_ADDRESS_POSTAL_CODE = PR_POSTAL_CODE
PR_BUSINESS_ADDRESS_POSTAL_CODE_W = PR_POSTAL_CODE_W
PR_BUSINESS_ADDRESS_POSTAL_CODE_A = PR_POSTAL_CODE_A
PR_POST_OFFICE_BOX = PROP_TAG(PT_TSTRING, 14891)
PR_POST_OFFICE_BOX_W = PROP_TAG(PT_UNICODE, 14891)
PR_POST_OFFICE_BOX_A = PROP_TAG(PT_STRING8, 14891)
PR_BUSINESS_ADDRESS_POST_OFFICE_BOX = PR_POST_OFFICE_BOX
PR_BUSINESS_ADDRESS_POST_OFFICE_BOX_W = PR_POST_OFFICE_BOX_W
PR_BUSINESS_ADDRESS_POST_OFFICE_BOX_A = PR_POST_OFFICE_BOX_A
PR_TELEX_NUMBER = PROP_TAG(PT_TSTRING, 14892)
PR_TELEX_NUMBER_W = PROP_TAG(PT_UNICODE, 14892)
PR_TELEX_NUMBER_A = PROP_TAG(PT_STRING8, 14892)
PR_ISDN_NUMBER = PROP_TAG(PT_TSTRING, 14893)
PR_ISDN_NUMBER_W = PROP_TAG(PT_UNICODE, 14893)
PR_ISDN_NUMBER_A = PROP_TAG(PT_STRING8, 14893)
PR_ASSISTANT_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14894)
PR_ASSISTANT_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14894)
PR_ASSISTANT_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14894)
PR_HOME2_TELEPHONE_NUMBER = PROP_TAG(PT_TSTRING, 14895)
PR_HOME2_TELEPHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14895)
PR_HOME2_TELEPHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14895)
PR_ASSISTANT = PROP_TAG(PT_TSTRING, 14896)
PR_ASSISTANT_W = PROP_TAG(PT_UNICODE, 14896)
PR_ASSISTANT_A = PROP_TAG(PT_STRING8, 14896)
PR_SEND_RICH_INFO = PROP_TAG(PT_BOOLEAN, 14912)
PR_WEDDING_ANNIVERSARY = PROP_TAG(PT_SYSTIME, 14913)
PR_BIRTHDAY = PROP_TAG(PT_SYSTIME, 14914)
PR_HOBBIES = PROP_TAG(PT_TSTRING, 14915)
PR_HOBBIES_W = PROP_TAG(PT_UNICODE, 14915)
PR_HOBBIES_A = PROP_TAG(PT_STRING8, 14915)
PR_MIDDLE_NAME = PROP_TAG(PT_TSTRING, 14916)
PR_MIDDLE_NAME_W = PROP_TAG(PT_UNICODE, 14916)
PR_MIDDLE_NAME_A = PROP_TAG(PT_STRING8, 14916)
PR_DISPLAY_NAME_PREFIX = PROP_TAG(PT_TSTRING, 14917)
PR_DISPLAY_NAME_PREFIX_W = PROP_TAG(PT_UNICODE, 14917)
PR_DISPLAY_NAME_PREFIX_A = PROP_TAG(PT_STRING8, 14917)
PR_PROFESSION = PROP_TAG(PT_TSTRING, 14918)
PR_PROFESSION_W = PROP_TAG(PT_UNICODE, 14918)
PR_PROFESSION_A = PROP_TAG(PT_STRING8, 14918)
PR_PREFERRED_BY_NAME = PROP_TAG(PT_TSTRING, 14919)
PR_PREFERRED_BY_NAME_W = PROP_TAG(PT_UNICODE, 14919)
PR_PREFERRED_BY_NAME_A = PROP_TAG(PT_STRING8, 14919)
PR_SPOUSE_NAME = PROP_TAG(PT_TSTRING, 14920)
PR_SPOUSE_NAME_W = PROP_TAG(PT_UNICODE, 14920)
PR_SPOUSE_NAME_A = PROP_TAG(PT_STRING8, 14920)
PR_COMPUTER_NETWORK_NAME = PROP_TAG(PT_TSTRING, 14921)
PR_COMPUTER_NETWORK_NAME_W = PROP_TAG(PT_UNICODE, 14921)
PR_COMPUTER_NETWORK_NAME_A = PROP_TAG(PT_STRING8, 14921)
PR_CUSTOMER_ID = PROP_TAG(PT_TSTRING, 14922)
PR_CUSTOMER_ID_W = PROP_TAG(PT_UNICODE, 14922)
PR_CUSTOMER_ID_A = PROP_TAG(PT_STRING8, 14922)
PR_TTYTDD_PHONE_NUMBER = PROP_TAG(PT_TSTRING, 14923)
PR_TTYTDD_PHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14923)
PR_TTYTDD_PHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14923)
PR_FTP_SITE = PROP_TAG(PT_TSTRING, 14924)
PR_FTP_SITE_W = PROP_TAG(PT_UNICODE, 14924)
PR_FTP_SITE_A = PROP_TAG(PT_STRING8, 14924)
PR_GENDER = PROP_TAG(PT_SHORT, 14925)
PR_MANAGER_NAME = PROP_TAG(PT_TSTRING, 14926)
PR_MANAGER_NAME_W = PROP_TAG(PT_UNICODE, 14926)
PR_MANAGER_NAME_A = PROP_TAG(PT_STRING8, 14926)
PR_NICKNAME = PROP_TAG(PT_TSTRING, 14927)
PR_NICKNAME_W = PROP_TAG(PT_UNICODE, 14927)
PR_NICKNAME_A = PROP_TAG(PT_STRING8, 14927)
PR_PERSONAL_HOME_PAGE = PROP_TAG(PT_TSTRING, 14928)
PR_PERSONAL_HOME_PAGE_W = PROP_TAG(PT_UNICODE, 14928)
PR_PERSONAL_HOME_PAGE_A = PROP_TAG(PT_STRING8, 14928)
PR_BUSINESS_HOME_PAGE = PROP_TAG(PT_TSTRING, 14929)
PR_BUSINESS_HOME_PAGE_W = PROP_TAG(PT_UNICODE, 14929)
PR_BUSINESS_HOME_PAGE_A = PROP_TAG(PT_STRING8, 14929)
PR_CONTACT_VERSION = PROP_TAG(PT_CLSID, 14930)
PR_CONTACT_ENTRYIDS = PROP_TAG(PT_MV_BINARY, 14931)
PR_CONTACT_ADDRTYPES = PROP_TAG(PT_MV_TSTRING, 14932)
PR_CONTACT_ADDRTYPES_W = PROP_TAG(PT_MV_UNICODE, 14932)
PR_CONTACT_ADDRTYPES_A = PROP_TAG(PT_MV_STRING8, 14932)
PR_CONTACT_DEFAULT_ADDRESS_INDEX = PROP_TAG(PT_LONG, 14933)
PR_CONTACT_EMAIL_ADDRESSES = PROP_TAG(PT_MV_TSTRING, 14934)
PR_CONTACT_EMAIL_ADDRESSES_W = PROP_TAG(PT_MV_UNICODE, 14934)
PR_CONTACT_EMAIL_ADDRESSES_A = PROP_TAG(PT_MV_STRING8, 14934)
PR_COMPANY_MAIN_PHONE_NUMBER = PROP_TAG(PT_TSTRING, 14935)
PR_COMPANY_MAIN_PHONE_NUMBER_W = PROP_TAG(PT_UNICODE, 14935)
PR_COMPANY_MAIN_PHONE_NUMBER_A = PROP_TAG(PT_STRING8, 14935)
PR_CHILDRENS_NAMES = PROP_TAG(PT_MV_TSTRING, 14936)
PR_CHILDRENS_NAMES_W = PROP_TAG(PT_MV_UNICODE, 14936)
PR_CHILDRENS_NAMES_A = PROP_TAG(PT_MV_STRING8, 14936)
PR_HOME_ADDRESS_CITY = PROP_TAG(PT_TSTRING, 14937)
PR_HOME_ADDRESS_CITY_W = PROP_TAG(PT_UNICODE, 14937)
PR_HOME_ADDRESS_CITY_A = PROP_TAG(PT_STRING8, 14937)
PR_HOME_ADDRESS_COUNTRY = PROP_TAG(PT_TSTRING, 14938)
PR_HOME_ADDRESS_COUNTRY_W = PROP_TAG(PT_UNICODE, 14938)
PR_HOME_ADDRESS_COUNTRY_A = PROP_TAG(PT_STRING8, 14938)
PR_HOME_ADDRESS_POSTAL_CODE = PROP_TAG(PT_TSTRING, 14939)
PR_HOME_ADDRESS_POSTAL_CODE_W = PROP_TAG(PT_UNICODE, 14939)
PR_HOME_ADDRESS_POSTAL_CODE_A = PROP_TAG(PT_STRING8, 14939)
PR_HOME_ADDRESS_STATE_OR_PROVINCE = PROP_TAG(PT_TSTRING, 14940)
PR_HOME_ADDRESS_STATE_OR_PROVINCE_W = PROP_TAG(PT_UNICODE, 14940)
PR_HOME_ADDRESS_STATE_OR_PROVINCE_A = PROP_TAG(PT_STRING8, 14940)
PR_HOME_ADDRESS_STREET = PROP_TAG(PT_TSTRING, 14941)
PR_HOME_ADDRESS_STREET_W = PROP_TAG(PT_UNICODE, 14941)
PR_HOME_ADDRESS_STREET_A = PROP_TAG(PT_STRING8, 14941)
PR_HOME_ADDRESS_POST_OFFICE_BOX = PROP_TAG(PT_TSTRING, 14942)
PR_HOME_ADDRESS_POST_OFFICE_BOX_W = PROP_TAG(PT_UNICODE, 14942)
PR_HOME_ADDRESS_POST_OFFICE_BOX_A = PROP_TAG(PT_STRING8, 14942)
PR_OTHER_ADDRESS_CITY = PROP_TAG(PT_TSTRING, 14943)
PR_OTHER_ADDRESS_CITY_W = PROP_TAG(PT_UNICODE, 14943)
PR_OTHER_ADDRESS_CITY_A = PROP_TAG(PT_STRING8, 14943)
PR_OTHER_ADDRESS_COUNTRY = PROP_TAG(PT_TSTRING, 14944)
PR_OTHER_ADDRESS_COUNTRY_W = PROP_TAG(PT_UNICODE, 14944)
PR_OTHER_ADDRESS_COUNTRY_A = PROP_TAG(PT_STRING8, 14944)
PR_OTHER_ADDRESS_POSTAL_CODE = PROP_TAG(PT_TSTRING, 14945)
PR_OTHER_ADDRESS_POSTAL_CODE_W = PROP_TAG(PT_UNICODE, 14945)
PR_OTHER_ADDRESS_POSTAL_CODE_A = PROP_TAG(PT_STRING8, 14945)
PR_OTHER_ADDRESS_STATE_OR_PROVINCE = PROP_TAG(PT_TSTRING, 14946)
PR_OTHER_ADDRESS_STATE_OR_PROVINCE_W = PROP_TAG(PT_UNICODE, 14946)
PR_OTHER_ADDRESS_STATE_OR_PROVINCE_A = PROP_TAG(PT_STRING8, 14946)
PR_OTHER_ADDRESS_STREET = PROP_TAG(PT_TSTRING, 14947)
PR_OTHER_ADDRESS_STREET_W = PROP_TAG(PT_UNICODE, 14947)
PR_OTHER_ADDRESS_STREET_A = PROP_TAG(PT_STRING8, 14947)
PR_OTHER_ADDRESS_POST_OFFICE_BOX = PROP_TAG(PT_TSTRING, 14948)
PR_OTHER_ADDRESS_POST_OFFICE_BOX_W = PROP_TAG(PT_UNICODE, 14948)
PR_OTHER_ADDRESS_POST_OFFICE_BOX_A = PROP_TAG(PT_STRING8, 14948)
PR_STORE_PROVIDERS = PROP_TAG(PT_BINARY, 15616)
PR_AB_PROVIDERS = PROP_TAG(PT_BINARY, 15617)
PR_TRANSPORT_PROVIDERS = PROP_TAG(PT_BINARY, 15618)
PR_DEFAULT_PROFILE = PROP_TAG(PT_BOOLEAN, 15620)
PR_AB_SEARCH_PATH = PROP_TAG(PT_MV_BINARY, 15621)
PR_AB_DEFAULT_DIR = PROP_TAG(PT_BINARY, 15622)
PR_AB_DEFAULT_PAB = PROP_TAG(PT_BINARY, 15623)
PR_FILTERING_HOOKS = PROP_TAG(PT_BINARY, 15624)
PR_SERVICE_NAME = PROP_TAG(PT_TSTRING, 15625)
PR_SERVICE_NAME_W = PROP_TAG(PT_UNICODE, 15625)
PR_SERVICE_NAME_A = PROP_TAG(PT_STRING8, 15625)
PR_SERVICE_DLL_NAME = PROP_TAG(PT_TSTRING, 15626)
PR_SERVICE_DLL_NAME_W = PROP_TAG(PT_UNICODE, 15626)
PR_SERVICE_DLL_NAME_A = PROP_TAG(PT_STRING8, 15626)
PR_SERVICE_ENTRY_NAME = PROP_TAG(PT_STRING8, 15627)
PR_SERVICE_UID = PROP_TAG(PT_BINARY, 15628)
PR_SERVICE_EXTRA_UIDS = PROP_TAG(PT_BINARY, 15629)
PR_SERVICES = PROP_TAG(PT_BINARY, 15630)
PR_SERVICE_SUPPORT_FILES = PROP_TAG(PT_MV_TSTRING, 15631)
PR_SERVICE_SUPPORT_FILES_W = PROP_TAG(PT_MV_UNICODE, 15631)
PR_SERVICE_SUPPORT_FILES_A = PROP_TAG(PT_MV_STRING8, 15631)
PR_SERVICE_DELETE_FILES = PROP_TAG(PT_MV_TSTRING, 15632)
PR_SERVICE_DELETE_FILES_W = PROP_TAG(PT_MV_UNICODE, 15632)
PR_SERVICE_DELETE_FILES_A = PROP_TAG(PT_MV_STRING8, 15632)
PR_AB_SEARCH_PATH_UPDATE = PROP_TAG(PT_BINARY, 15633)
PR_PROFILE_NAME = PROP_TAG(PT_TSTRING, 15634)
PR_PROFILE_NAME_A = PROP_TAG(PT_STRING8, 15634)
PR_PROFILE_NAME_W = PROP_TAG(PT_UNICODE, 15634)
PR_IDENTITY_DISPLAY = PROP_TAG(PT_TSTRING, 15872)
PR_IDENTITY_DISPLAY_W = PROP_TAG(PT_UNICODE, 15872)
PR_IDENTITY_DISPLAY_A = PROP_TAG(PT_STRING8, 15872)
PR_IDENTITY_ENTRYID = PROP_TAG(PT_BINARY, 15873)
PR_RESOURCE_METHODS = PROP_TAG(PT_LONG, 15874)
PR_RESOURCE_TYPE = PROP_TAG(PT_LONG, 15875)
PR_STATUS_CODE = PROP_TAG(PT_LONG, 15876)
PR_IDENTITY_SEARCH_KEY = PROP_TAG(PT_BINARY, 15877)
PR_OWN_STORE_ENTRYID = PROP_TAG(PT_BINARY, 15878)
PR_RESOURCE_PATH = PROP_TAG(PT_TSTRING, 15879)
PR_RESOURCE_PATH_W = PROP_TAG(PT_UNICODE, 15879)
PR_RESOURCE_PATH_A = PROP_TAG(PT_STRING8, 15879)
PR_STATUS_STRING = PROP_TAG(PT_TSTRING, 15880)
PR_STATUS_STRING_W = PROP_TAG(PT_UNICODE, 15880)
PR_STATUS_STRING_A = PROP_TAG(PT_STRING8, 15880)
PR_X400_DEFERRED_DELIVERY_CANCEL = PROP_TAG(PT_BOOLEAN, 15881)
PR_HEADER_FOLDER_ENTRYID = PROP_TAG(PT_BINARY, 15882)
PR_REMOTE_PROGRESS = PROP_TAG(PT_LONG, 15883)
PR_REMOTE_PROGRESS_TEXT = PROP_TAG(PT_TSTRING, 15884)
PR_REMOTE_PROGRESS_TEXT_W = PROP_TAG(PT_UNICODE, 15884)
PR_REMOTE_PROGRESS_TEXT_A = PROP_TAG(PT_STRING8, 15884)
PR_REMOTE_VALIDATE_OK = PROP_TAG(PT_BOOLEAN, 15885)
PR_CONTROL_FLAGS = PROP_TAG(PT_LONG, 16128)
PR_CONTROL_STRUCTURE = PROP_TAG(PT_BINARY, 16129)
PR_CONTROL_TYPE = PROP_TAG(PT_LONG, 16130)
PR_DELTAX = PROP_TAG(PT_LONG, 16131)
PR_DELTAY = PROP_TAG(PT_LONG, 16132)
PR_XPOS = PROP_TAG(PT_LONG, 16133)
PR_YPOS = PROP_TAG(PT_LONG, 16134)
PR_CONTROL_ID = PROP_TAG(PT_BINARY, 16135)
PR_INITIAL_DETAILS_PANE = PROP_TAG(PT_LONG, 16136)

PROP_ID_SECURE_MIN = 26608
PROP_ID_SECURE_MAX = 26623

# From EdkMdb.h
pidExchangeXmitReservedMin = 16352
pidExchangeNonXmitReservedMin = 26080
pidProfileMin = 26112
pidStoreMin = 26136
pidFolderMin = 26168
pidMessageReadOnlyMin = 26176
pidMessageWriteableMin = 26200
pidAttachReadOnlyMin = 26220
pidSpecialMin = 26224
pidAdminMin = 26256
pidSecureProfileMin = PROP_ID_SECURE_MIN

PR_PROFILE_VERSION = PROP_TAG(PT_LONG, pidProfileMin + 0)
PR_PROFILE_CONFIG_FLAGS = PROP_TAG(PT_LONG, pidProfileMin + 1)
PR_PROFILE_HOME_SERVER = PROP_TAG(PT_STRING8, pidProfileMin + 2)
PR_PROFILE_HOME_SERVER_DN = PROP_TAG(PT_STRING8, pidProfileMin + 18)
PR_PROFILE_HOME_SERVER_ADDRS = PROP_TAG(PT_MV_STRING8, pidProfileMin + 19)
PR_PROFILE_USER = PROP_TAG(PT_STRING8, pidProfileMin + 3)
PR_PROFILE_CONNECT_FLAGS = PROP_TAG(PT_LONG, pidProfileMin + 4)
PR_PROFILE_TRANSPORT_FLAGS = PROP_TAG(PT_LONG, pidProfileMin + 5)
PR_PROFILE_UI_STATE = PROP_TAG(PT_LONG, pidProfileMin + 6)
PR_PROFILE_UNRESOLVED_NAME = PROP_TAG(PT_STRING8, pidProfileMin + 7)
PR_PROFILE_UNRESOLVED_SERVER = PROP_TAG(PT_STRING8, pidProfileMin + 8)
PR_PROFILE_BINDING_ORDER = PROP_TAG(PT_STRING8, pidProfileMin + 9)
PR_PROFILE_MAX_RESTRICT = PROP_TAG(PT_LONG, pidProfileMin + 13)
PR_PROFILE_AB_FILES_PATH = PROP_TAG(PT_STRING8, pidProfileMin + 14)
PR_PROFILE_OFFLINE_STORE_PATH = PROP_TAG(PT_STRING8, pidProfileMin + 16)
PR_PROFILE_OFFLINE_INFO = PROP_TAG(PT_BINARY, pidProfileMin + 17)
PR_PROFILE_ADDR_INFO = PROP_TAG(PT_BINARY, pidSpecialMin + 23)
PR_PROFILE_OPTIONS_DATA = PROP_TAG(PT_BINARY, pidSpecialMin + 25)
PR_PROFILE_SECURE_MAILBOX = PROP_TAG(PT_BINARY, pidSecureProfileMin + 0)
PR_DISABLE_WINSOCK = PROP_TAG(PT_LONG, pidProfileMin + 24)
PR_OST_ENCRYPTION = PROP_TAG(PT_LONG, 26370)
PR_PROFILE_OPEN_FLAGS = PROP_TAG(PT_LONG, pidProfileMin + 9)
PR_PROFILE_TYPE = PROP_TAG(PT_LONG, pidProfileMin + 10)
PR_PROFILE_MAILBOX = PROP_TAG(PT_STRING8, pidProfileMin + 11)
PR_PROFILE_SERVER = PROP_TAG(PT_STRING8, pidProfileMin + 12)
PR_PROFILE_SERVER_DN = PROP_TAG(PT_STRING8, pidProfileMin + 20)
PR_PROFILE_FAVFLD_DISPLAY_NAME = PROP_TAG(PT_STRING8, pidProfileMin + 15)
PR_PROFILE_FAVFLD_COMMENT = PROP_TAG(PT_STRING8, pidProfileMin + 21)
PR_PROFILE_ALLPUB_DISPLAY_NAME = PROP_TAG(PT_STRING8, pidProfileMin + 22)
PR_PROFILE_ALLPUB_COMMENT = PROP_TAG(PT_STRING8, pidProfileMin + 23)

OSTF_NO_ENCRYPTION = -2147483648
OSTF_COMPRESSABLE_ENCRYPTION = 1073741824
OSTF_BEST_ENCRYPTION = 536870912


PR_NON_IPM_SUBTREE_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 8)
PR_EFORMS_REGISTRY_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 9)
PR_SPLUS_FREE_BUSY_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 10)
PR_OFFLINE_ADDRBOOK_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 11)
PR_EFORMS_FOR_LOCALE_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 12)
PR_FREE_BUSY_FOR_LOCAL_SITE_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 13)
PR_ADDRBOOK_FOR_LOCAL_SITE_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 14)
PR_OFFLINE_MESSAGE_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 15)
PR_IPM_FAVORITES_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 24)
PR_IPM_PUBLIC_FOLDERS_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 25)
PR_GW_MTSIN_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 16)
PR_GW_MTSOUT_ENTRYID = PROP_TAG(PT_BINARY, pidStoreMin + 17)
PR_TRANSFER_ENABLED = PROP_TAG(PT_BOOLEAN, pidStoreMin + 18)
PR_TEST_LINE_SPEED = PROP_TAG(PT_BINARY, pidStoreMin + 19)
PR_HIERARCHY_SYNCHRONIZER = PROP_TAG(PT_OBJECT, pidStoreMin + 20)
PR_CONTENTS_SYNCHRONIZER = PROP_TAG(PT_OBJECT, pidStoreMin + 21)
PR_COLLECTOR = PROP_TAG(PT_OBJECT, pidStoreMin + 22)
PR_FAST_TRANSFER = PROP_TAG(PT_OBJECT, pidStoreMin + 23)
PR_STORE_OFFLINE = PROP_TAG(PT_BOOLEAN, pidStoreMin + 26)
PR_IN_TRANSIT = PROP_TAG(PT_BOOLEAN, pidStoreMin)
PR_REPLICATION_STYLE = PROP_TAG(PT_LONG, pidAdminMin)
PR_REPLICATION_SCHEDULE = PROP_TAG(PT_BINARY, pidAdminMin + 1)
PR_REPLICATION_MESSAGE_PRIORITY = PROP_TAG(PT_LONG, pidAdminMin + 2)
PR_OVERALL_MSG_AGE_LIMIT = PROP_TAG(PT_LONG, pidAdminMin + 3)
PR_REPLICATION_ALWAYS_INTERVAL = PROP_TAG(PT_LONG, pidAdminMin + 4)
PR_REPLICATION_MSG_SIZE = PROP_TAG(PT_LONG, pidAdminMin + 5)
STYLE_ALWAYS_INTERVAL_DEFAULT = 15
REPLICATION_MESSAGE_SIZE_LIMIT_DEFAULT = 100
STYLE_NEVER = 0
STYLE_NORMAL = 1
STYLE_ALWAYS = 2
STYLE_DEFAULT = -1
PR_SOURCE_KEY = PROP_TAG(PT_BINARY, pidExchangeNonXmitReservedMin + 0)
PR_PARENT_SOURCE_KEY = PROP_TAG(PT_BINARY, pidExchangeNonXmitReservedMin + 1)
PR_CHANGE_KEY = PROP_TAG(PT_BINARY, pidExchangeNonXmitReservedMin + 2)
PR_PREDECESSOR_CHANGE_LIST = PROP_TAG(PT_BINARY, pidExchangeNonXmitReservedMin + 3)
PR_FOLDER_CHILD_COUNT = PROP_TAG(PT_LONG, pidFolderMin)
PR_RIGHTS = PROP_TAG(PT_LONG, pidFolderMin + 1)
PR_ACL_TABLE = PROP_TAG(PT_OBJECT, pidExchangeXmitReservedMin)
PR_RULES_TABLE = PROP_TAG(PT_OBJECT, pidExchangeXmitReservedMin + 1)
PR_HAS_RULES = PROP_TAG(PT_BOOLEAN, pidFolderMin + 2)
PR_ADDRESS_BOOK_ENTRYID = PROP_TAG(PT_BINARY, pidFolderMin + 3)
PR_ACL_DATA = PROP_TAG(PT_BINARY, pidExchangeXmitReservedMin)
PR_RULES_DATA = PROP_TAG(PT_BINARY, pidExchangeXmitReservedMin + 1)
PR_FOLDER_DESIGN_FLAGS = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 2)
PR_DESIGN_IN_PROGRESS = PROP_TAG(PT_BOOLEAN, pidExchangeXmitReservedMin + 4)
PR_SECURE_ORIGINATION = PROP_TAG(PT_BOOLEAN, pidExchangeXmitReservedMin + 5)
PR_PUBLISH_IN_ADDRESS_BOOK = PROP_TAG(PT_BOOLEAN, pidExchangeXmitReservedMin + 6)
PR_RESOLVE_METHOD = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 7)
PR_ADDRESS_BOOK_DISPLAY_NAME = PROP_TAG(PT_TSTRING, pidExchangeXmitReservedMin + 8)
PR_EFORMS_LOCALE_ID = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 9)
PR_REPLICA_LIST = PROP_TAG(PT_BINARY, pidAdminMin + 8)
PR_OVERALL_AGE_LIMIT = PROP_TAG(PT_LONG, pidAdminMin + 9)
RESOLVE_METHOD_DEFAULT = 0
RESOLVE_METHOD_LAST_WRITER_WINS = 1
RESOLVE_METHOD_NO_CONFLICT_NOTIFICATION = 2
PR_PUBLIC_FOLDER_ENTRYID = PROP_TAG(PT_BINARY, pidFolderMin + 4)
PR_HAS_NAMED_PROPERTIES = PROP_TAG(PT_BOOLEAN, pidMessageReadOnlyMin + 10)
PR_CREATOR_NAME = PROP_TAG(PT_TSTRING, pidExchangeXmitReservedMin + 24)
PR_CREATOR_ENTRYID = PROP_TAG(PT_BINARY, pidExchangeXmitReservedMin + 25)
PR_LAST_MODIFIER_NAME = PROP_TAG(PT_TSTRING, pidExchangeXmitReservedMin + 26)
PR_LAST_MODIFIER_ENTRYID = PROP_TAG(PT_BINARY, pidExchangeXmitReservedMin + 27)
PR_HAS_DAMS = PROP_TAG(PT_BOOLEAN, pidExchangeXmitReservedMin + 10)
PR_RULE_TRIGGER_HISTORY = PROP_TAG(PT_BINARY, pidExchangeXmitReservedMin + 18)
PR_MOVE_TO_STORE_ENTRYID = PROP_TAG(PT_BINARY, pidExchangeXmitReservedMin + 19)
PR_MOVE_TO_FOLDER_ENTRYID = PROP_TAG(PT_BINARY, pidExchangeXmitReservedMin + 20)
PR_REPLICA_SERVER = PROP_TAG(PT_TSTRING, pidMessageReadOnlyMin + 4)
PR_DEFERRED_SEND_NUMBER = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 11)
PR_DEFERRED_SEND_UNITS = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 12)
PR_EXPIRY_NUMBER = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 13)
PR_EXPIRY_UNITS = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 14)
PR_DEFERRED_SEND_TIME = PROP_TAG(PT_SYSTIME, pidExchangeXmitReservedMin + 15)
PR_GW_ADMIN_OPERATIONS = PROP_TAG(PT_LONG, pidMessageWriteableMin)
PR_P1_CONTENT = PROP_TAG(PT_BINARY, 4352)
PR_P1_CONTENT_TYPE = PROP_TAG(PT_BINARY, 4353)
PR_CLIENT_ACTIONS = PROP_TAG(PT_BINARY, pidMessageReadOnlyMin + 5)
PR_DAM_ORIGINAL_ENTRYID = PROP_TAG(PT_BINARY, pidMessageReadOnlyMin + 6)
PR_DAM_BACK_PATCHED = PROP_TAG(PT_BOOLEAN, pidMessageReadOnlyMin + 7)
PR_RULE_ERROR = PROP_TAG(PT_LONG, pidMessageReadOnlyMin + 8)
PR_RULE_ACTION_TYPE = PROP_TAG(PT_LONG, pidMessageReadOnlyMin + 9)
PR_RULE_ACTION_NUMBER = PROP_TAG(PT_LONG, pidMessageReadOnlyMin + 16)
PR_RULE_FOLDER_ENTRYID = PROP_TAG(PT_BINARY, pidMessageReadOnlyMin + 17)
PR_CONFLICT_ENTRYID = PROP_TAG(PT_BINARY, pidExchangeXmitReservedMin + 16)
PR_MESSAGE_LOCALE_ID = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 17)
PR_STORAGE_QUOTA_LIMIT = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 21)
PR_EXCESS_STORAGE_USED = PROP_TAG(PT_LONG, pidExchangeXmitReservedMin + 22)
PR_SVR_GENERATING_QUOTA_MSG = PROP_TAG(PT_TSTRING, pidExchangeXmitReservedMin + 23)
PR_DELEGATED_BY_RULE = PROP_TAG(PT_BOOLEAN, pidExchangeXmitReservedMin + 3)
MSGSTATUS_IN_CONFLICT = 2048
PR_IN_CONFLICT = PROP_TAG(PT_BOOLEAN, pidAttachReadOnlyMin)
PR_LONGTERM_ENTRYID_FROM_TABLE = PROP_TAG(PT_BINARY, pidSpecialMin)
PR_ORIGINATOR_NAME = PROP_TAG(PT_TSTRING, pidMessageWriteableMin + 3)
PR_ORIGINATOR_ADDR = PROP_TAG(PT_TSTRING, pidMessageWriteableMin + 4)
PR_ORIGINATOR_ADDRTYPE = PROP_TAG(PT_TSTRING, pidMessageWriteableMin + 5)
PR_ORIGINATOR_ENTRYID = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 6)
PR_ARRIVAL_TIME = PROP_TAG(PT_SYSTIME, pidMessageWriteableMin + 7)
PR_TRACE_INFO = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 8)
PR_INTERNAL_TRACE_INFO = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 18)
PR_SUBJECT_TRACE_INFO = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 9)
PR_RECIPIENT_NUMBER = PROP_TAG(PT_LONG, pidMessageWriteableMin + 10)
PR_MTS_SUBJECT_ID = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 11)
PR_REPORT_DESTINATION_NAME = PROP_TAG(PT_TSTRING, pidMessageWriteableMin + 12)
PR_REPORT_DESTINATION_ENTRYID = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 13)
PR_CONTENT_SEARCH_KEY = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 14)
PR_FOREIGN_ID = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 15)
PR_FOREIGN_REPORT_ID = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 16)
PR_FOREIGN_SUBJECT_ID = PROP_TAG(PT_BINARY, pidMessageWriteableMin + 17)
PR_MTS_ID = PR_MESSAGE_SUBMISSION_ID
PR_MTS_REPORT_ID = PR_MESSAGE_SUBMISSION_ID

PR_FOLDER_FLAGS = PROP_TAG(PT_LONG, pidAdminMin + 24)
PR_LAST_ACCESS_TIME = PROP_TAG(PT_SYSTIME, pidAdminMin + 25)
PR_RESTRICTION_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 26)
PR_CATEG_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 27)
PR_CACHED_COLUMN_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 28)
PR_NORMAL_MSG_W_ATTACH_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 29)
PR_ASSOC_MSG_W_ATTACH_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 30)
PR_RECIPIENT_ON_NORMAL_MSG_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 31)
PR_RECIPIENT_ON_ASSOC_MSG_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 32)
PR_ATTACH_ON_NORMAL_MSG_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 33)
PR_ATTACH_ON_ASSOC_MSG_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 34)
PR_NORMAL_MESSAGE_SIZE = PROP_TAG(PT_LONG, pidAdminMin + 35)
PR_NORMAL_MESSAGE_SIZE_EXTENDED = PROP_TAG(PT_I8, pidAdminMin + 35)
PR_ASSOC_MESSAGE_SIZE = PROP_TAG(PT_LONG, pidAdminMin + 36)
PR_ASSOC_MESSAGE_SIZE_EXTENDED = PROP_TAG(PT_I8, pidAdminMin + 36)
PR_FOLDER_PATHNAME = PROP_TAG(PT_TSTRING, pidAdminMin + 37)
PR_OWNER_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 38)
PR_CONTACT_COUNT = PROP_TAG(PT_LONG, pidAdminMin + 39)

PR_MESSAGE_SIZE_EXTENDED = PROP_TAG(PT_I8, PROP_ID(PR_MESSAGE_SIZE))

PR_USERFIELDS = PROP_TAG(PT_BINARY, 0x36E3)

# IExchangeManageStoreEx::CreateStoreEntryID2
PR_FORCE_USE_ENTRYID_SERVER = PROP_TAG(PT_BOOLEAN, 0x7CFE)
PR_PROFILE_MDB_DN = PROP_TAG(PT_STRING8, 0x7CFF)

# MSPST.h
PST_EXTERN_PROPID_BASE = 0x6700
PR_PST_PATH = PROP_TAG(PT_STRING8, PST_EXTERN_PROPID_BASE + 0)
PR_PST_PATH_W = PROP_TAG(PT_UNICODE, PST_EXTERN_PROPID_BASE + 0)
PR_PST_PATH_A = PROP_TAG(PT_STRING8, PST_EXTERN_PROPID_BASE + 0)
PR_PST_REMEMBER_PW = PROP_TAG(PT_BOOLEAN, PST_EXTERN_PROPID_BASE + 1)
PR_PST_ENCRYPTION = PROP_TAG(PT_LONG, PST_EXTERN_PROPID_BASE + 2)
PR_PST_PW_SZ_OLD = PROP_TAG(PT_STRING8, PST_EXTERN_PROPID_BASE + 3)
PR_PST_PW_SZ_OLD_W = PROP_TAG(PT_UNICODE, PST_EXTERN_PROPID_BASE + 3)
PR_PST_PW_SZ_OLD_A = PROP_TAG(PT_STRING8, PST_EXTERN_PROPID_BASE + 3)
PR_PST_PW_SZ_NEW = PROP_TAG(PT_STRING8, PST_EXTERN_PROPID_BASE + 4)
PR_PST_PW_SZ_NEW_W = PROP_TAG(PT_UNICODE, PST_EXTERN_PROPID_BASE + 4)
PR_PST_PW_SZ_NEW_A = PROP_TAG(PT_STRING8, PST_EXTERN_PROPID_BASE + 4)

# === NexusCore/policy_test_sandbox\app\__init__.py ===

# === NexusCore/quality_loop_test_sandbox\app\__init__.py ===

# === NexusCore/src\agents\__init__.py ===

# === NexusCore/src\code_interpreter\__init__.py ===

# === NexusCore/src\core\__init__.py ===

# === NexusCore/src\gradio_app\__init__.py ===

# === NexusCore/src\utils\__init__.py ===

# === NexusCore/workspace\default_project\app\__init__.py ===

# === NexusCore/openenv\Lib\site-packages\litellm\integrations\langfuse\langfuse.py ===
#### What this does ####
#    On success, logs events to Langfuse
import copy
import os
import traceback
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast

from packaging.version import Version

import litellm
from litellm._logging import verbose_logger
from litellm.constants import MAX_LANGFUSE_INITIALIZED_CLIENTS
from litellm.litellm_core_utils.redact_messages import redact_user_api_key_info
from litellm.llms.custom_httpx.http_handler import _get_httpx_client
from litellm.secret_managers.main import str_to_bool
from litellm.types.integrations.langfuse import *
from litellm.types.llms.openai import HttpxBinaryResponseContent
from litellm.types.utils import (
    EmbeddingResponse,
    ImageResponse,
    ModelResponse,
    RerankResponse,
    StandardLoggingPayload,
    StandardLoggingPromptManagementMetadata,
    TextCompletionResponse,
    TranscriptionResponse,
)

if TYPE_CHECKING:
    from langfuse.client import Langfuse, StatefulTraceClient

    from litellm.litellm_core_utils.litellm_logging import DynamicLoggingCache
else:
    DynamicLoggingCache = Any
    StatefulTraceClient = Any
    Langfuse = Any


class LangFuseLogger:
    # Class variables or attributes
    def __init__(
        self,
        langfuse_public_key=None,
        langfuse_secret=None,
        langfuse_host=None,
        flush_interval=1,
    ):
        try:
            import langfuse
            from langfuse import Langfuse
        except Exception as e:
            raise Exception(
                f"\033[91mLangfuse not installed, try running 'pip install langfuse' to fix this error: {e}\n{traceback.format_exc()}\033[0m"
            )
        # Instance variables
        self.secret_key = langfuse_secret or os.getenv("LANGFUSE_SECRET_KEY")
        self.public_key = langfuse_public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        self.langfuse_host = langfuse_host or os.getenv(
            "LANGFUSE_HOST", "https://cloud.langfuse.com"
        )
        if not (
            self.langfuse_host.startswith("http://")
            or self.langfuse_host.startswith("https://")
        ):
            # add http:// if unset, assume communicating over private network - e.g. render
            self.langfuse_host = "http://" + self.langfuse_host
        self.langfuse_release = os.getenv("LANGFUSE_RELEASE")
        self.langfuse_debug = os.getenv("LANGFUSE_DEBUG")
        self.langfuse_flush_interval = LangFuseLogger._get_langfuse_flush_interval(
            flush_interval
        )
        http_client = _get_httpx_client()
        self.langfuse_client = http_client.client

        parameters = {
            "public_key": self.public_key,
            "secret_key": self.secret_key,
            "host": self.langfuse_host,
            "release": self.langfuse_release,
            "debug": self.langfuse_debug,
            "flush_interval": self.langfuse_flush_interval,  # flush interval in seconds
            "httpx_client": self.langfuse_client,
        }
        self.langfuse_sdk_version: str = langfuse.version.__version__

        if Version(self.langfuse_sdk_version) >= Version("2.6.0"):
            parameters["sdk_integration"] = "litellm"
        self.Langfuse: Langfuse = self.safe_init_langfuse_client(parameters)

        # set the current langfuse project id in the environ
        # this is used by Alerting to link to the correct project
        try:
            project_id = self.Langfuse.client.projects.get().data[0].id
            os.environ["LANGFUSE_PROJECT_ID"] = project_id
        except Exception:
            project_id = None

        if os.getenv("UPSTREAM_LANGFUSE_SECRET_KEY") is not None:
            upstream_langfuse_debug = (
                str_to_bool(self.upstream_langfuse_debug)
                if self.upstream_langfuse_debug is not None
                else None
            )
            self.upstream_langfuse_secret_key = os.getenv(
                "UPSTREAM_LANGFUSE_SECRET_KEY"
            )
            self.upstream_langfuse_public_key = os.getenv(
                "UPSTREAM_LANGFUSE_PUBLIC_KEY"
            )
            self.upstream_langfuse_host = os.getenv("UPSTREAM_LANGFUSE_HOST")
            self.upstream_langfuse_release = os.getenv("UPSTREAM_LANGFUSE_RELEASE")
            self.upstream_langfuse_debug = os.getenv("UPSTREAM_LANGFUSE_DEBUG")
            self.upstream_langfuse = Langfuse(
                public_key=self.upstream_langfuse_public_key,
                secret_key=self.upstream_langfuse_secret_key,
                host=self.upstream_langfuse_host,
                release=self.upstream_langfuse_release,
                debug=(
                    upstream_langfuse_debug
                    if upstream_langfuse_debug is not None
                    else False
                ),
            )
        else:
            self.upstream_langfuse = None

    def safe_init_langfuse_client(self, parameters: dict) -> Langfuse:
        """
        Safely init a langfuse client if the number of initialized clients is less than the max

        Note:
            - Langfuse initializes 1 thread everytime a client is initialized.
            - We've had an incident in the past where we reached 100% cpu utilization because Langfuse was initialized several times.
        """
        from langfuse import Langfuse

        if litellm.initialized_langfuse_clients >= MAX_LANGFUSE_INITIALIZED_CLIENTS:
            raise Exception(
                f"Max langfuse clients reached: {litellm.initialized_langfuse_clients} is greater than {MAX_LANGFUSE_INITIALIZED_CLIENTS}"
            )
        langfuse_client = Langfuse(**parameters)
        litellm.initialized_langfuse_clients += 1
        verbose_logger.debug(
            f"Created langfuse client number {litellm.initialized_langfuse_clients}"
        )
        return langfuse_client

    @staticmethod
    def add_metadata_from_header(litellm_params: dict, metadata: dict) -> dict:
        """
        Adds metadata from proxy request headers to Langfuse logging if keys start with "langfuse_"
        and overwrites litellm_params.metadata if already included.

        For example if you want to append your trace to an existing `trace_id` via header, send
        `headers: { ..., langfuse_existing_trace_id: your-existing-trace-id }` via proxy request.
        """
        if litellm_params is None:
            return metadata

        if litellm_params.get("proxy_server_request") is None:
            return metadata

        if metadata is None:
            metadata = {}

        proxy_headers = (
            litellm_params.get("proxy_server_request", {}).get("headers", {}) or {}
        )

        for metadata_param_key in proxy_headers:
            if metadata_param_key.startswith("langfuse_"):
                trace_param_key = metadata_param_key.replace("langfuse_", "", 1)
                if trace_param_key in metadata:
                    verbose_logger.warning(
                        f"Overwriting Langfuse `{trace_param_key}` from request header"
                    )
                else:
                    verbose_logger.debug(
                        f"Found Langfuse `{trace_param_key}` in request header"
                    )
                metadata[trace_param_key] = proxy_headers.get(metadata_param_key)

        return metadata

    def log_event_on_langfuse(
        self,
        kwargs: dict,
        response_obj: Union[
            None,
            dict,
            EmbeddingResponse,
            ModelResponse,
            TextCompletionResponse,
            ImageResponse,
            TranscriptionResponse,
            RerankResponse,
            HttpxBinaryResponseContent,
        ],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
        level: str = "DEFAULT",
        status_message: Optional[str] = None,
    ) -> dict:
        """
        Logs a success or error event on Langfuse
        """
        try:
            verbose_logger.debug(
                f"Langfuse Logging - Enters logging function for model {kwargs}"
            )

            # set default values for input/output for langfuse logging
            input = None
            output = None

            litellm_params = kwargs.get("litellm_params", {})
            litellm_call_id = kwargs.get("litellm_call_id", None)
            metadata = (
                litellm_params.get("metadata", {}) or {}
            )  # if litellm_params['metadata'] == None
            metadata = self.add_metadata_from_header(litellm_params, metadata)
            optional_params = copy.deepcopy(kwargs.get("optional_params", {}))

            prompt = {"messages": kwargs.get("messages")}

            functions = optional_params.pop("functions", None)
            tools = optional_params.pop("tools", None)
            if functions is not None:
                prompt["functions"] = functions
            if tools is not None:
                prompt["tools"] = tools

            # langfuse only accepts str, int, bool, float for logging
            for param, value in optional_params.items():
                if not isinstance(value, (str, int, bool, float)):
                    try:
                        optional_params[param] = str(value)
                    except Exception:
                        # if casting value to str fails don't block logging
                        pass

            input, output = self._get_langfuse_input_output_content(
                kwargs=kwargs,
                response_obj=response_obj,
                prompt=prompt,
                level=level,
                status_message=status_message,
            )
            verbose_logger.debug(
                f"OUTPUT IN LANGFUSE: {output}; original: {response_obj}"
            )
            trace_id = None
            generation_id = None
            if self._is_langfuse_v2():
                trace_id, generation_id = self._log_langfuse_v2(
                    user_id=user_id,
                    metadata=metadata,
                    litellm_params=litellm_params,
                    output=output,
                    start_time=start_time,
                    end_time=end_time,
                    kwargs=kwargs,
                    optional_params=optional_params,
                    input=input,
                    response_obj=response_obj,
                    level=level,
                    litellm_call_id=litellm_call_id,
                )
            elif response_obj is not None:
                self._log_langfuse_v1(
                    user_id=user_id,
                    metadata=metadata,
                    output=output,
                    start_time=start_time,
                    end_time=end_time,
                    kwargs=kwargs,
                    optional_params=optional_params,
                    input=input,
                    response_obj=response_obj,
                )
            verbose_logger.debug(
                f"Langfuse Layer Logging - final response object: {response_obj}"
            )
            verbose_logger.info("Langfuse Layer Logging - logging success")

            return {"trace_id": trace_id, "generation_id": generation_id}
        except Exception as e:
            verbose_logger.exception(
                "Langfuse Layer Error(): Exception occured - {}".format(str(e))
            )
            return {"trace_id": None, "generation_id": None}

    def _get_langfuse_input_output_content(
        self,
        kwargs: dict,
        response_obj: Union[
            None,
            dict,
            EmbeddingResponse,
            ModelResponse,
            TextCompletionResponse,
            ImageResponse,
            TranscriptionResponse,
            RerankResponse,
            HttpxBinaryResponseContent,
        ],
        prompt: dict,
        level: str,
        status_message: Optional[str],
    ) -> Tuple[Optional[dict], Optional[Union[str, dict, list]]]:
        """
        Get the input and output content for Langfuse logging

        Args:
            kwargs: The keyword arguments passed to the function
            response_obj: The response object returned by the function
            prompt: The prompt used to generate the response
            level: The level of the log message
            status_message: The status message of the log message

        Returns:
            input: The input content for Langfuse logging
            output: The output content for Langfuse logging
        """
        input = None
        output: Optional[Union[str, dict, List[Any]]] = None
        if (
            level == "ERROR"
            and status_message is not None
            and isinstance(status_message, str)
        ):
            input = prompt
            output = status_message
        elif response_obj is not None and (
            kwargs.get("call_type", None) == "embedding"
            or isinstance(response_obj, litellm.EmbeddingResponse)
        ):
            input = prompt
            output = None
        elif response_obj is not None and isinstance(
            response_obj, litellm.ModelResponse
        ):
            input = prompt
            output = self._get_chat_content_for_langfuse(response_obj)
        elif response_obj is not None and isinstance(
            response_obj, litellm.HttpxBinaryResponseContent
        ):
            input = prompt
            output = "speech-output"
        elif response_obj is not None and isinstance(
            response_obj, litellm.TextCompletionResponse
        ):
            input = prompt
            output = self._get_text_completion_content_for_langfuse(response_obj)
        elif response_obj is not None and isinstance(
            response_obj, litellm.ImageResponse
        ):
            input = prompt
            output = response_obj.get("data", None)
        elif response_obj is not None and isinstance(
            response_obj, litellm.TranscriptionResponse
        ):
            input = prompt
            output = response_obj.get("text", None)
        elif response_obj is not None and isinstance(
            response_obj, litellm.RerankResponse
        ):
            input = prompt
            output = response_obj.results
        elif (
            kwargs.get("call_type") is not None
            and kwargs.get("call_type") == "_arealtime"
            and response_obj is not None
            and isinstance(response_obj, list)
        ):
            input = kwargs.get("input")
            output = response_obj
        elif (
            kwargs.get("call_type") is not None
            and kwargs.get("call_type") == "pass_through_endpoint"
            and response_obj is not None
            and isinstance(response_obj, dict)
        ):
            input = prompt
            output = response_obj.get("response", "")
        return input, output

    async def _async_log_event(
        self, kwargs, response_obj, start_time, end_time, user_id
    ):
        """
        Langfuse SDK uses a background thread to log events

        This approach does not impact latency and runs in the background
        """

    def _is_langfuse_v2(self):
        import langfuse

        return Version(langfuse.version.__version__) >= Version("2.0.0")

    def _log_langfuse_v1(
        self,
        user_id,
        metadata,
        output,
        start_time,
        end_time,
        kwargs,
        optional_params,
        input,
        response_obj,
    ):
        from langfuse.model import CreateGeneration, CreateTrace  # type: ignore

        verbose_logger.warning(
            "Please upgrade langfuse to v2.0.0 or higher: https://github.com/langfuse/langfuse-python/releases/tag/v2.0.1"
        )

        trace = self.Langfuse.trace(  # type: ignore
            CreateTrace(  # type: ignore
                name=metadata.get("generation_name", "litellm-completion"),
                input=input,
                output=output,
                userId=user_id,
            )
        )

        trace.generation(
            CreateGeneration(
                name=metadata.get("generation_name", "litellm-completion"),
                startTime=start_time,
                endTime=end_time,
                model=kwargs["model"],
                modelParameters=optional_params,
                prompt=input,
                completion=output,
                usage={
                    "prompt_tokens": response_obj.usage.prompt_tokens,
                    "completion_tokens": response_obj.usage.completion_tokens,
                },
                metadata=metadata,
            )
        )

    def _log_langfuse_v2(  # noqa: PLR0915
        self,
        user_id: Optional[str],
        metadata: dict,
        litellm_params: dict,
        output: Optional[Union[str, dict, list]],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        kwargs: dict,
        optional_params: dict,
        input: Optional[dict],
        response_obj,
        level: str,
        litellm_call_id: Optional[str],
    ) -> tuple:
        verbose_logger.debug("Langfuse Layer Logging - logging to langfuse v2")

        try:
            metadata = metadata or {}
            standard_logging_object: Optional[StandardLoggingPayload] = cast(
                Optional[StandardLoggingPayload],
                kwargs.get("standard_logging_object", None),
            )
            tags = (
                self._get_langfuse_tags(standard_logging_object=standard_logging_object)
                if self._supports_tags()
                else []
            )

            if standard_logging_object is None:
                end_user_id = None
                prompt_management_metadata: Optional[
                    StandardLoggingPromptManagementMetadata
                ] = None
            else:
                end_user_id = standard_logging_object["metadata"].get(
                    "user_api_key_end_user_id", None
                )

                prompt_management_metadata = cast(
                    Optional[StandardLoggingPromptManagementMetadata],
                    standard_logging_object["metadata"].get(
                        "prompt_management_metadata", None
                    ),
                )

            # Clean Metadata before logging - never log raw metadata
            # the raw metadata can contain circular references which leads to infinite recursion
            # we clean out all extra litellm metadata params before logging
            clean_metadata: Dict[str, Any] = {}
            if prompt_management_metadata is not None:
                clean_metadata[
                    "prompt_management_metadata"
                ] = prompt_management_metadata
            if isinstance(metadata, dict):
                for key, value in metadata.items():
                    # generate langfuse tags - Default Tags sent to Langfuse from LiteLLM Proxy
                    if (
                        litellm.langfuse_default_tags is not None
                        and isinstance(litellm.langfuse_default_tags, list)
                        and key in litellm.langfuse_default_tags
                    ):
                        tags.append(f"{key}:{value}")

                    # clean litellm metadata before logging
                    if key in [
                        "headers",
                        "endpoint",
                        "caching_groups",
                        "previous_models",
                    ]:
                        continue
                    else:
                        clean_metadata[key] = value

            # Add default langfuse tags
            tags = self.add_default_langfuse_tags(
                tags=tags, kwargs=kwargs, metadata=metadata
            )

            session_id = clean_metadata.pop("session_id", None)
            trace_name = cast(Optional[str], clean_metadata.pop("trace_name", None))
            trace_id = clean_metadata.pop("trace_id", litellm_call_id)
            existing_trace_id = clean_metadata.pop("existing_trace_id", None)
            update_trace_keys = cast(list, clean_metadata.pop("update_trace_keys", []))
            debug = clean_metadata.pop("debug_langfuse", None)
            mask_input = clean_metadata.pop("mask_input", False)
            mask_output = clean_metadata.pop("mask_output", False)

            clean_metadata = redact_user_api_key_info(metadata=clean_metadata)

            if trace_name is None and existing_trace_id is None:
                # just log `litellm-{call_type}` as the trace name
                ## DO NOT SET TRACE_NAME if trace-id set. this can lead to overwriting of past traces.
                trace_name = f"litellm-{kwargs.get('call_type', 'completion')}"

            if existing_trace_id is not None:
                trace_params: Dict[str, Any] = {"id": existing_trace_id}

                # Update the following keys for this trace
                for metadata_param_key in update_trace_keys:
                    trace_param_key = metadata_param_key.replace("trace_", "")
                    if trace_param_key not in trace_params:
                        updated_trace_value = clean_metadata.pop(
                            metadata_param_key, None
                        )
                        if updated_trace_value is not None:
                            trace_params[trace_param_key] = updated_trace_value

                # Pop the trace specific keys that would have been popped if there were a new trace
                for key in list(
                    filter(lambda key: key.startswith("trace_"), clean_metadata.keys())
                ):
                    clean_metadata.pop(key, None)

                # Special keys that are found in the function arguments and not the metadata
                if "input" in update_trace_keys:
                    trace_params["input"] = (
                        input if not mask_input else "redacted-by-litellm"
                    )
                if "output" in update_trace_keys:
                    trace_params["output"] = (
                        output if not mask_output else "redacted-by-litellm"
                    )
            else:  # don't overwrite an existing trace
                trace_params = {
                    "id": trace_id,
                    "name": trace_name,
                    "session_id": session_id,
                    "input": input if not mask_input else "redacted-by-litellm",
                    "version": clean_metadata.pop(
                        "trace_version", clean_metadata.get("version", None)
                    ),  # If provided just version, it will applied to the trace as well, if applied a trace version it will take precedence
                    "user_id": end_user_id,
                }
                for key in list(
                    filter(lambda key: key.startswith("trace_"), clean_metadata.keys())
                ):
                    trace_params[key.replace("trace_", "")] = clean_metadata.pop(
                        key, None
                    )

                if level == "ERROR":
                    trace_params["status_message"] = output
                else:
                    trace_params["output"] = (
                        output if not mask_output else "redacted-by-litellm"
                    )

            if debug is True or (isinstance(debug, str) and debug.lower() == "true"):
                if "metadata" in trace_params:
                    # log the raw_metadata in the trace
                    trace_params["metadata"]["metadata_passed_to_litellm"] = metadata
                else:
                    trace_params["metadata"] = {"metadata_passed_to_litellm": metadata}

            cost = kwargs.get("response_cost", None)
            verbose_logger.debug(f"trace: {cost}")

            clean_metadata["litellm_response_cost"] = cost
            if standard_logging_object is not None:
                clean_metadata["hidden_params"] = standard_logging_object[
                    "hidden_params"
                ]

            if (
                litellm.langfuse_default_tags is not None
                and isinstance(litellm.langfuse_default_tags, list)
                and "proxy_base_url" in litellm.langfuse_default_tags
            ):
                proxy_base_url = os.environ.get("PROXY_BASE_URL", None)
                if proxy_base_url is not None:
                    tags.append(f"proxy_base_url:{proxy_base_url}")

            api_base = litellm_params.get("api_base", None)
            if api_base:
                clean_metadata["api_base"] = api_base

            vertex_location = kwargs.get("vertex_location", None)
            if vertex_location:
                clean_metadata["vertex_location"] = vertex_location

            aws_region_name = kwargs.get("aws_region_name", None)
            if aws_region_name:
                clean_metadata["aws_region_name"] = aws_region_name

            if self._supports_tags():
                if "cache_hit" in kwargs:
                    if kwargs["cache_hit"] is None:
                        kwargs["cache_hit"] = False
                    clean_metadata["cache_hit"] = kwargs["cache_hit"]
                if existing_trace_id is None:
                    trace_params.update({"tags": tags})

            proxy_server_request = litellm_params.get("proxy_server_request", None)
            if proxy_server_request:
                proxy_server_request.get("method", None)
                proxy_server_request.get("url", None)
                headers = proxy_server_request.get("headers", None)
                clean_headers = {}
                if headers:
                    for key, value in headers.items():
                        # these headers can leak our API keys and/or JWT tokens
                        if key.lower() not in ["authorization", "cookie", "referer"]:
                            clean_headers[key] = value

            trace: StatefulTraceClient = self.Langfuse.trace(**trace_params)

            # Log provider specific information as a span
            log_provider_specific_information_as_span(trace, clean_metadata)

            # Log guardrail information as a span
            self._log_guardrail_information_as_span(
                trace=trace,
                standard_logging_object=standard_logging_object,
            )

            generation_id = None
            usage = None
            if response_obj is not None:
                if (
                    hasattr(response_obj, "id")
                    and response_obj.get("id", None) is not None
                ):
                    generation_id = litellm.utils.get_logging_id(
                        start_time, response_obj
                    )
                _usage_obj = getattr(response_obj, "usage", None)

                if _usage_obj:
                    usage = {
                        "prompt_tokens": _usage_obj.prompt_tokens,
                        "completion_tokens": _usage_obj.completion_tokens,
                        "total_cost": cost if self._supports_costs() else None,
                    }
            generation_name = clean_metadata.pop("generation_name", None)
            if generation_name is None:
                # if `generation_name` is None, use sensible default values
                # If using litellm proxy user `key_alias` if not None
                # If `key_alias` is None, just log `litellm-{call_type}` as the generation name
                _user_api_key_alias = cast(
                    Optional[str], clean_metadata.get("user_api_key_alias", None)
                )
                generation_name = (
                    f"litellm-{cast(str, kwargs.get('call_type', 'completion'))}"
                )
                if _user_api_key_alias is not None:
                    generation_name = f"litellm:{_user_api_key_alias}"

            if response_obj is not None:
                system_fingerprint = getattr(response_obj, "system_fingerprint", None)
            else:
                system_fingerprint = None

            if system_fingerprint is not None:
                optional_params["system_fingerprint"] = system_fingerprint

            generation_params = {
                "name": generation_name,
                "id": clean_metadata.pop("generation_id", generation_id),
                "start_time": start_time,
                "end_time": end_time,
                "model": kwargs["model"],
                "model_parameters": optional_params,
                "input": input if not mask_input else "redacted-by-litellm",
                "output": output if not mask_output else "redacted-by-litellm",
                "usage": usage,
                "metadata": log_requester_metadata(clean_metadata),
                "level": level,
                "version": clean_metadata.pop("version", None),
            }

            parent_observation_id = metadata.get("parent_observation_id", None)
            if parent_observation_id is not None:
                generation_params["parent_observation_id"] = parent_observation_id

            if self._supports_prompt():
                generation_params = _add_prompt_to_generation_params(
                    generation_params=generation_params,
                    clean_metadata=clean_metadata,
                    prompt_management_metadata=prompt_management_metadata,
                    langfuse_client=self.Langfuse,
                )
            if output is not None and isinstance(output, str) and level == "ERROR":
                generation_params["status_message"] = output

            if self._supports_completion_start_time():
                generation_params["completion_start_time"] = kwargs.get(
                    "completion_start_time", None
                )

            generation_client = trace.generation(**generation_params)

            return generation_client.trace_id, generation_id
        except Exception:
            verbose_logger.error(f"Langfuse Layer Error - {traceback.format_exc()}")
            return None, None

    @staticmethod
    def _get_chat_content_for_langfuse(
        response_obj: ModelResponse,
    ):
        """
        Get the chat content for Langfuse logging
        """
        if response_obj.choices and len(response_obj.choices) > 0:
            output = response_obj["choices"][0]["message"].json()
            return output
        else:
            return None

    @staticmethod
    def _get_text_completion_content_for_langfuse(
        response_obj: TextCompletionResponse,
    ):
        """
        Get the text completion content for Langfuse logging
        """
        if response_obj.choices and len(response_obj.choices) > 0:
            return response_obj.choices[0].text
        else:
            return None

    @staticmethod
    def _get_langfuse_tags(
        standard_logging_object: Optional[StandardLoggingPayload],
    ) -> List[str]:
        if standard_logging_object is None:
            return []
        return standard_logging_object.get("request_tags", []) or []

    def add_default_langfuse_tags(self, tags, kwargs, metadata):
        """
        Helper function to add litellm default langfuse tags

        - Special LiteLLM tags:
            - cache_hit
            - cache_key

        """
        if litellm.langfuse_default_tags is not None and isinstance(
            litellm.langfuse_default_tags, list
        ):
            if "cache_hit" in litellm.langfuse_default_tags:
                _cache_hit_value = kwargs.get("cache_hit", False)
                tags.append(f"cache_hit:{_cache_hit_value}")
            if "cache_key" in litellm.langfuse_default_tags:
                _hidden_params = metadata.get("hidden_params", {}) or {}
                _cache_key = _hidden_params.get("cache_key", None)
                if _cache_key is None and litellm.cache is not None:
                    # fallback to using "preset_cache_key"
                    _preset_cache_key = litellm.cache._get_preset_cache_key_from_kwargs(
                        **kwargs
                    )
                    _cache_key = _preset_cache_key
                tags.append(f"cache_key:{_cache_key}")
        return tags

    def _supports_tags(self):
        """Check if current langfuse version supports tags"""
        return Version(self.langfuse_sdk_version) >= Version("2.6.3")

    def _supports_prompt(self):
        """Check if current langfuse version supports prompt"""
        return Version(self.langfuse_sdk_version) >= Version("2.7.3")

    def _supports_costs(self):
        """Check if current langfuse version supports costs"""
        return Version(self.langfuse_sdk_version) >= Version("2.7.3")

    def _supports_completion_start_time(self):
        """Check if current langfuse version supports completion start time"""
        return Version(self.langfuse_sdk_version) >= Version("2.7.3")

    @staticmethod
    def _get_langfuse_flush_interval(flush_interval: int) -> int:
        """
        Get the langfuse flush interval to initialize the Langfuse client

        Reads `LANGFUSE_FLUSH_INTERVAL` from the environment variable.
        If not set, uses the flush interval passed in as an argument.

        Args:
            flush_interval: The flush interval to use if LANGFUSE_FLUSH_INTERVAL is not set

        Returns:
            [int] The flush interval to use to initialize the Langfuse client
        """
        return int(os.getenv("LANGFUSE_FLUSH_INTERVAL") or flush_interval)

    def _log_guardrail_information_as_span(
        self,
        trace: StatefulTraceClient,
        standard_logging_object: Optional[StandardLoggingPayload],
    ):
        """
        Log guardrail information as a span
        """
        if standard_logging_object is None:
            verbose_logger.debug(
                "Not logging guardrail information as span because standard_logging_object is None"
            )
            return

        guardrail_information = standard_logging_object.get(
            "guardrail_information", None
        )
        if guardrail_information is None:
            verbose_logger.debug(
                "Not logging guardrail information as span because guardrail_information is None"
            )
            return

        span = trace.span(
            name="guardrail",
            input=guardrail_information.get("guardrail_request", None),
            output=guardrail_information.get("guardrail_response", None),
            metadata={
                "guardrail_name": guardrail_information.get("guardrail_name", None),
                "guardrail_mode": guardrail_information.get("guardrail_mode", None),
                "guardrail_masked_entity_count": guardrail_information.get(
                    "masked_entity_count", None
                ),
            },
            start_time=guardrail_information.get("start_time", None),  # type: ignore
            end_time=guardrail_information.get("end_time", None),  # type: ignore
        )

        verbose_logger.debug(f"Logged guardrail information as span: {span}")
        span.end()


def _add_prompt_to_generation_params(
    generation_params: dict,
    clean_metadata: dict,
    prompt_management_metadata: Optional[StandardLoggingPromptManagementMetadata],
    langfuse_client: Any,
) -> dict:
    from langfuse import Langfuse
    from langfuse.model import (
        ChatPromptClient,
        Prompt_Chat,
        Prompt_Text,
        TextPromptClient,
    )

    langfuse_client = cast(Langfuse, langfuse_client)

    user_prompt = clean_metadata.pop("prompt", None)
    if user_prompt is None and prompt_management_metadata is None:
        pass
    elif isinstance(user_prompt, dict):
        if user_prompt.get("type", "") == "chat":
            _prompt_chat = Prompt_Chat(**user_prompt)
            generation_params["prompt"] = ChatPromptClient(prompt=_prompt_chat)
        elif user_prompt.get("type", "") == "text":
            _prompt_text = Prompt_Text(**user_prompt)
            generation_params["prompt"] = TextPromptClient(prompt=_prompt_text)
        elif "version" in user_prompt and "prompt" in user_prompt:
            # prompts
            if isinstance(user_prompt["prompt"], str):
                prompt_text_params = getattr(
                    Prompt_Text, "model_fields", Prompt_Text.__fields__
                )
                _data = {
                    "name": user_prompt["name"],
                    "prompt": user_prompt["prompt"],
                    "version": user_prompt["version"],
                    "config": user_prompt.get("config", None),
                }
                if "labels" in prompt_text_params and "tags" in prompt_text_params:
                    _data["labels"] = user_prompt.get("labels", []) or []
                    _data["tags"] = user_prompt.get("tags", []) or []
                _prompt_obj = Prompt_Text(**_data)  # type: ignore
                generation_params["prompt"] = TextPromptClient(prompt=_prompt_obj)

            elif isinstance(user_prompt["prompt"], list):
                prompt_chat_params = getattr(
                    Prompt_Chat, "model_fields", Prompt_Chat.__fields__
                )
                _data = {
                    "name": user_prompt["name"],
                    "prompt": user_prompt["prompt"],
                    "version": user_prompt["version"],
                    "config": user_prompt.get("config", None),
                }
                if "labels" in prompt_chat_params and "tags" in prompt_chat_params:
                    _data["labels"] = user_prompt.get("labels", []) or []
                    _data["tags"] = user_prompt.get("tags", []) or []

                _prompt_obj = Prompt_Chat(**_data)  # type: ignore

                generation_params["prompt"] = ChatPromptClient(prompt=_prompt_obj)
            else:
                verbose_logger.error(
                    "[Non-blocking] Langfuse Logger: Invalid prompt format"
                )
        else:
            verbose_logger.error(
                "[Non-blocking] Langfuse Logger: Invalid prompt format. No prompt logged to Langfuse"
            )
    elif (
        prompt_management_metadata is not None
        and prompt_management_metadata["prompt_integration"] == "langfuse"
    ):
        try:
            generation_params["prompt"] = langfuse_client.get_prompt(
                prompt_management_metadata["prompt_id"]
            )
        except Exception as e:
            verbose_logger.debug(
                f"[Non-blocking] Langfuse Logger: Error getting prompt client for logging: {e}"
            )
            pass

    else:
        generation_params["prompt"] = user_prompt

    return generation_params


def log_provider_specific_information_as_span(
    trace,
    clean_metadata,
):
    """
    Logs provider-specific information as spans.

    Parameters:
        trace: The tracing object used to log spans.
        clean_metadata: A dictionary containing metadata to be logged.

    Returns:
        None
    """

    _hidden_params = clean_metadata.get("hidden_params", None)
    if _hidden_params is None:
        return

    vertex_ai_grounding_metadata = _hidden_params.get(
        "vertex_ai_grounding_metadata", None
    )

    if vertex_ai_grounding_metadata is not None:
        if isinstance(vertex_ai_grounding_metadata, list):
            for elem in vertex_ai_grounding_metadata:
                if isinstance(elem, dict):
                    for key, value in elem.items():
                        trace.span(
                            name=key,
                            input=value,
                        )
                else:
                    trace.span(
                        name="vertex_ai_grounding_metadata",
                        input=elem,
                    )
        else:
            trace.span(
                name="vertex_ai_grounding_metadata",
                input=vertex_ai_grounding_metadata,
            )


def log_requester_metadata(clean_metadata: dict):
    returned_metadata = {}
    requester_metadata = clean_metadata.get("requester_metadata") or {}
    for k, v in clean_metadata.items():
        if k not in requester_metadata:
            returned_metadata[k] = v

    returned_metadata.update({"requester_metadata": requester_metadata})

    return returned_metadata