* Saving the order of operations discussion from original readme*



# Order of operations

### Initialization

1. Instantiate the component modules, which sets the intial conditions

2. Run get_outputs, which sets the initial outputs
    
3. Establish the helics connection to AMRwind (?)


### Main run: for $k = 0, 1, 2, 3, \dots$

1. Compute control actions in controller, [i.e. $u_k = h(y_k, d_k)$]

2. Record all signals for time step $k$.

3. Update state in component [$x_{k+1} = f(x_k, u_k, d_k)$] and output in component [$y_{k+1} = g(x_{k+1})$]

4. Update state and output in helics/AMRwind, possibly using components from component (TODO: what ordering should be used there?)
    [$x_{k+1} = f(x_k, u_k, d_k)$, $y_{k+1} = g(x_{k+1})$]

