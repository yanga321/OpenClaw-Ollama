#!/usr/bin/env python3
# =============================================================================
# Swarm Connector - Distributed AI Computing Protocol
# =============================================================================
# Features:
#   - OTG-to-OTG peer discovery
#   - Mesh networking for collective inference
#   - Compute marketplace with blockchain credits
#   - Federated learning across swarm
#   - Load balancing and task distribution
# =============================================================================

import json
import uuid
import socket
import threading
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('SwarmConnector')


@dataclass
class PeerNode:
    """Represents a peer node in the swarm"""
    node_id: str
    ip_address: str
    port: int
    device_type: str
    available_ram_gb: float
    available_compute: float  # Percentage
    models_available: List[str]
    reputation_score: float = 1.0
    last_seen: str = ""
    
    def __post_init__(self):
        if not self.last_seen:
            self.last_seen = datetime.now().isoformat()


@dataclass
class ComputeTask:
    """Represents a distributed compute task"""
    task_id: str
    task_type: str  # 'inference', 'training', 'embedding'
    payload: Dict
    required_compute: float
    priority: int = 5
    created_at: str = ""
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Dict] = None
    assigned_nodes: List[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if self.assigned_nodes is None:
            self.assigned_nodes = []


@dataclass
class ComputeCredit:
    """Blockchain-style compute credit"""
    credit_id: str
    owner: str
    amount: float
    earned_at: str = ""
    source: str = ""  # 'computation', 'storage', 'bandwidth'
    transaction_hash: str = ""
    
    def __post_init__(self):
        if not self.earned_at:
            self.earned_at = datetime.now().isoformat()


class SwarmConnector:
    """
    Distributed computing protocol for OTG drive mesh networks.
    
    Enables:
    - Multiple OTG drives to connect and form ad-hoc mesh networks
    - Collective inference by splitting large models across devices
    - Compute marketplace where users earn credits by sharing idle resources
    - Federated learning without centralizing data
    """
    
    def __init__(self, node_name: str = "default_node", 
                 otg_root: str = "user_data"):
        self.node_id = self._generate_node_id()
        self.node_name = node_name
        self.otg_root = Path(otg_root)
        
        # Network configuration
        self.host_ip = "0.0.0.0"
        self.port = 8765
        self.broadcast_port = 8766
        self.discovery_interval = 30  # seconds
        
        # Peer management
        self.peers: Dict[str, PeerNode] = {}
        self.active_tasks: Dict[str, ComputeTask] = {}
        self.completed_tasks: List[ComputeTask] = []
        
        # Compute credits wallet
        self.credits: List[ComputeCredit] = []
        self.wallet_file = self.otg_root / "blockchain_wallet" / "compute_credits.json"
        
        # Server socket
        self.server_socket = None
        self.running = False
        
        # Load existing wallet
        self._load_wallet()
        
        logger.info(f"Swarm Connector initialized (Node ID: {self.node_id})")
    
    def _generate_node_id(self) -> str:
        """Generate unique node ID based on hardware fingerprint"""
        # In production: Use actual hardware identifiers
        # Here: Use random UUID
        return f"node_{uuid.uuid4().hex[:12]}"
    
    def _load_wallet(self):
        """Load compute credits from wallet file"""
        if self.wallet_file.exists():
            try:
                with open(self.wallet_file, 'r') as f:
                    data = json.load(f)
                    self.credits = [
                        ComputeCredit(**credit) for credit in data.get('credits', [])
                    ]
                logger.info(f"Loaded wallet with {len(self.credits)} credits")
            except Exception as e:
                logger.error(f"Failed to load wallet: {e}")
                self.credits = []
        else:
            # Initialize empty wallet
            self._save_wallet()
            logger.info("Created new wallet")
    
    def _save_wallet(self):
        """Save compute credits to wallet file"""
        self.wallet_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'node_id': self.node_id,
            'last_updated': datetime.now().isoformat(),
            'credits': [asdict(credit) for credit in self.credits]
        }
        
        with open(self.wallet_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def start_discovery(self):
        """Start peer discovery via UDP broadcast"""
        logger.info("Starting peer discovery...")
        
        # Create broadcast socket
        broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        broadcast_socket.settimeout(5)
        
        def broadcast_presence():
            """Broadcast our presence to the network"""
            while self.running:
                message = json.dumps({
                    'type': 'discovery',
                    'node_id': self.node_id,
                    'node_name': self.node_name,
                    'ip': self._get_local_ip(),
                    'port': self.port,
                    'timestamp': datetime.now().isoformat()
                })
                
                try:
                    broadcast_socket.sendto(
                        message.encode(), 
                        ('<broadcast>', self.broadcast_port)
                    )
                except Exception as e:
                    logger.debug(f"Broadcast error: {e}")
                
                time.sleep(self.discovery_interval)
        
        # Start broadcast thread
        broadcast_thread = threading.Thread(target=broadcast_presence, daemon=True)
        broadcast_thread.start()
        
        # Listen for other peers
        listen_thread = threading.Thread(
            target=self._listen_for_peers, 
            args=(broadcast_socket,), 
            daemon=True
        )
        listen_thread.start()
        
        logger.info("Peer discovery started")
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def _listen_for_peers(self, sock: socket.socket):
        """Listen for discovery messages from other peers"""
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                message = json.loads(data.decode())
                
                if message.get('type') == 'discovery':
                    node_id = message.get('node_id')
                    
                    # Don't add ourselves
                    if node_id == self.node_id:
                        continue
                    
                    # Create or update peer
                    peer = PeerNode(
                        node_id=node_id,
                        ip_address=message.get('ip', addr[0]),
                        port=message.get('port', self.port),
                        device_type='mobile',
                        available_ram_gb=4.0,  # Placeholder
                        available_compute=100.0,
                        models_available=['phi3-mini'],
                        last_seen=datetime.now().isoformat()
                    )
                    
                    self.peers[node_id] = peer
                    logger.info(f"Discovered peer: {node_id} at {peer.ip_address}")
                    
            except socket.timeout:
                pass
            except Exception as e:
                logger.debug(f"Discovery error: {e}")
    
    def start_server(self):
        """Start TCP server for peer communication"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host_ip, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"Swarm server listening on {self.host_ip}:{self.port}")
            
            # Accept connections in separate thread
            accept_thread = threading.Thread(target=self._accept_connections, daemon=True)
            accept_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.running = False
    
    def _accept_connections(self):
        """Accept incoming peer connections"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                logger.info(f"Accepted connection from {addr}")
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, addr),
                    daemon=True
                )
                client_thread.start()
                
            except Exception as e:
                if self.running:
                    logger.error(f"Connection error: {e}")
    
    def _handle_client(self, client_socket: socket.socket, addr: tuple):
        """Handle communication with a connected client"""
        try:
            # Receive message
            data = client_socket.recv(4096)
            if not data:
                return
            
            message = json.loads(data.decode())
            msg_type = message.get('type')
            
            logger.info(f"Received {msg_type} from {addr}")
            
            # Route message based on type
            if msg_type == 'task_request':
                self._handle_task_request(client_socket, message)
            elif msg_type == 'task_result':
                self._handle_task_result(client_socket, message)
            elif msg_type == 'credit_transfer':
                self._handle_credit_transfer(client_socket, message)
            elif msg_type == 'status_query':
                self._send_status(client_socket)
            
        except Exception as e:
            logger.error(f"Client handling error: {e}")
        finally:
            client_socket.close()
    
    def _handle_task_request(self, client_socket: socket.socket, message: Dict):
        """Handle incoming compute task request"""
        task_data = message.get('task', {})
        
        task = ComputeTask(
            task_id=task_data.get('task_id', str(uuid.uuid4())),
            task_type=task_data.get('task_type', 'inference'),
            payload=task_data.get('payload', {}),
            required_compute=task_data.get('required_compute', 1.0),
            priority=task_data.get('priority', 5)
        )
        
        logger.info(f"Received task: {task.task_id} ({task.task_type})")
        
        # Process task (in production, this would use actual AI models)
        result = self._execute_task(task)
        
        # Send result back
        response = {
            'type': 'task_result',
            'task_id': task.task_id,
            'status': 'completed',
            'result': result,
            'credits_charged': 0.1  # Example charge
        }
        
        client_socket.send(json.dumps(response).encode())
        
        # Award credits
        self._award_credits(0.1, 'computation', task.task_id)
    
    def _execute_task(self, task: ComputeTask) -> Dict:
        """Execute a compute task (placeholder implementation)"""
        logger.info(f"Executing task {task.task_id}")
        
        # Simulate computation
        time.sleep(0.1)
        
        # Placeholder result
        return {
            'output': 'Task completed successfully',
            'computation_time': 0.1,
            'node_id': self.node_id
        }
    
    def _handle_task_result(self, client_socket: socket.socket, message: Dict):
        """Handle task result from peer"""
        task_id = message.get('task_id')
        result = message.get('result')
        
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = 'completed'
            task.result = result
            self.completed_tasks.append(task)
            
            logger.info(f"Task {task_id} completed by peer")
    
    def _handle_credit_transfer(self, client_socket: socket.socket, message: Dict):
        """Handle compute credit transfer"""
        amount = message.get('amount', 0)
        source = message.get('source', 'transfer')
        
        if amount > 0:
            self._award_credits(amount, source, message.get('transaction_id', ''))
            
            response = {'status': 'accepted', 'amount': amount}
            client_socket.send(json.dumps(response).encode())
    
    def _award_credits(self, amount: float, source: str, transaction_id: str):
        """Award compute credits to wallet"""
        credit = ComputeCredit(
            credit_id=str(uuid.uuid4()),
            owner=self.node_id,
            amount=amount,
            source=source,
            transaction_hash=transaction_id
        )
        
        self.credits.append(credit)
        self._save_wallet()
        
        logger.info(f"Awarded {amount} credits from {source}")
    
    def _send_status(self, client_socket: socket.socket):
        """Send node status to requester"""
        status = {
            'type': 'status_response',
            'node_id': self.node_id,
            'node_name': self.node_name,
            'peers_count': len(self.peers),
            'active_tasks': len(self.active_tasks),
            'total_credits': sum(c.amount for c in self.credits),
            'uptime': datetime.now().isoformat()
        }
        
        client_socket.send(json.dumps(status).encode())
    
    def distribute_task(self, task: ComputeTask) -> bool:
        """
        Distribute a task across the swarm.
        
        Args:
            task: The compute task to distribute
            
        Returns:
            True if task was successfully distributed
        """
        if not self.peers:
            logger.warning("No peers available for task distribution")
            return False
        
        # Select best peer based on availability and reputation
        best_peer = None
        best_score = 0
        
        for peer_id, peer in self.peers.items():
            if peer.available_compute >= task.required_compute:
                score = peer.reputation_score * peer.available_compute
                if score > best_score:
                    best_score = score
                    best_peer = peer
        
        if not best_peer:
            logger.warning("No suitable peer found for task")
            return False
        
        # Send task to selected peer
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((best_peer.ip_address, best_peer.port))
            
            message = {
                'type': 'task_request',
                'task': asdict(task)
            }
            
            peer_socket.send(json.dumps(message).encode())
            
            # Store task reference
            self.active_tasks[task.task_id] = task
            task.assigned_nodes.append(best_peer.node_id)
            
            logger.info(f"Task {task.task_id} assigned to {best_peer.node_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to distribute task: {e}")
            return False
    
    def get_swarm_statistics(self) -> Dict:
        """Get swarm network statistics"""
        total_compute = sum(p.available_compute for p in self.peers.values())
        total_ram = sum(p.available_ram_gb for p in self.peers.values())
        
        return {
            'node_id': self.node_id,
            'total_peers': len(self.peers),
            'active_tasks': len(self.active_tasks),
            'completed_tasks': len(self.completed_tasks),
            'total_credits': sum(c.amount for c in self.credits),
            'swarm_compute_capacity': total_compute,
            'swarm_ram_gb': total_ram,
            'peers': [
                {
                    'node_id': p.node_id,
                    'device_type': p.device_type,
                    'reputation': p.reputation_score
                }
                for p in self.peers.values()
            ]
        }
    
    def stop(self):
        """Stop swarm connector"""
        logger.info("Stopping swarm connector...")
        self.running = False
        
        if self.server_socket:
            self.server_socket.close()
        
        logger.info("Swarm connector stopped")


