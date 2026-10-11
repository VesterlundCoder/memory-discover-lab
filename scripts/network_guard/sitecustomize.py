"""Test-only outbound socket denial; loopback is allowed for local server tests."""
import os
if os.environ.get('WQ_BLOCK_EXTERNAL_NETWORK')=='1':
    import socket
    _connect=socket.socket.connect
    _getaddrinfo=socket.getaddrinfo
    allowed={'localhost','127.0.0.1','::1'}
    def connect(self,address):
        if isinstance(address,tuple) and address[0] not in allowed:
            raise PermissionError('External network disabled for reproduction test: '+str(address[0]))
        return _connect(self,address)
    def getaddrinfo(host,*args,**kwargs):
        if host not in allowed:
            raise PermissionError('External DNS disabled for reproduction test: '+str(host))
        return _getaddrinfo(host,*args,**kwargs)
    socket.socket.connect=connect
    socket.getaddrinfo=getaddrinfo
