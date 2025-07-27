import os
import json
import time
import logging
from typing import Dict, Any, Optional, List

import requests
from web3 import Web3
from web3.exceptions import BadFunctionCallOutput, ContractLogicError
from web3.contract import Contract
from requests.exceptions import RequestException

# --- CONFIGURATION ---
# In a real application, this would be loaded from environment variables or a secure config file.
CONFIG = {
    "source_chain": {
        "name": "Ethereum_Sepolia",
        "rpc_url": "https://rpc.sepolia.org",  # Replace with your actual RPC URL
        "bridge_contract_address": "0x779877A7B0D9E8603169DdbD7836e478b4624789", # Example: Chainlink Token on Sepolia
        "etherscan_api_url": "https://api-sepolia.etherscan.io/api",
        "event_name": "Transfer", # We will listen for 'Transfer' events as a proxy for deposits
        "confirmations": 3 # Number of blocks to wait for finality
    },
    "destination_chain": {
        "name": "Polygon_Amoy",
        "rpc_url": "https://rpc-amoy.polygon.technology/", # Replace with your actual RPC URL
        "bridge_contract_address": "0xYourDestinationContractAddress", # Placeholder
        "signer_private_key": "0x..." # Placeholder for the key that would sign transactions
    },
    "listener": {
        "poll_interval_seconds": 15,
        "block_processing_batch_size": 100
    },
    "api_keys": {
        "etherscan": "YOUR_ETHERSCAN_API_KEY" # Required to fetch ABI dynamically
    },
    "state_file": "listener_state.json"
}

# --- STATE MANAGEMENT ---
class StateManager:
    """Manages the persistent state of the listener, specifically the last processed block."""
    def __init__(self, filepath: str):
        """Initializes the StateManager.

        Args:
            filepath (str): The path to the JSON file where the state is stored.
        """
        self.filepath = filepath

    def load_last_processed_block(self) -> int:
        """Loads the last processed block number from the state file.

        Returns:
            int: The last processed block number, or 0 if the file doesn't exist.
        """
        if not os.path.exists(self.filepath):
            return 0
        try:
            with open(self.filepath, 'r') as f:
                state = json.load(f)
                return state.get("last_processed_block", 0)
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not read state file {self.filepath}, starting from block 0. Error: {e}")
            return 0

    def save_last_processed_block(self, block_number: int):
        """Saves the last processed block number to the state file.

        Args:
            block_number (int): The block number to save.
        """
        try:
            with open(self.filepath, 'w') as f:
                json.dump({"last_processed_block": block_number}, f)
        except IOError as e:
            logging.error(f"Fatal: Could not write to state file {self.filepath}. Error: {e}")
            raise

# --- CHAIN INTERACTION ---
class ChainConnector:
    """Handles the connection and interaction with a single blockchain via Web3.py."""
    def __init__(self, rpc_url: str):
        """Initializes the ChainConnector.

        Args:
            rpc_url (str): The HTTP/WSS RPC endpoint URL for the blockchain node.
        """
        self.rpc_url = rpc_url
        self.web3 = None

    def connect(self) -> Web3:
        """Establishes a connection to the blockchain node with retry logic.

        Returns:
            Web3: An initialized and connected Web3 instance.
        
        Raises:
            ConnectionError: If connection fails after multiple retries.
        """
        for attempt in range(3):
            try:
                self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
                if self.web3.is_connected():
                    logging.info(f"Successfully connected to RPC endpoint: {self.rpc_url}")
                    return self.web3
            except Exception as e:
                logging.warning(f"Connection attempt {attempt + 1} failed: {e}")
                time.sleep(2 ** attempt)
        raise ConnectionError(f"Failed to connect to RPC endpoint after multiple retries: {self.rpc_url}")

    def get_latest_block_number(self) -> int:
        """Fetches the latest block number from the connected chain.

        Returns:
            int: The latest block number.
        """
        if not self.web3 or not self.web3.is_connected():
            self.connect()
        return self.web3.eth.block_number

    def get_contract(self, address: str, abi: List[Dict]) -> Contract:
        """Get a Web3.py contract instance.

        Args:
            address (str): The contract's address.
            abi (List[Dict]): The contract's ABI.

        Returns:
            Contract: The Web3.py contract object.
        """
        if not self.web3 or not self.web3.is_connected():
            self.connect()
        checksum_address = Web3.to_checksum_address(address)
        return self.web3.eth.contract(address=checksum_address, abi=abi)


