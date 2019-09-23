# ======================================================================
# Azure-Discovery
# Get Azure resources and create inventory documentation in Confluence using API
#
# 1. Connect to Azure
# 2. Get information about resources
# 3. Create Confluence documentation using API
#
# Author:szymon@circlekeurope.com
# Date Created: 2019-09-17
# ======================================================================

# For use with MIA
from msrestazure.azure_active_directory import MSIAuthentication


# For use wih SP
from azure.common.credentials import ServicePrincipalCredentials


# Imports
import os
import csv
from azure.mgmt.resource import ResourceManagementClient, SubscriptionClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from msrestazure.azure_exceptions import CloudError
from atlassian import Confluence
from datetime import date


#Authentication credentials setup
#Fisrt try to authenticate using MIA


sp_error = True
mia_error = True

print("Connecting to Azure.")


#Authentication using MSI
#Use MIA in production
try:
    credentials = MSIAuthentication()
    mia_error = False

except:
    print("Azure Managed Identity is not set up for this machine.")
    print("Trying to use Service Pricipal connection.")
    mia_error = True


#Authentication using SP
if mia_error == True:
    try:
        credentials = ServicePrincipalCredentials(
            client_id=os.environ['AZURE_CLIENT_ID'],
            secret=os.environ['AZURE_CLIENT_SECRET'],
            tenant=os.environ['AZURE_TENANT_ID']
        )
        subscription_id = os.environ['AZURE_SUBSCRIPTION_ID']
        sp_error = False
    except:
        print("Azure Service Principal variables are not set.")
        sp_error = True


#Quit if nothing works
if sp_error == True and mia_error == True:
    print("No Service Principal or Managed Identity Access authentication possible.\nPlease check you credentials...")
    exit(1)


#Get OS variables for Confluence API
confluence_api_error = True

confluence_api_key  = os.environ['CONFLUENCE_API_KEY']
confluence_server   = os.environ['CONFLUENCE_SERVER']
confluence_username = os.environ['CONFLUENCE_USERNAME']

try:
    confluence = Confluence(
    url=confluence_server,
    username=confluence_username,
    password=confluence_api_key)
    confluence_api_error = False
except:
    confluence_api_error = True


if confluence_api_error == True:
    print("Missing os variables for Confluence API: CONFLUENCE_API_KEY,CONFLUENCE_USERNAME,CONFLUENCE_SERVER")
    exit(2)
 

#Create output variables
output_name = ""
output_application = ""
output_environment = ""
output_application = ""
output_owner=""
output_project = ""
output_subscription_name = ""
output_resource_group = ""
output_location = ""
output_address_space = ""
output_subnets = ""
putput_peerings=""


# Build Confluene body
today = date.today()
post_body=''


# Create a Subscription Client
subscription_client = SubscriptionClient(credentials)

for subscriptions in subscription_client.subscriptions.list():
    print(subscriptions.display_name)
    subscription_name = subscriptions.display_name
    subscription_id = subscriptions.subscription_id
    output_subscription_name = subscription_name
    body=''
    body+='<h2>Subscription: ' + subscription_name + '</h2>'
    body+='<table><colgroup><col /><col /></colgroup><tbody>'
    body+='<tr>'
    body+='<th>Network Name</th>'
    body+='<th>Address Space</th>'
    body+='<th>Subnets</th>'
    body+='<th>Peerings</th>'
    body+='<th>Resource Group</th>'
    body+='<th>Location</th>'
    body+='</tr>'


# Create a Resource Management client

    resource_client = ResourceManagementClient(credentials, subscription_id)
    vnet_count=0

    for resource_group in resource_client.resource_groups.list():
        resource_group_name = resource_group.name
        print("Subscription:" + subscription_name + " Resource Group:" + resource_group_name)
        output_resource_group = resource_group.name

        network_client = NetworkManagementClient(credentials,subscription_id)

    
        for vnet in network_client.virtual_networks.list(resource_group_name):
            vnet_count+=1
            
            output_name = vnet.name
            output_location = vnet.location
            output_address_space=""
            output_subnets=""
            output_peerings=""
            #print(vnet.address_space.address_prefixes)
            for address in vnet.address_space.address_prefixes:
                output_address_space+='<p>' + address + '</p> '

            for subnet in vnet.subnets:
                output_subnets+='<p>' + subnet.name + ' ' + subnet.address_prefix + '</p> '
            
            for peer in vnet.virtual_network_peerings:
                output_peerings+='<p>' + peer.name + '</p><p>Status:' + peer.peering_state + '</p> '
            
            
            tags = vnet.tags

            if tags != None:
                if "Application" in tags:
                    output_application = tags["Application"]
                else:
                    output_application=""
                if "Owner" in tags:
                    output_owner = tags["Owner"]
                else:
                    output_owner=""
                if "Environment" in tags:
                    output_environment = tags["Environment"]
                else:
                    output_environment=""
                if "Project" in tags:
                    output_project = tags["Project"]
                else:
                    output_project=""

            body+='<tr>'
                
            body+='<td>' + output_name + '</td>'
            body+='<td>' + output_address_space +  '</td>'
            body+='<td>' + output_subnets + '</td>'
            body+='<td>' + output_peerings + '</td>'
            body+='<td>' + output_resource_group +  '</td>'
            body+='<td>' + output_location.capitalize() +  '</td>'
            body+='</tr>'

    body+='</tbody></table>'
    body+='<p></p>'
    
    if vnet_count == 0:
        print("No Vnets in subscription:" + subscription_name)
    else:
        post_body+=body
    
post_body+='<p>Azure Automated Inventory - Virtual Networks </p>'
post_body+='<p>Last discovery execution date :' + str(today)  +  '</p>'

#print (body)
#status = confluence.create_page(space='DCS',parent_id=1463911167,title="Azure Virtual Machines",body=body)


status = confluence.update_page(page_id=1465024702,title="Azure Virtual Networks",body=post_body)
print(status)

