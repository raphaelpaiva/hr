"""Pydantic payload shapes for API handlers.

Business validation (blank names, missing devices) lives in the services and
raises domain ValidationError -> 400; these models only shape the body.
"""
from typing import List, Optional

from pydantic import BaseModel


class NamePayload(BaseModel):
  name: Optional[str] = None


class DevicesPayload(BaseModel):
  devices: Optional[List[str]] = None


class StartSessionPayload(DevicesPayload):
  name: Optional[str] = None


class DeleteSessionPayload(BaseModel):
  id: str


class AliasPayload(BaseModel):
  device_name: Optional[str] = None
  alias: Optional[str] = None