# --- EVENT PROCESSING & TRANSACTION SUBMISSION ---
class EventProcessor:
    """Parses and validates raw event logs into a structured format."""

    def process_event_log(self, event_log: Dict) -> Optional[Dict[str, Any]]:
        """Processes a single raw event log.

        Args:
            event_log (Dict): The raw log from web3.eth.get_logs.

        Returns:
            Optional[Dict[str, Any]]: A dictionary with structured event data, or None if invalid.
        """
        try:
            # Example for ERC20 'Transfer' event
            processed_event = {
                "tx_hash": event_log['transactionHash'].hex(),
                "block_number": event_log['blockNumber'],
                "from_address": event_log['args']['from'],
                "to_address": event_log['args']['to'],
                "amount": event_log['args']['value'],
                "unique_event_id": f"{event_log['transactionHash'].hex()}-{event_log['logIndex']}"
            }
            # Basic validation
            if not all(k in processed_event for k in ['from_address', 'to_address', 'amount']):
                logging.warning(f"Malformed event log detected: {event_log}")
                return None
            return processed_event
        except (KeyError, AttributeError) as e:
            logging.error(f"Error processing event log: {e}. Log: {event_log}")
            return None

class TransactionSubmitter:
    """SIMULATOR: Simulates building, signing, and submitting a transaction to the destination chain."""

    def __init__(self, dest_chain_name: str):
        self.dest_chain_name = dest_chain_name

    def submit_claim_transaction(self, processed_event: Dict) -> str:
        """Simulates submitting a claim/mint transaction on the destination chain.
        In a real system, this would involve:
        1. Connecting to the destination chain's Web3 provider.
        2. Loading the relayer's wallet/private key.
        3. Building the transaction (e.g., calling a 'mint' function with event data).
        4. Estimating gas, signing the transaction, and sending it.
        5. Waiting for the transaction receipt.

        Args:
            processed_event (Dict): The structured data from the source chain event.

        Returns:
            str: A simulated transaction hash.
        """
        logging.info(f"[SIMULATION] Preparing to submit claim on '{self.dest_chain_name}' for event ID: {processed_event['unique_event_id']}")
        logging.info(f"[SIMULATION]   - Amount: {processed_event['amount']}")
        logging.info(f"[SIMULATION]   - Recipient: {processed_event['to_address']}")

        # Simulate transaction building and signing delay
        time.sleep(1)

        mock_tx_hash = Web3.keccak(text=f"mock_tx_{processed_event['unique_event_id']}_{time.time()}").hex()
        logging.info(f"[SIMULATION] Successfully submitted transaction to '{self.dest_chain_name}'. Mock TxHash: {mock_tx_hash}")
        return mock_tx_hash


