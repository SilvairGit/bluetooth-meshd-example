import asyncio
import logging

import dbussy as dbus
import ravel
import os

@ravel.interface(ravel.INTERFACE.SERVER, name='org.bluez.mesh.Element1')
class ElementInterface:
    def __init__(self, application, index, location=0, models=None, vendor_models=None):
        self.application = application
        self.index = index
        self.location = location
        self.models = models or []
        self.vendor_models = vendor_models or []
        self.logger = logging.getLogger('ElementInterface.%i' % index)

    @ravel.propgetter(name='VendorModels',
                      type='a(qq)',
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def get_models(self):
        return self.vendor_models

    @ravel.method(name='MessageReceived', in_signature='qqbay', out_signature='')
    def message_received(self, source, key_index, subscription, data):
        self.logger.info('Message from %04x [key %04x]: %s', source, key_index, bytes(data).hex())

    @ravel.method(name='UpdateModelConfiguration', in_signature='qa{sv}', out_signature='')
    def update_model_configuration(self, model_id, configuration):
        self.logger.info('Update configuration of model %04x', model_id)
        self.logger.info('  bindings: %s', configuration['Bindings'])
        self.logger.info('  publication period: %s', configuration['PublicationPeriod'])
        self.logger.info('  vendor: %s', configuration['VendorId'])

    @ravel.propgetter(name='Index',
                      type='y',
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def get_index(self):
        return self.index

    @ravel.propgetter(name='Location',
                      type='q',
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def get_location(self):
        return self.location

    @ravel.propgetter(name='Models',
                      type='aq',
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def get_vendor_models(self):
        return self.models


@ravel.interface(ravel.INTERFACE.SERVER, name='org.bluez.mesh.ProvisionAgent1')
class ProvisionAgentInterface:
    def __init__(self, application):
        self.application = application
        self.logger = logging.getLogger('ProvisionAgentInterface')

    @ravel.method(name='PrivateKey', in_signature='', out_signature='ay')
    def private_key(self):
        return []

    @ravel.method(name='PublicKey', in_signature='', out_signature='ay')
    def public_key(self):
        return []

    @ravel.method(name='DisplayString', in_signature='s', out_signature='')
    def display_string(self, value):
        pass

    @ravel.method(name='DisplayNumeric', in_signature='su', out_signature='')
    def display_numeric(self, type, number):
        pass

    @ravel.method(name='PromptNumeric', in_signature='s', out_signature='u')
    def prompt_numeric(self, type):
        return 0

    @ravel.method(name='PromptStatic', in_signature='s', out_signature='ay')
    def prompt_static(self, type):
        return []

    @ravel.method(name='Cancel', in_signature='', out_signature='')
    def cancel(self):
        pass

    @ravel.propgetter(name='Capabilities',
                      type='as',
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def get_capabilities(self):
        return []

    @ravel.propgetter(name='OutOfBandInfo',
                      type='as',
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def out_of_band_info(self):
        return []

    @ravel.propgetter(name='URI',
                      type='s',
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def uri(self):
        return ''


@ravel.interface(ravel.INTERFACE.SERVER, name='org.bluez.mesh.Application1')
class ApplicationInterface:
    def __init__(self, application):
        self.application = application
        self.logger = logging.getLogger('ApplicationInterface')
        self.join_completed = asyncio.Future()
        self.token_path = '~/.cache/bluetooth-meshd-example/'

    @ravel.method(name='JoinComplete', in_signature='t', out_signature='')
    async def join_complete(self, token):
        self.logger.info('Join complete: %x', token)
        self.join_completed.set_result(token)

        if not os.path.exists(self.token_path):
            os.makedirs(self.token_path)

        with open(self.token_path + 'token.txt', 'w') as file:
            file.write("%x" % token)

    @ravel.method(name='JoinFailed', in_signature='s', out_signature='')
    async def join_failed(self, reason):
        self.logger.error('Join failed: %s', reason)
        self.join_completed.set_exception(Exception(reason))

    @ravel.propgetter(name='CompanyID',
                      type='q', #dbus.BasicType(dbus.TYPE.UINT16),
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def get_company_id(self):
        return 0x0136

    @ravel.propgetter(name='ProductID',
                      type='q', #dbus.BasicType(dbus.TYPE.UINT16),
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def get_product_id(self):
        return 0x255

    @ravel.propgetter(name='VersionID',
                      type='q', #dbus.BasicType(dbus.TYPE.UINT16),
                      change_notification=dbus.Introspection.PROP_CHANGE_NOTIFICATION.INVALIDATES)
    def get_version_id(self):
        return 0x0001
