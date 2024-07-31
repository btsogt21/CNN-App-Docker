# Pydantic imports
from pydantic import BaseModel, Field, field_validator

# Other imports
from typing import List
from re import compile

# Definiting pydantic models, setting types and constraints for request parameters, and adding
# validation logic to ensure that the request parameters are valid.
class TrainModelRequest(BaseModel):
    layers: int = Field(ge=1, le=3, description="Number of convolutional layers in the model")
    units: List[int] = Field(min_length = 1, max_length = 3)
    epochs: int = Field(ge=0, le=200)
    batchSize: int = Field(ge=1, le=512)
    optimizer: str = Field(
        ...,
        description = "Optimizer to use for training",
    )

    # SEtting extra to "forbid" ensures that the request will fail if any extra fields are present.
    class Config:
        extra = "forbid"
    
    # Field validators to enforce additional constraints on the request parameters. This one for making
    # sure that the size of the units list matches the number of layers.
    @field_validator('units')
    @classmethod
    def validate_units_length(cls, v, values):
        layers = values.data.get('layers')
        if layers is not None and len(v) != layers:
            raise ValueError(f"Number of units must match number of layers ({layers})")
        return v

    # This field validator ensures that units (nodes) are within a certain range.
    @field_validator('units')
    @classmethod
    def validate_units(cls, v):
        for unit in v:
            if unit < 1 or unit >1024:
                raise ValueError('Units must be between 1 and 1024')
        return v
    
    # This field validator ensures that the optimizer is one of the valid options.
    @field_validator('optimizer')
    @classmethod
    def validate_optimizer(cls, v):
        valid_optimizers = ['adam', 'sgd', 'rmsprop']  # Add or remove as needed
        if v.lower() not in valid_optimizers:
            raise ValueError(f"Optimizer must be one of: {', '.join(valid_optimizers)}")
        return v.lower()

# Defining a pydantic model for the response to the cancel training endpoint.
class CancelTaskRequest(BaseModel):
    task_id: str
    
    # Ensuring that the task ID is in the correct format.
    @field_validator('task_id')
    @classmethod
    def validate_task_id(cls, v, values):
        pattern = compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$')
        if not pattern.match(v):
            raise ValueError('Invalid task ID')
        return v

    # Setting extra to "forbid" ensures that the request will fail if any extra fields are present.
    class Config:
        extra = "forbid"