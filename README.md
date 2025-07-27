# fall-source: Cross-Chain Bridge Event Listener Simulation

This repository contains a Python script that simulates a critical component of a decentralized cross-chain bridge. It acts as a robust event listener on a source blockchain (e.g., Ethereum), processes relevant events, and simulates the corresponding action (e.g., minting tokens) on a destination blockchain (e.g., Polygon).

This project is designed as an architectural showcase, emphasizing modularity, error handling, and state management, rather than being a production-ready bridge relayer.

---

## Concept

A cross-chain bridge allows users to transfer assets or data from one blockchain to another. A common pattern is "lock-and-mint":

1.  A user deposits tokens into a bridge contract on the **Source Chain** (e.g., Ethereum).
2.  This action emits a `Deposit` event.
3.  A network of off-chain relayers (or listeners) detects this event.
4.  After verifying the event and waiting for sufficient block confirmations (to prevent reorgs), a relayer submits a transaction to a bridge contract on the **Destination Chain**.
5.  This transaction triggers the minting of a corresponding wrapped token (e.g., ETH -> WETH on Polygon) for the user.

This script simulates the role of the **off-chain relayer/listener** (steps 3 and 4).

## Code Architecture

The script is designed with a clear separation of concerns, using several classes to handle distinct responsibilities:

-   `CrossChainBridgeListener` (in `script.py`)
    -   **Role**: The main orchestrator.
    -   **Responsibilities**: Initializes all components, manages the main processing loop, coordinates interactions between other classes, and handles graceful startup/shutdown.

-   `StateManager`
    -   **Role**: Handles persistence.
    -   **Responsibilities**: Saves the last successfully processed block number to a local file (`listener_state.json`). This allows the script to be stopped and restarted without reprocessing historical events.

-   `ChainConnector`
    -   **Role**: Blockchain interaction wrapper.
    -   **Responsibilities**: Manages the connection to a blockchain's RPC endpoint using `web3.py`. It includes logic for connection retries and provides methods to fetch blocks and contract instances.

-   `EventProcessor`
    -   **Role**: Data transformation and validation.
    -   **Responsibilities**: Takes raw event logs from `web3.py`, parses them into a clean, structured dictionary, and performs basic validation.

-   `TransactionSubmitter`
    -   **Role**: Destination chain action simulator.
    -   **Responsibilities**: Simulates the process of building, signing, and sending a transaction to the destination chain. In this simulation, it logs the intended action and generates a mock transaction hash instead of performing a real on-chain transaction.

### Architectural Flow

```
+----------------------------+
| CrossChainBridgeListener   | (Orchestrator)
+-------------+--------------+
              | 1. run() loop starts
              | 2. Get last processed block
              |              |              
+-------------v--------------+      +-------------------------+
| StateManager               |----->| listener_state.json     |
+----------------------------+      +-------------------------+
              |
              | 3. Get latest block from source chain
              v
+-------------+--------------+
| ChainConnector (Source)    |<---- (Source Chain RPC)
+-------------+--------------+
              |
              | 4. Fetch event logs in range [last_block..latest_block]
              v
+-------------+--------------+
| EventProcessor             |
+-------------+--------------+
              |
              | 5. Parse and validate each log
              v
+-------------+--------------+
| TransactionSubmitter       | (Simulation)
+-------------+--------------+
              |
              | 6. Simulate "mint" transaction on destination chain
              v
              | 7. Log mock transaction hash
              |
              | 8. Update last processed block
              |              |
              +--------------+ (goto step 2)
```

## How it Works

