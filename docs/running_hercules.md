
# Running Hercules

It is recommended to run Hercules using a python runscript. The typical pattern follows the FLORIS convention:

```python
from hercules import HerculesModel

# Define your controller class
class MyController:
    def __init__(self, h_dict):
        # Initialize with the prepared h_dict
        self.h_dict = h_dict
    
    def step(self, h_dict):
        # Implement your control logic here
        # Set power setpoints, etc.
        return h_dict

# Initialize and run the Hercules model
hmodel = HerculesModel("hercules_input.yaml", MyController)
hmodel.run()
```

See the example runscripts in the `examples/` directory for complete examples.




