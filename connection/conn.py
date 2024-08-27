import asyncio
from slixmpp import ClientXMPP
import sys
import threading

# Forzar el uso de SelectorEventLoop en Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class XMPPClient(ClientXMPP):
    def __init__(self, jid, password, auth_callback):
        super().__init__(jid=jid, password=password)
        self.auth_callback = auth_callback
        self.authenticated = False
        self.contact_jid = None  # Para almacenar el JID del contacto que se desea agregar
        self.contacts_callback = None  # Callback para manejar la lista de contactos
        self.jid = jid  # Guardar el JID del usuario para excluirlo de la lista de contactos
        self.set_handlers()

    def set_handlers(self):
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("failed_auth", self.failed_auth)
        self.add_event_handler("presence_subscribed", self.on_subscribed)
        self.add_event_handler("presence_subscribe", self.on_subscribe)

    async def start(self, event):
        print("Conexión exitosa: Autenticado con el servidor XMPP.")
        self.send_presence(pshow="chat", pstatus="Connected")
        await self.get_roster()
        self.authenticated = True
        self.auth_callback(True)

        # Si hay un contacto para agregar, enviar la solicitud de suscripción
        if self.contact_jid:
            await self.add_contact(self.contact_jid)

        # Obtener y devolver todos los contactos después de la autenticación
        if self.contacts_callback:
            contacts = self.get_all_contacts()
            self.contacts_callback(contacts)

    def get_all_contacts(self):
        """Devuelve una lista con todos los contactos del usuario, excluyendo el propio JID."""
        contacts = []
        for jid in self.client_roster.keys():
            if jid != self.jid:  # Excluir el propio JID
                contacts.append(jid)
        return contacts

    def failed_auth(self, event):
        print("Fallo en la autenticación: No se pudo autenticar con el servidor XMPP.")
        self.authenticated = False
        self.auth_callback(False)
        self.disconnect()

    async def add_contact(self, contact_jid):
        """Envío de solicitud de suscripción."""
        self.send_presence_subscription(pto=contact_jid)
        print(f"Solicitud de suscripción enviada a {contact_jid}")
        
        # Actualizar la lista de contactos en tiempo real
        await self.get_roster()
        if self.contacts_callback:
            contacts = self.get_all_contacts()
            self.contacts_callback(contacts)

    def on_subscribed(self, presence):
        """Confirmación de la suscripción."""
        print(f"Ahora estás suscrito a {presence['from'].bare}")

    def on_subscribe(self, presence):
        """Responder a las solicitudes de suscripción entrantes."""
        self.send_presence_subscription(pto=presence['from'].bare)
        print(f"Solicitud de suscripción de {presence['from'].bare} aceptada")

def start_xmpp(jid, password, auth_callback, contacts_callback=None):
    def run_xmpp():
        loop = asyncio.new_event_loop()  # Crear un nuevo bucle de eventos
        asyncio.set_event_loop(loop)  # Establecer este bucle como el bucle de eventos del hilo actual

        xmpp = XMPPClient(jid, password, auth_callback)
        xmpp.contacts_callback = contacts_callback  # Asignar el callback de contactos
        xmpp.connect(disable_starttls=True, use_ssl=False)
        
        loop.run_until_complete(xmpp.process(forever=False))  # Ejecutar el bucle de eventos hasta que se complete el proceso

    thread = threading.Thread(target=run_xmpp)
    thread.start()

def add_contact(jid, password, contact_jid, auth_callback):
    def run_xmpp_with_contact():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        xmpp = XMPPClient(jid, password, auth_callback)
        xmpp.contact_jid = contact_jid  # Asignar el JID del contacto a agregar
        xmpp.connect(disable_starttls=True, use_ssl=False)
        
        loop.run_until_complete(xmpp.process(forever=False))

    thread = threading.Thread(target=run_xmpp_with_contact)
    thread.start()