1.  **Initialization**: The `CrossChainBridgeListener` is instantiated. It sets up logging and initializes all helper classes.
2.  **ABI Fetching**: It uses the `requests` library to dynamically fetch the source contract's ABI from an Etherscan-like API. This demonstrates interaction with external, non-blockchain services.
3.  **State Loading**: The `StateManager` reads `listener_state.json` to find the last block number that was processed. If the file doesn't exist, it defaults to starting from the current block to avoid a lengthy catch-up.
4.  **Main Loop**: The listener enters an infinite loop.
5.  **Block Polling**: In each iteration, it checks the latest block number on the source chain.
6.  **Event Scanning**: It scans a batch of blocks between the `last_processed_block` and the `latest_block` (minus a confirmation delay) for the target event (e.g., `Transfer`).
7.  **Processing**: If events are found, each one is passed to the `EventProcessor` to be parsed.
8.  **Submission (Simulation)**: For each valid, processed event, the `TransactionSubmitter` is called. It logs the details of the transaction it *would* have sent to the destination chain and creates a mock transaction hash.
9.  **State Saving**: After successfully processing a batch of blocks, the `StateManager` updates `listener_state.json` with the new latest processed block number.
10. **Sleep**: The listener then waits for a configured poll interval before starting the loop again.

## Usage Example

### 1. Prerequisites

-   Python 3.8+
-   An RPC endpoint URL for an Ethereum testnet (e.g., Sepolia). You can get one for free from services like [Infura](https://infura.io) or [Alchemy](https://www.alchemy.com).
-   An Etherscan API key (free to generate) to allow the script to fetch contract ABIs automatically.

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/your-username/fall-source.git
cd fall-source

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

# Install the required libraries
pip install -r requirements.txt
```

### 3. Configuration

Open the `script.py` file and edit the `CONFIG` dictionary at the top:

```python
CONFIG = {
    "source_chain": {
        "name": "Ethereum_Sepolia",
        # Replace with your Sepolia RPC URL
        "rpc_url": "https://sepolia.infura.io/v3/YOUR_INFURA_PROJECT_ID",
        # ... (other settings)
    },
    # ...
    "api_keys": {
        # Replace with your Etherscan API key
        "etherscan": "YOUR_ETHERSCAN_API_KEY"
    },
    # ...
}
```

-   Update `source_chain.rpc_url` with your personal RPC endpoint.
-   Update `api_keys.etherscan` with your Etherscan API key.

The script is pre-configured to watch `Transfer` events on the Chainlink (LINK) token contract on the Sepolia testnet, which is a good way to see events being generated.

### 4. Running the Script

Execute the script from your terminal:

```bash
python script.py
```

### 5. Expected Output

On the first run, the script will fetch the contract ABI and start scanning from a recent block.

```
2023-10-27 14:30:00 - INFO - Starting Cross-Chain Bridge Listener...
2023-10-27 14:30:00 - INFO - Successfully connected to RPC endpoint: https://rpc.sepolia.org
2023-10-27 14:30:00 - INFO - Fetching ABI for 0x779877A7B0D9E8603169DdbD7836e478b4624789 from https://api-sepolia.etherscan.io/api...
2023-10-27 14:30:02 - INFO - Successfully fetched ABI.
2023-10-27 14:30:02 - INFO - No previous state found. Starting from block 4851200
2023-10-27 14:30:05 - INFO - Scanning for events from block 4851201 to 4851300 (Latest: 4851303)
...
(after some time, if a Transfer event occurs)
...
2023-10-27 14:31:15 - INFO - Found 1 new event(s) in the scanned range.
2023-10-27 14:31:15 - INFO - Processing event from Tx: 0x123abc...
2023-10-27 14:31:15 - INFO - [SIMULATION] Preparing to submit claim on 'Polygon_Amoy' for event ID: 0x123abc...-15
2023-10-27 14:31:15 - INFO - [SIMULATION]   - Amount: 1000000000000000000
2023-10-27 14:31:15 - INFO - [SIMULATION]   - Recipient: 0xRecipientAddress...
2023-10-27 14:31:16 - INFO - [SIMULATION] Successfully submitted transaction to 'Polygon_Amoy'. Mock TxHash: 0x456def...
```

To stop the listener, press `Ctrl+C`.