# =============================================================================
# Demo Function
# =============================================================================
def demo():
    """Demonstrate Swarm Connector functionality"""
    print("=" * 70)
    print("🌐 Swarm Connector Demo - Distributed AI Computing")
    print("=" * 70)
    
    # Initialize swarm connector
    swarm = SwarmConnector(node_name="DemoNode_001")
    
    print(f"\n📍 Node ID: {swarm.node_id}")
    print(f"💰 Initial Credits: {sum(c.amount for c in swarm.credits)}")
    
    # Simulate discovering peers
    print("\n🔍 Simulating peer discovery...")
    swarm.peers['node_abc123'] = PeerNode(
        node_id='node_abc123',
        ip_address='192.168.1.100',
        port=8765,
        device_type='mobile',
        available_ram_gb=6.0,
        available_compute=80.0,
        models_available=['phi3-mini', 'gemma-2b'],
        reputation_score=0.95
    )
    
    swarm.peers['node_def456'] = PeerNode(
        node_id='node_def456',
        ip_address='192.168.1.101',
        port=8765,
        device_type='tablet',
        available_ram_gb=8.0,
        available_compute=90.0,
        models_available=['llama3-8b', 'mistral-7b'],
        reputation_score=0.98
    )
    
    print(f"  ✓ Discovered {len(swarm.peers)} peers")
    
    # Create and distribute a task
    print("\n📤 Creating compute task...")
    task = ComputeTask(
        task_id='task_001',
        task_type='inference',
        payload={'prompt': 'Explain quantum computing'},
        required_compute=50.0,
        priority=5
    )
    
    success = swarm.distribute_task(task)
    print(f"  {'✓' if success else '✗'} Task distribution: {'Success' if success else 'Failed'}")
    
    # Simulate task completion
    if success:
        task.status = 'completed'
        task.result = {'output': 'Quantum computing explanation...', 'tokens': 150}
        swarm.completed_tasks.append(task)
        swarm._award_credits(0.5, 'computation', task.task_id)
    
    # Display statistics
    print("\n📊 Swarm Statistics:")
    stats = swarm.get_swarm_statistics()
    print(f"  Total Peers: {stats['total_peers']}")
    print(f"  Active Tasks: {stats['active_tasks']}")
    print(f"  Completed Tasks: {stats['completed_tasks']}")
    print(f"  Total Credits: {stats['total_credits']:.2f}")
    print(f"  Swarm Compute Capacity: {stats['swarm_compute_capacity']:.1f}%")
    print(f"  Swarm RAM: {stats['swarm_ram_gb']:.1f} GB")
    
    print("\n👥 Connected Peers:")
    for peer in stats['peers']:
        print(f"  - {peer['node_id']} ({peer['device_type']}) - Rep: {peer['reputation']:.2f}")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    demo()
