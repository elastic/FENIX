# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. See the NOTICE file distributed with
# this work for additional information regarding copyright
# ownership. Elasticsearch B.V. licenses this file to you under
# the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#	http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""YAML configuration loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a FENIX YAML run configuration."""
    config_path = Path(path).expanduser().resolve()
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Config must be a YAML mapping: {config_path}")

    if "technique" not in data:
        raise ValueError(f"Config missing required key 'technique': {config_path}")

    return data


def config_get(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Read a config value, accepting kebab-case or snake_case keys."""
    if key in data:
        return data[key]
    alt = key.replace("-", "_")
    if alt in data:
        return data[alt]
    alt = key.replace("_", "-")
    if alt in data:
        return data[alt]
    return default
