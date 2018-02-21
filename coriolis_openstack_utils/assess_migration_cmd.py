# Copyright 2018 Cloudbase Solutions Srl
# All Rights Reserved.

import argparse
import json
import math
import yaml
import xlsxwriter

from oslo_log import log as logging

from coriolis_openstack_utils import actions
from coriolis_openstack_utils import conf
from coriolis_openstack_utils import constants
from coriolis_openstack_utils import instances
from oslo_utils import units


# Setup logging:
logging.register_options(conf.CONF)
logging.setup(conf.CONF, 'coriolis')
LOG = logging.getLogger(__name__)

# Setup argument parsing:
PARSER = argparse.ArgumentParser(
    description="Coriolis Openstack Instance Metrics.")
PARSER.add_argument(
    "--config-file", metavar="CONF_FILE", dest="conf_file",
    help="Path to the config file.")
PARSER.add_argument(
    "--format", dest="format",
    choices=["yaml", "json", "excel"],
    default="json",
    help="the output format for the data, default is json")
PARSER.add_argument(
    "migrations", metavar="MIGRATION_ID", nargs="+")
PARSER.add_argument(
    "--excel-filepath",
    default="migration_assessment.xlsx",
    help="default filepath for excel format")


def write_excel(result_list, file_path):
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()
    name_col = 0
    worksheet.write(0, name_col, "VM Name")
    src_tenant_col = name_col + 1
    worksheet.write(0, src_tenant_col, "Source Tenant Name")
    dst_tenant_col = src_tenant_col + 1
    worksheet.write(0, dst_tenant_col, "Destination Tenant Name")
    image_size_col = dst_tenant_col + 1
    worksheet.write(0, image_size_col, "Glance Image Size(GB)")
    flavor_size_col = image_size_col + 1
    worksheet.write(0, flavor_size_col, "VM Flavor Size(GB)")
    volume_size_col = flavor_size_col + 1
    worksheet.write(0, volume_size_col, "VM Volumes(GB)")
    migr_time_col = volume_size_col + 1
    worksheet.write(0, migr_time_col, "VM Migration Time")

    row = 1
    for assessment_list in result_list:
        for assessment in assessment_list:
            for key, value in assessment.items():
                if key == "instance_name":
                    worksheet.write(row, name_col, value)
                elif key == "source_tenant_name":
                    worksheet.write(row, src_tenant_col, value)
                    worksheet.write(row, dst_tenant_col, value+"-Migrated")
                elif key == "storage":
                    if 'image' in value:
                        image_size = math.ceil(
                            value['image']['size_bytes'] / units.Gi)
                    else:
                        image_size = "deleted"
                    flavor_size = math.ceil(
                        value['flavor']['flavor_disk_size'] / units.Gi)
                    volume_list = [vol['size_bytes'] for
                                   vol in value['volumes']]
                    volumes_size = math.ceil(sum(volume_list) / units.Gi)
                    worksheet.write(row, image_size_col, image_size)
                    worksheet.write(row, flavor_size_col, flavor_size)
                    worksheet.write(row, volume_size_col, volumes_size)
                elif key == "migration":
                    migration_time = value['migration_time']
                    worksheet.write(row, migr_time_col, migration_time)
            row += 1
    workbook.close()


def main():
    args = PARSER.parse_args()
    conf.CONF(
        # NOTE: passing the whole of sys.argv[1:] will make
        # oslo_conf error out with urecognized arguments:
        ["--config-file", args.conf_file],
        project=constants.PROJECT_NAME,
        version=constants.PROJECT_VERSION)

    migration_ids = args.migrations
    source_client = conf.get_source_openstack_client()
    coriolis = conf.get_coriolis_client()
    result_list = []
    for migration_id in migration_ids:
        result = instances.get_migration_assessment(
            source_client, coriolis, migration_id)
        result_list.append(result)

    if args.format.lower() == "yaml":
        yaml_result = yaml.dump(
            result_list, default_flow_style=False, indent=4)
        print(yaml_result)
    elif args.format.lower() == "json":
        json_result = json.dumps(result_list, indent=4)
        print(json_result)
    elif args.format.lower() == "excel":
        write_excel(result_list, args.excel_filepath)
    else:
        raise ValueError("Undefinded output format.")


if __name__ == "__main__":
    main()
