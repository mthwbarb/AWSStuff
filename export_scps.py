import boto3
import json

#Get all OU's including nested ones
def get_all_ous(parent_id=None): 
    org_client = boto3.client('organizations')
    ous = []
    
    paginator = org_client.get_paginator('list_organizational_units_for_parent')
    for page in paginator.paginate(ParentId=parent_id or org_client.list_roots()['Roots'][0]['Id']):
        for ou in page['OrganizationalUnits']:
            ous.append(ou)
            ous.extend(get_all_ous(ou['Id']))  # Recursively get nested OUs
    
    return ous
#List all of the SCP's, even unattached ones
def get_all_scps():
    org_client = boto3.client('organizations')
    scps = []
    
    paginator = org_client.get_paginator('list_policies')
    for page in paginator.paginate(Filter='SERVICE_CONTROL_POLICY'):
        scps.extend(page['Policies'])
    
    return scps

#Get the content of SCP
def get_policy_content(policy_id):
    org_client = boto3.client('organizations')
    response = org_client.describe_policy(PolicyId=policy_id)
    return json.loads(response['Policy']['Content'])

#List the attached SCP's for each OU
def get_attached_scps(target_id):
    org_client = boto3.client('organizations')
    attached_policies = []
    
    paginator = org_client.get_paginator('list_policies_for_target')
    for page in paginator.paginate(TargetId=target_id, Filter='SERVICE_CONTROL_POLICY'):
        attached_policies.extend(page['Policies'])
    
    return attached_policies

#Export all to a json file
def export_scps_to_json():
    ous = get_all_ous()
    all_scps = get_all_scps()
    
    org_structure = {}
    
    for ou in ous:
        ou_id = ou['Id']
        ou_name = ou['Name']
        attached_scps = get_attached_scps(ou_id)
        
        ou_policies = {}
        for scp in attached_scps:
            policy_id = scp['Id']
            policy_name = scp['Name']
            policy_content = get_policy_content(policy_id)
            
            ou_policies[policy_name] = {
                'Id': policy_id,
                'Content': policy_content
            }
        
        org_structure[ou_name] = {
            'Id': ou_id,
            'Policies': ou_policies
        }
    
    # Add SCPs not attached to any OU
    unattached_scps = {}
    for scp in all_scps:
        if not any(scp['Id'] in ou_data['Policies'] for ou_data in org_structure.values()):
            policy_id = scp['Id']
            policy_name = scp['Name']
            policy_content = get_policy_content(policy_id)
            
            unattached_scps[policy_name] = {
                'Id': policy_id,
                'Content': policy_content
            }
    
    if unattached_scps:
        org_structure['Unattached_SCPs'] = unattached_scps
    
    with open('organization_scps.json', 'w') as f:
        json.dump(org_structure, f, indent=2)

if __name__ == '__main__':
    export_scps_to_json()
    print("Organization structure and SCPs have been exported to 'organization_scps.json'")
