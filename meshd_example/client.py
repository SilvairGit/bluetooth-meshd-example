import asyncio
import logging
import json
import os
import uuid

import dbussy as dbus
import ravel

from secrets import token_hex
from meshd_example.interfaces import (ApplicationInterface,
                                      ElementInterface,
                                      ProvisionAgentInterface)

class TokenRing:
    PATH = '~/.cache/bluetooth-mesh-example'

    @property
    def path(self):
        return os.path.expanduser(self.PATH)

    def __init__(self):
        self.__tokens = {}

        os.makedirs(self.path, exist_ok=True)
        for filename in os.listdir(self.path):
            with open(os.path.join(self.path, filename), 'r') as f:
                self.__tokens[uuid.UUID(filename)] = int(f.readline(), 16)

    def get(self, uuid):
        return self.__tokens.get(uuid, 0)

    def set(self, uuid, token):
        self.__tokens[uuid] = token

        with open(os.path.join(self.path, str(uuid)), 'w') as f:
            f.write('%x' % token)


class Application:
    PATH = '/com/silvair/%s'

    def __init__(self, bus, uuid):
        self.token_ring = TokenRing()

        self.uuid = uuid
        self.path = self.PATH % self.uuid.hex
        self.bus = bus
        self.node = None

        self.application_interface = ApplicationInterface(self)
        self.provision_agent_interface = ProvisionAgentInterface(self)

        self.bus.register(self.path, fallback=False, interface=self.application_interface)
        self.bus.register(self.path, fallback=False, interface=self.provision_agent_interface)
        self.bus.object_added(self.path)

        self.elements = {}
        for index in range(1):
            path = os.path.join(self.path, str(index))
            self.elements[index] = (path, ElementInterface(self, index, models=[0]))

            self.bus.register(path, fallback=False, interface=ElementInterface(self, index))
            self.bus.object_added(path)

        self.mesh_service = self.bus['org.bluez.mesh']

        self.logger = logging.getLogger('Application')

    @property
    def token(self):
        return self.token_ring.get(self.uuid)

    @token.setter
    def token(self, value):
        self.token_ring.set(self.uuid, value)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.token_ring.set(self.uuid, self.token)

    async def attach(self):
        self.logger.info('Attach with %x', self.token)
        path, configuration = await self.network_interface.Attach(self.path, self.token)
        return path, configuration

    async def import_local_node(self):
        json_data = dict(
            cid='%04x' % self.application_interface.get_company_id(),
            pid='%04x' % self.application_interface.get_product_id(),
            vid='%04x' % self.application_interface.get_version_id(),
            IVindex=0,
            IVupdate=0,
            unicastAddress='%04x' % 0x0042,
            deviceKey="56325fd145f3d5eee1b82136dc3e1454",
            elements={
                index: dict(
                    location='%04x' % interface.get_location(),
                    models={ '%04x' % i: {} for i in interface.get_models() },
                )
                for index, (path, interface) in self.elements.items()
            },
            netKeys={
                0: dict(
                    keyRefresh=0,
                    key="9a17cbec499b4151ae045ac6f259bf43"
                ),
            },
            # appKeys={
            #     0: "68d3c3363bae45e2a2fd20de1b8614ed"
            # },
        )
        self.logger.info(json.dumps(json_data))
        token, = await self.network_interface.ImportLocalNode(json.dumps(json_data),
                                                             list(self.uuid.bytes))
        return token

    async def join(self):
        self.network_interface = await self.mesh_service['/org/bluez/mesh'] \
            .get_async_interface('org.bluez.mesh.Network1')

        try:
            path, configuration = await self.attach()
        except dbus.DBusError as ex:
            self.logger.error('Attach failed: %s, trying to import node', ex)
            self.token = await self.import_local_node()
            path, configuration = await self.attach()

        # if self.token is None:
        #     self.logger.info('Joining')
        #     await network.Join(self.path, list(self.uuid.bytes))
        #     self.token = await self.application_interface.join_completed
        #
        #     path, configuration = await network.Attach(self.path, self.token)

        self.node = await self.mesh_service[path] \
            .get_async_interface('org.bluez.mesh.Node1')
        self.logger.info('Attached to node %s, configuration: %s', path, configuration)

    async def composition_data_get(self):
        # Send from local element #0
        element_path = self.elements[0][0]

        # Send to local node
        destination = 0x0042

        # Use local device key
        key_index = 0x7fff

        # Config Composition Data Get, page = 0xff
        data = [0x80, 0x08, 0xff]

        await self.node.Send(element_path, destination, key_index, data)

    async def attention(self, destination, timer=3):
        # Send from local element #0
        element_path = self.elements[0][0]

        # Use application key #0
        key_index = 0

        # Health Attention Set
        data = [0x80, 0x05, timer]

        await self.node.Send(element_path, destination, key_index, data)


async def client(bus):
    with Application(bus, uuid.UUID('9c791e88-7acb-42e5-95ab-ab75cb74d774')) as application:
        await application.join()

        while True:
            # await application.attention(1080)
            await asyncio.sleep(5)


def main():
    logging.basicConfig(level=logging.DEBUG)

    loop = asyncio.get_event_loop()

    bus = ravel.system_bus(managed_objects=True)
    bus.attach_asyncio(loop)

    loop.run_until_complete(client(bus))
