from coriolis_openstack_utils import subnets
from coriolis_openstack_utils import conf

CONF = conf.CONF

def get_network(openstack_client, name_or_id):
    return openstack_client.neutron.find_resource(
        'network', name_or_id)


def list_networks(openstack_client, tenant_id, filters={}):
    return openstack_client.neutron.list_networks(
        tenant_id=tenant_id, project_id=tenant_id, **filters)['networks']


def create_network(openstack_client, body):
    network_id = openstack_client.neutron.create_network(
        {'network': body})['network']['id']
    return network_id


def get_body(openstack_client, network_id):
    src_network = get_network(openstack_client, network_id)
    relevant_keys = set([
        'admin_state_up', 'dns_domain', 'port_security_enabled',
        'router:external', 'shared', 'vlan_transparent', 'is_default',
        'subnets'])

    body = {k: v for k, v in src_network.items() if k in relevant_keys}
    # 'provider:physical_network'
    network_type_map = CONF.destination.new_network_type
    physical_network_map = CONF.destination.new_physical_network
    # 'provider:network_type'
    if network_type_map.get(src_network['provider:physical_network']):
        body['provider:physical_network'] = network_type_map.get(
            src_network['provider:physical_network'])

    if physical_network_map.get(src_network['provider:network_type']):
        body['provider:network_type'] = physical_network_map.get(
            src_network['provider:network_type'])

    body['availability_zone_hints'] = src_network['availability_zones']

    return body

def check_network_similarity(
        src_network, dest_network, source_client, destination_client):

    relevant_keys = set([
        'admin_state_up', 'dns_domain', 'mtu',
        'port_security_enabled', 'provider:physical_network'
        'provider:network_type', 'router:external', 'shared',
        'vlan_transparent', 'is_default', 'availability_zones', 'subnets'])
    src_availability_zones = set(src_network.get('availability_zones'))
    dest_availability_zones = set(dest_network.get('availability_zones'))
    conflict_keys = set()
    if src_availability_zones == dest_availability_zones:
        conflict_keys.add('availability_zones')

    network_type_map = CONF.destination.new_network_type
    physical_network_map = CONF.destination.new_physical_network

    for k in src_network:
        if k in relevant_keys:
            if k == 'provider:network_type':
                if network_type_map.get(src_network[k]) == dest_network.get(k):
                    conflict_keys.add(k)
            elif k == 'provider:physical_network':
                if physical_network_map.get(
                        src_network[k]) == dest_network.get(k):
                    conflict_keys.add(k)
            elif src_network[k] == dest_network.get(k):
                conflict_keys.add(k)

    src_relevant_keys = set(src_network.keys()).intersection(relevant_keys)

    src_subnets = [subnets.get_subnet(source_client, subnet_id) for
                   subnet_id in src_network['subnets']]

    dest_subnets = [subnets.get_subnet(destination_client, subnet_id) for
                    subnet_id in src_network['subnets']]

    similar_subnets = []
    for src_subnet in src_subnets:
        for dest_subnet in dest_subnets:
            if subnets.check_subnet_similarity(src_subnet, dest_subnet):
                similar_subnets.append(src_subnet)
                break

    if len(similar_subnets) == len(src_subnets):
        conflict_keys.add('subnets')

    return src_relevant_keys == conflict_keys
