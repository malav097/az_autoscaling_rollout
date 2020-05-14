# az_autoscaling_rollout.py
Rolling update Azure scale set instances to be used in CI/CD Pipelines 

I develop this simple script to be used in a Jenkins Job. 

### Functionality
The script calculates the scale set instance capacity and multiply it by 2, then set the new instance capacity and do a 
heatlh check using the Application Gateway module from Azure, once all instances are healthy it returns the scale set to 
the original instance capacity.

### Parameters

vmss name: Virtual machine scale set name

appgw:  Application Gateway name

resource group: Rersource group Name

Usage: 

az_autoscaling_rollout.py [vmss] [appgwy] [resource group]

