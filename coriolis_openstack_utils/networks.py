def get_network(openstack_client, name_or_id):
    return openstack_client.neutron.find_resource(
        'network', name_or_id)
