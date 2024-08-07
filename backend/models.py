from pydantic import BaseModel, Field, field_validator
from typing import List
from re import compile, match

class TrainModelRequest(BaseModel):
    layers: int = Field(ge=1, le=3, description="Number of convolutional layers in the model")
    units: List[int] = Field(min_length = 1, max_length = 3)
    epochs: int = Field(ge=0, le=200)
    batchSize: int = Field(ge=1, le=512)
    optimizer: str

    class Config:
        extra = "forbid"
    
    @field_validator('units')
    @classmethod
    def validate_units_length(cls, v, values):
        layers = values.data.get('layers')
        if layers is not None and len(v) != layers:
            raise ValueError(f"Number of units must match number of layers ({layers})")
        return v

    @field_validator('units')
    @classmethod
    def validate_units(cls, v):
        for unit in v:
            if unit < 1 or unit >1024:
                raise ValueError('Units must be between 1 and 1024')
        return v
    
class CancelTaskRequest(BaseModel):
    task_id: str
    
    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v, values):
        pattern = compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
        if not pattern.match(v):
            raise ValueError('Invalid task ID')
        return v


    class Config:
        extra = "forbid"