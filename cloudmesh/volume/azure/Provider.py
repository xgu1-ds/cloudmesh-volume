from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.compute.models import DiskCreateOption
# from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.compute import ComputeManagementClient
from cloudmesh.common.Printer import Printer
from cloudmesh.common.console import Console
from cloudmesh.common.debug import VERBOSE
from cloudmesh.configuration.Config import Config
from cloudmesh.volume.VolumeABC import VolumeABC


# client = get_client_from_auth_file(ComputeManagementClient, auth_path=C:\Users\plj2861\Documents\AshleyPersonal\School\IndianaUniversity\CloudComputing\azure_credentials.json)


class Provider(VolumeABC):

    """The provider class is a category of objects, and in this case objects
    related to creating, deleting, and listing a volume, along with other
    volume related functions."""

    kind = "volume"

    sample = """
    cloudmesh:
      volume:
        azure:
          cm:
            active: true
            heading: Chameleon
            host: chameleoncloud.org
            label: chameleon
            kind: azure
            version: train
            service: compute
          credentials:
             AZURE_TENANT_ID: {tenantid}
             AZURE_SUBSCRIPTION_ID: {subscriptionid}
             AZURE_APPLICATION_ID: {applicationid}
             AZURE_SECRET_KEY: {secretkey}
             AZURE_REGION: westus
          default:
            size: Basic_A0
            volume_type: __DEFAULT__

    """


    volume_states = [
        'ACTIVE',
        'BUILDING',
        'DELETED',
        'ERROR',
        'HARD_REBOOT',
        'PASSWORD',
        'PAUSED',
        'REBOOT',
        'REBUILD',
        'RESCUED',
        'RESIZED',
        'REVERT_RESIZE',
        'SHUTOFF',
        'SOFT_DELETED',
        'STOPPED',
        'SUSPENDED',
        'UNKNOWN',
        'VERIFY_RESIZE'
    ]

    output = {

        "volume": {
            "sort_keys": ["cm.name"],
            "order": ["cm.name",
                      "cm.cloud",
                      "cm.kind",
                      "availability_zone",
                      "created_at",
                      "size",
                      "status",
                      "id",
                      "volume_type"
                      ],
            "header": ["Name",
                       "Cloud",
                       "Kind",
                       "Availability Zone",
                       "Created At",
                       "Size",
                       "Status",
                       "Id",
                       "Volume Type"
                       ],
        }
    }


    def __init__(self, name="azure", configuration=None, credentials=None):
        """
        Initializes the provider. The default parameters are read from the
        configuration file that is defined in yaml format.

        :param name: The name of the provider as defined in the yaml file
        :param configuration: The location of the yaml configuration file
        """
        # configuration = configuration if configuration is not None \
            # else CLOUDMESH_YAML_PATH

        conf = Config(configuration)["cloudmesh"]

        self.user = Config()["cloudmesh"]["profile"]["user"]

        self.spec = conf["volume"][name]
        self.cloud = name

        cred = self.spec["credentials"]
        self.default = self.spec["default"]
        self.cloudtype = self.spec["cm"]["kind"]
        super().__init__(name, configuration)

        # update credentials with the passed dict
        if credentials is not None:
            cred.update(credentials)

        VERBOSE(cred, verbose=10)

        if self.cloudtype != 'azure':
            Console.error("This class is meant for azure cloud")

        # ServicePrincipalCredentials related Variables to configure in
        # cloudmesh.yaml file

        # AZURE_APPLICATION_ID = '<Application ID from Azure Active Directory
        # App Registration Process>'

        # AZURE_SECRET_KEY = '<Secret Key from Application configured in
        # Azure>'

        # AZURE_TENANT_ID = '<Directory ID from Azure Active Directory
        # section>'

        credentials = ServicePrincipalCredentials(
            client_id=cred['AZURE_APPLICATION_ID'],
            #application and client id are same thing
            secret=cred['AZURE_SECRET_KEY'],
            tenant=cred['AZURE_TENANT_ID']
        )

        subscription = cred['AZURE_SUBSCRIPTION_ID']

        # Management Clients
        self.compute_client = ComputeManagementClient(
            credentials, subscription)


    def Print(self, data, output=None, kind=None):
        """
        Print out the result dictionary as table(by default) or json.

        :param data: dic returned from volume functions
        :param kind: kind of provider
        :param output: "table" or "json"
        :return:
        """
        order = self.output["volume"]['order']
        header = self.output["volume"]['header']
        print(Printer.flatwrite(data,
                                sort_keys=["name"],
                                order=order,
                                header=header,
                                output=output,
                                )
              )


    def update_dict(self, results):
        """
        This function adds a cloudmesh cm dict to each dict in the list
        elements. Libcloud returns an object or list of objects with the dict
        method. This object is converted to a dict. Typically this method is used
        internally.

        :param results: the original dicts.
        :param kind: for some kinds special attributes are added. This includes
                     key, vm, image, flavor.
        :return: The list with the modified dicts
        """

        if results is None:
            return None

        d = []

        for entry in results:
            print("entry", entry)
            volume_name = entry['name']
            if "cm" not in entry:
                entry['cm'] = {}

            entry["cm"].update({
                "cloud": self.cloud,
                "kind": "volume",
                "name": volume_name,
            })
            d.append(entry)
        return d


    # def _get_resource_group(self):
    #     groups = self.resource_client.resource_groups
    #     if groups.check_existence(self.GROUP_NAME):
    #         return groups.get(self.GROUP_NAME)
    #     else:
    #         # Create or Update Resource groupCreating new public IP
    #         Console.info('Creating Azure Resource Group')
    #         res = groups.create_or_update(self.GROUP_NAME,
    #                                       {'location': self.LOCATION})
    #         Console.info('Azure Resource Group created: ' + res.name)
    #         return res
    #
    #
    # # Azure Resource Group
    # self.GROUP_NAME = self.default["resource_group"]


    def create(self, **kwargs):
        """
        This function creates a disk. It returns result to list the new disk.

        :param LOCATION (string): datacenter region
        :param GROUP_NAME (string): name of resource group
        :return: result
        """
        GROUP_NAME = 'cloudmesh'
        LOCATION = 'eastus'
        disk_creation = self.compute_client.disks.create_or_update(
            GROUP_NAME,
            "cloudmesh-os-disk",
            {
                'location': LOCATION,
                'disk_size_gb': 1,
                'creation_data': {
                    'create_option': 'Empty'
                }
            }
        )
        # return after create
        results = disk_creation.result().as_dict()
        result = self.update_dict([results])
        return result


    def delete (self, NAMES=None):
        """
        This function deletes a disk. It returns result to list outcome of
        disk deletion, which is nothing since the disk is now gone.

        :param LOCATION (string): datacenter region
        :param GROUP_NAME (string): name of resource group
        :return: result
        """
        GROUP_NAME = 'cloudmesh'
        LOCATION = 'eastus'
        disk_deletion = self.compute_client.disks.delete(
            GROUP_NAME,
            "cloudmesh-os-disk",
            {
                'location': LOCATION
            }
        )
        # return after deleting
        results = disk_deletion.result()
        result = self.update_dict(results)
        return result


