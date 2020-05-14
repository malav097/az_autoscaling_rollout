#!/usr/bin/python3
from azure.mgmt.compute import ComputeManagementClient
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.network import NetworkManagementClient
import subprocess
import time
import sys

''' If you are going to use this in production please retrieve credentials from a secure storage. Never hard-code 
credentials into code. For more information about authentication methods please visit:
https://docs.microsoft.com/en-us/azure/developer/python/azure-sdk-authenticate '''

default_client_id = ###
default_secret = ###
tenant_id = ###
subscription_id = ###

class az_rollout:
    def __init__(self, tenant_id, subscription_id, vmss, resource_group, appgwy):
        self.tenant_id = tenant_id
        self.subscription_id = subscription_id
        self.vmss = vmss
        self.resource_group = resource_group
        self.appgwy = appgwy
        try:
            self.client_id = sys.argv[4]
        except:
            print("Client_id for AZ user not set, setting default.")
            self.client_id = default_client_id
            pass
        try:
            self.secret = sys.argv[5]
        except:
            print("Secret for AZ user not set, setting default.")
            self.secret = default_secret
            pass
        self.credentials = ServicePrincipalCredentials(
            client_id = self.client_id,
            secret = self.secret,
            tenant = self.tenant_id
        )

    def get_vms(self, client):
        """ 
        Method used to obtain a list of the vms running inside the scale set.

            Parameters:
                'client' parameter must be a ComputeManagementClient class instance from azure.mgmt.compute module.

        """
        vms = client.virtual_machine_scale_set_vms.list(self.resource_group, self.vmss)
        id_list = list()
        for vm in vms:
            id = "{}".format(vm.id)
            id_list.append(id[-1])
        return id_list

    def policy_check(self, client):
        '''
        Method used to verify the scale in policy, it must be "OldestVM" or the
        execution will stop.

            Parameters:
                'client' parameter must be a ComputeManagementClient class instance from azure.mgmt.compute module.
        '''
        print("Verifying scale-in-policy")
        vmss_info = client.virtual_machine_scale_sets.get(self.resource_group, self.vmss)
        policy_info = vmss_info.scale_in_policy.rules[0]
        if policy_info != 'OldestVM':
            #### print invalid policy ####
            print('Invalid Scale-in policy. Please set the polity to OldestVM, current policy is: ' + policy_info)
            quit()
        else:
            print('Valid Scale-in policy: ' + policy_info)

    def scale_commnad(self, size):
        """ 
        Method to execute scaling using the az-cli command.

            Parameters:
                'size' parameter must be a (str) instance. It indicates the number of the new instance capacity.
        """
        print("New vmss capacity: " + str(size))
        command = "az vmss scale --name " + self.vmss + " --new-capacity " + size + " --subscription "+ self.subscription_id + " --resource-group " + self.resource_group
        print("Executing command... " + command)
        output = subprocess.Popen(command, shell=True, executable='/bin/bash', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = output.stdout.read().decode('utf-8')

    def health_check(self, client):
        """
        Method used to execute a healtcheck over the scale set instances using the attached application gateway.
        
            Parameters:
                'client' parameter must be a NetworkManagementClient class instance from azure.mgmt.network module.
        """
        print("Getting into the healthcheck while loop...")
        def check_health_loop(vmshealth):
            for vm in vmshealth:
                if vm['health'] != 'Healthy':
                    return False
                else:
                    print(vm['health'])
                    pass
            return True

        print("Vms health state:")
        healthcheck = client.application_gateways.backend_health(self.resource_group, self.appgwy)
        healthcheck = healthcheck.result()
        healthcheck = healthcheck.as_dict()
        vmshealth = healthcheck['backend_address_pools'][0]['backend_http_settings_collection'][0]['servers']
        health_eval = check_health_loop(vmshealth)
        print("Healthchecks results: " + str(health_eval))
        retries = 0
        while health_eval == False and retries < 10:
            retries += 1
            healthcheck = client.application_gateways.backend_health(self.resource_group, self.appgwy)
            healthcheck = healthcheck.result()
            healthcheck = healthcheck.as_dict()
            vmshealth = healthcheck['backend_address_pools'][0]['backend_http_settings_collection'][0]['servers']
            health_eval = check_health_loop(vmshealth)
            print(health_eval)
            time.sleep(60)
        if retries == 10:
            print('Maximun number of healthcheck attempts reached.')
            quit()

def main():
    vmss = sys.argv[1]
    appgwy = sys.argv[2]
    resource_group = sys.argv[3]
    #Creating az_rollout instance.   
    rollout = az_rollout(tenant_id, subscription_id, vmss, resource_group, appgwy)
    #Obtaining credentials.
    credentials = rollout.credentials
    #Creating ComputeManagementClient instance.
    client_C = ComputeManagementClient(credentials, subscription_id)
    #Executing policy check.
    rollout.policy_check(client_C)
    #Obtaining vmss running vms list.
    id_list = rollout.get_vms(client_C)
    #Calculating the original scale set vm capacity.
    original_size = str(len(id_list))
    #Getting the new scale vm capacity size by multiplying the original size by 2.
    new_size = str(len(id_list) * 2)
    #Executing the scale command.
    rollout.scale_commnad(new_size)
    #Creating NetworkManagementClient instance.
    client_N = NetworkManagementClient(credentials, subscription_id)
    #Executing healthcheck and returning the scale set to the original vm capacity.
    rollout.health_check(client_N)
    rollout.scale_commnad(original_size)

if __name__ == '__main__':
    main()
    
