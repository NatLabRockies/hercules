
# Running Hercules

It is recommended to run Hercules using a python runscript. The typical pattern is:

```python
from hercules.hercules_model import HerculesModel

# Initialize the Hercules model
hmodel = HerculesModel("hercules_input.yaml")

# Define your controller class
class MyController:
    def __init__(self, h_dict):
        # Initialize with the prepared h_dict
        pass
    
    def step(self, h_dict):
        # Implement your control logic here
        # Set power setpoints, etc.
        return h_dict

# Assign the controller to the Hercules model
hmodel.assign_controller(MyController(hmodel.h_dict))

# Run the simulation
hmodel.run()
```

See the example runscripts in the `examples/` directory for complete examples.




