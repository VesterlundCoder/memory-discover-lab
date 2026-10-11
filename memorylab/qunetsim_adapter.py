"""QuNetSim 0.1.2 transport with a bounded custom QuTiP density backend.

Uses native Host/Network queues, quantum connections and ACKs. QuNetSim wall-
clock sleeps are scheduling machinery, NOT simulated physical storage time.
The shared logical trace supplies ages. No routing/queue-timing equivalence claimed.
"""
import threading
import numpy as np
from .common import optional_import, UnsupportedPhysics


class DensityBackend:
    """Small protocol-specific QuNetSim backend; no unsupported gate is simulated."""
    def __init__(self):
        self.qt = optional_import('qutip')
        self.hosts = {};self.groups = {};self.counter = 0;self.transfers = 0
        self.lock = threading.RLock()

    def start(self, **kwargs):
        pass

    def stop(self):
        with self.lock:
            self.groups.clear()

    def add_host(self, host):
        self.hosts[host.host_id] = host

    def create_qubit(self, host_id):
        with self.lock:
            self.counter += 1;key = str(self.counter)
            self.groups[key] = {'keys':[key], 'rho':self.qt.ket2dm(self.qt.basis(2,0))}
            return key

    def _merge(self, first, second):
        a,b = self.groups[first],self.groups[second]
        if a is b:
            return a
        keys = a['keys']+b['keys']
        if len(keys)>4:
            raise UnsupportedPhysics('QuNetSim density backend is bounded to 4 joint qubits')
        group = {'keys':keys, 'rho':self.qt.tensor(a['rho'],b['rho'])}
        for key in keys:self.groups[key]=group
        return group

    def custom_gate(self, qubit, gate):
        with self.lock:
            g=self.groups[qubit.qubit];index=g['keys'].index(qubit.qubit)
            op=self.qt.tensor([self.qt.Qobj(gate) if j==index else self.qt.qeye(2) for j in range(len(g['keys']))])
            g['rho']=op*g['rho']*op.dag()

    def H(self, qubit):
        self.custom_gate(qubit,np.array([[1,1],[1,-1]])/np.sqrt(2))

    def X(self, qubit):
        self.custom_gate(qubit,np.array([[0,1],[1,0]]))

    def Y(self, qubit):
        self.custom_gate(qubit,np.array([[0,-1j],[1j,0]]))

    def Z(self, qubit):
        self.custom_gate(qubit,np.diag([1,-1]))

    def cnot(self, qubit, target):
        from qutip_qip.operations import expand_operator
        with self.lock:
            g=self._merge(qubit.qubit,target.qubit)
            op=self.qt.Qobj([[1,0,0,0],[0,1,0,0],[0,0,0,1],[0,0,1,0]],dims=[[2,2],[2,2]])
            expanded=expand_operator(op,dims=[2]*len(g['keys']),targets=[g['keys'].index(qubit.qubit),g['keys'].index(target.qubit)])
            g['rho']=expanded*g['rho']*expanded.dag()

    def apply_superoperator(self,qubit,superop):
        with self.lock:
            g=self.groups[qubit.qubit];index=g['keys'].index(qubit.qubit)
            local=self.qt.Qobj(superop,dims=[[[2],[2]],[[2],[2]]],superrep='super')
            full=self.qt.super_tensor([local if j==index else self.qt.to_super(self.qt.qeye(2)) for j in range(len(g['keys']))])
            g['rho']=self.qt.vector_to_operator(full*self.qt.operator_to_vector(g['rho']))
            if abs(g['rho'].tr()-1)>1e-9 or np.linalg.eigvalsh(g['rho'].full()).min() < -1e-9:
                raise ValueError('Invalid QuNetSim density state after local channel')

    def joint_state(self,qubits):
        with self.lock:
            keys=[q.qubit for q in qubits];g=self.groups[keys[0]]
            if any(self.groups[k] is not g for k in keys):
                raise ValueError('Qubits do not share a density state')
            indices=[g['keys'].index(k) for k in keys]
            ordered=sorted(indices)
            reduced=g['rho'].ptrace(ordered)
            if indices!=ordered:
                reduced=reduced.permute([ordered.index(i) for i in indices])
            return reduced.full()

    def density_operator(self,qubit):
        return self.joint_state([qubit])

    def send_qubit_to(self,qubit,from_host_id,to_host_id):
        qubit.host=self.hosts[to_host_id];self.transfers+=1

    def release(self,qubit):
        with self.lock:
            if qubit.qubit not in self.groups:return
            g=self.groups[qubit.qubit];indices=[i for i,k in enumerate(g['keys']) if k!=qubit.qubit]
            remaining=[g['keys'][i] for i in indices]
            del self.groups[qubit.qubit]
            if remaining:
                new={'keys':remaining,'rho':g['rho'].ptrace(indices)}
                for key in remaining:self.groups[key]=new

    def measure(self,*args,**kwargs):
        raise UnsupportedPhysics('This density backend implements transport and channel application, not measurement protocols')


class QuNetSimSession:
    def __init__(self):
        from qunetsim.components import Host,Network
        self.backend=DensityBackend();self.network=Network.get_instance()
        if self.network.ARP:
            raise UnsupportedPhysics('Run the QuNetSim study in a fresh process')
        self.network.start(['A','B'],backend=self.backend)
        self.network.delay=0;self.network.packet_drop_rate=0
        self.left,self.right=(Host(x,backend=self.backend) for x in ['A','B'])
        self.left.add_connection('B');self.right.add_connection('A')
        self.left.delay=self.right.delay=0
        self.left.max_ack_wait=self.right.max_ack_wait=5
        self.left.start();self.right.start();self.network.add_hosts([self.left,self.right])

    def load_bell(self):
        from qunetsim.objects import Qubit
        a,b=Qubit(self.left),Qubit(self.left)
        a.H();a.cnot(b)
        qid,ack=self.left.send_qubit('B',b,await_ack=True)
        if not ack:raise TimeoutError('QuNetSim transport ACK timed out')
        received=self.right.get_data_qubit('A',q_id=qid,wait=5)
        if received is None:raise TimeoutError('QuNetSim did not deliver the quantum packet')
        if received.host.host_id!='B':raise ValueError('QuNetSim receiver ownership mismatch')
        return a,received

    def close(self):
        self.network.stop(True)