# --- MAIN ORCHESTRATOR ---
class CrossChainBridgeListener:
    """The main orchestrator that listens for events and coordinates the bridging process."""

    def __init__(self, config: Dict):
        self.config = config
        self.state_manager = StateManager(config["state_file"])
        
        self._setup_logging()

        # Initialize source chain components
        self.source_connector = ChainConnector(config["source_chain"]["rpc_url"])
        self.source_web3 = self.source_connector.connect()
        self.bridge_contract_abi = self._fetch_abi_from_etherscan(
            config["api_keys"]["etherscan"],
            config["source_chain"]["bridge_contract_address"],
            config["source_chain"]["etherscan_api_url"]
        )
        self.source_bridge_contract = self.source_connector.get_contract(
            config["source_chain"]["bridge_contract_address"],
            self.bridge_contract_abi
        )

        # Initialize processors and simulators
        self.event_processor = EventProcessor()
        self.tx_submitter = TransactionSubmitter(config["destination_chain"]["name"])

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        logging.getLogger("web3").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def _fetch_abi_from_etherscan(self, api_key: str, contract_address: str, api_url: str) -> List[Dict]:
        """Fetches a contract's ABI from an Etherscan-compatible API.
        Demonstrates use of the 'requests' library for off-chain data.
        """
        params = {
            "module": "contract",
            "action": "getabi",
            "address": contract_address,
            "apikey": api_key
        }
        try:
            logging.info(f"Fetching ABI for {contract_address} from {api_url}...")
            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data['status'] == '1':
                logging.info("Successfully fetched ABI.")
                return json.loads(data['result'])
            else:
                raise ValueError(f"Etherscan API error: {data['message']} - {data['result']}")
        except RequestException as e:
            logging.error(f"HTTP error fetching ABI: {e}")
            raise
        except (ValueError, json.JSONDecodeError) as e:
            logging.error(f"Error parsing ABI response: {e}")
            raise

    def run(self):
        """Starts the main event listening loop."""
        logging.info("Starting Cross-Chain Bridge Listener...")
        last_processed_block = self.state_manager.load_last_processed_block()
        if last_processed_block == 0:
            # On first run, start from the current block to avoid processing a long history
            last_processed_block = self.source_connector.get_latest_block_number() - self.config["source_chain"]["confirmations"]
            logging.info(f"No previous state found. Starting from block {last_processed_block}")
        else:
            logging.info(f"Resuming from last processed block: {last_processed_block}")

        while True:
            try:
                latest_block = self.source_connector.get_latest_block_number()
                # Ensure we only process blocks with enough confirmations
                target_block = latest_block - self.config["source_chain"]["confirmations"]

                if target_block <= last_processed_block:
                    time.sleep(self.config["listener"]["poll_interval_seconds"])
                    continue

                # Process blocks in batches to avoid overwhelming the RPC node
                batch_end_block = min(target_block, last_processed_block + self.config["listener"]["block_processing_batch_size"])
                
                logging.info(f"Scanning for events from block {last_processed_block + 1} to {batch_end_block} (Latest: {latest_block})")

                event_filter = self.source_bridge_contract.events[self.config["source_chain"]["event_name"]].create_filter(
                    fromBlock=last_processed_block + 1,
                    toBlock=batch_end_block
                )
                
                logs = event_filter.get_all_entries()

                if logs:
                    logging.info(f"Found {len(logs)} new event(s) in the scanned range.")
                    for log in logs:
                        processed_event = self.event_processor.process_event_log(log)
                        if processed_event:
                            # In a real system, you'd check if this event has already been processed
                            # using a database to prevent replays.
                            logging.info(f"Processing event from Tx: {processed_event['tx_hash']}")
                            self.tx_submitter.submit_claim_transaction(processed_event)
                
                # Update state only after successful processing of the batch
                self.state_manager.save_last_processed_block(batch_end_block)
                last_processed_block = batch_end_block

            except ConnectionError as e:
                logging.error(f"Connection error: {e}. Reconnecting...")
                self.source_connector.connect()
                time.sleep(5)
            except Exception as e:
                logging.error(f"An unexpected error occurred in the main loop: {e}")
                time.sleep(self.config["listener"]["poll_interval_seconds"])

def main():
    if CONFIG["api_keys"]["etherscan"] == "YOUR_ETHERSCAN_API_KEY":
        print("ERROR: Please set your Etherscan API key in the CONFIG dictionary.")
        return

    listener = CrossChainBridgeListener(CONFIG)
    try:
        listener.run()
    except KeyboardInterrupt:
        logging.info("Shutdown signal received. Exiting gracefully.")

if __name__ == "__main__":
    main()