#not working, figure out why
    def list(self, **kwargs):
        """
        This function lists all disks.

        :return: result
        """
        disk_list = self.compute_client.disks.list()
        return disk_list

    # def create_nic(network_client):
    #     """Create a Network Interface for a VM.
    #     """
    #     LOCATION = 'eastus'
    #     GROUP_NAME = 'cloudmesh'
    #     async_vnet_creation = network_client.virtual_networks.create_or_update(
    #         GROUP_NAME,
    #         'vnet',
    #         {
    #             'location': LOCATION,
    #             'address_space': {
    #                 'address_prefixes': ['10.0.0.0/16']
    #             }
    #         }
    #     )
    #     async_vnet_creation.wait()


    def attach(self, NAMES=None, vm=None):
        """
        This function attaches a given volume to a given instance

        :param NAMES: Names of Volumes
        :param vm: Instance name
        :return: Dictionary of volumes
        """
        LOCATION = 'eastus'
        GROUP_NAME = 'cloudmesh'
        # VM_NAME = 'ashthorn-vm-3'
        VM_NAME = vm
        self.vms = self.compute_client.virtual_machines
        disk_creation = self.compute_client.disks.create_or_update(
            GROUP_NAME,
            "test",
            {
                'location': LOCATION,
                'disk_size_gb': 1,
                'creation_data': {
                    'create_option': 'Empty'
                }
            }
        )
        luns = [
                  "0",
                  "1",
                  "2",
                  "3",
                  "4",
                  "5"]
        data_disk = disk_creation.result()
        virtual_machine = self.vms.get(GROUP_NAME, VM_NAME)
        disk_attach = virtual_machine.storage_profile.data_disks.append({
            'lun': luns,
            'name': data_disk.name,
            'create_option': 'Attach',
            'managed_disk': {
                'id': data_disk.id
            }
        })
        updated_vm = self.vms.create_or_update(
            GROUP_NAME,
            VM_NAME,
            virtual_machine
        )
        # return after attaching
        results = updated_vm.result().as_dict()
        result = self.update_dict([results])
        return result


    def detach(self, NAME=None):
        """
        This function detaches a single disk from a vm. I did not find any
        documentation about deleting multiple disks from a vm at the same
        time. It returns result to list the updated disk.

        :param VM_NAME (string): name of vm
        :param LOCATION (string): datacenter region
        :param GROUP_NAME (string): name of resource group
        :return: result
        """
        LOCATION = 'eastus'
        GROUP_NAME = 'cloudmesh'
        VM_NAME = 'ashthorn-vm-3' #need to fix
        self.vms = self.compute_client.virtual_machines
        virtual_machine = self.vms.get(GROUP_NAME, VM_NAME)
        data_disks = virtual_machine.storage_profile.data_disks
        data_disks[:] = [
            disk for disk in data_disks if disk.name != 'test']
        async_vm_update = self.compute_client.virtual_machines.create_or_update(
            GROUP_NAME,
            VM_NAME,
            virtual_machine
        )
        # return after detaching
        results = async_vm_update.result().as_dict()
        result = self.update_dict([results])
        return result


    def status(self, NAME=None):
        """
        TODO: missing

        :param NAME:
        :return:
        """
        print("update me")


    def add_tag(self,**kwargs):
        """
        TODO: missing

        :param kwargs:
        :return:
        """
        LOCATION = 'eastus'
        GROUP_NAME = 'cloudmesh'
        async_vm_update = self.compute_client.disks.create_or_update(
            GROUP_NAME,
            "test",
            {
                'location': LOCATION,
                'disk_size_gb': 1,
                'creation_data': {
                    'create_option': 'Empty',
                },
                'tags': {
                    'volumeproject': 'test',
                    'tag2': 'test2'
                }
            }
        )
        async_vm_update.wait()
        # return after adding tags
        results = async_vm_update.result().as_dict()
        result = self.update_dict([results])
        return result


    def migrate(self,
                name=None,
                from_vm=None,
                to_vm=None):
        """
        TODO: missing

        :param name:
        :param from_vm:
        :param to_vm:
        :return:
        """
        print("update me")


    def sync(self,
             from_volume=None,
             to_volume=None):
        """
        TODO: missing

        :param from_volume:
        :param to_volume:
        :return:
        """
        print("update me")



#every cloud needs a function called search (per Xin) such as describe or
# list volume