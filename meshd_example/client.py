import asyncio
import logging
import os
import uuid

import dbussy as dbus
import ravel

from meshd_example.interfaces import (ApplicationInterface,
                                      ElementInterface,
                                      ProvisionAgentInterface)


class Application:
    PATH = '/com/silvair/%s'

    def __init__(self, bus, uuid, token=None):
        self.uuid = uuid
        self.token = int(token, 16) if token is not None else None
        self.path = self.PATH % self.uuid.hex
        self.bus = bus
        self.node = None

        self.application_interface = ApplicationInterface(self)
        self.provision_agent_interface = ProvisionAgentInterface(self)

        self.bus.register(self.path, fallback=False, interface=self.application_interface)
        self.bus.register(self.path, fallback=False, interface=self.provision_agent_interface)
        self.bus.object_added(self.path)

        self.elements = {}
        for index in range(2):
            path = os.path.join(self.path, str(index))
            self.elements[index] = (path, ElementInterface(self, index))

            self.bus.register(path, fallback=False, interface=ElementInterface(self, index))
            self.bus.object_added(path)

        self.mesh_service = self.bus['org.bluez.mesh']

        self.logger = logging.getLogger('Application')

    async def join(self):
        network = await self.mesh_service['/org/bluez/mesh'] \
            .get_async_interface('org.bluez.mesh.Network1')

        try:
            path, configuration = await network.Attach(self.path, self.token)
        except dbus.DBusError as ex:
            self.logger.error('Attach failed: %s', ex)
            self.token = None

        if self.token is None:
            self.logger.info('Joining')
            await network.Join(self.path, list(self.uuid.bytes))
            self.token = await self.application_interface.join_completed

            path, configuration = await network.Attach(self.path, self.token)

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


async def client(bus):
    application = Application(bus,
                              uuid.UUID('9c791e88-7acb-42e5-95ab-ab75cb74d774'),
                              token='9dbbbf60c5376e3')

    await application.join()

    await application.composition_data_get()

    while True:
        await asyncio.sleep(1)


def main():
    logging.basicConfig(level=logging.DEBUG)

    loop = asyncio.get_event_loop()

    bus = ravel.system_bus(managed_objects=True)
    bus.attach_asyncio(loop)

    loop.run_until_complete(client(bus))
