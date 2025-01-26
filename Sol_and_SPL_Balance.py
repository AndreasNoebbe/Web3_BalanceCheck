import requests
from solders.keypair import Keypair
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
import nacl.signing  # To derive the public key from the private key
from moralis import sol_api

# Solana RPC Endpoint
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Your API token for authentication
SOLANA_RPC_TOKEN = "INSERT UR API TOKEN HERE FROM SOLSCAN"

# Moralis API Key
MORALIS_API_KEY = "INSERT UR API TOKEN HERE FROM MORALIS"

# Your 12-word mnemonic phrase
MNEMONIC_PHRASE = "12 word phrase here"

print("Current: ", MNEMONIC_PHRASE)
PASSPHRASE = ""  # Leave blank for no passphrase

# Number of addresses to generate
NUM_ADDRESSES = 110

# Known token mint addresses for easy identification
KNOWN_TOKENS = {
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "So11111111111111111111111111111111111111112": "Wrapped SOL (wSOL)",
    "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E": "USD Tether (USDT)"
}
# Function to derive Solana public keys and private keys
def derive_solana_addresses(seed_bytes, num_addresses):
    addresses = []
    bip44 = Bip44.FromSeed(seed_bytes, Bip44Coins.SOLANA)
    for account_index in range(num_addresses):
        bip44_acc = bip44.Purpose().Coin().Account(account_index).Change(Bip44Changes.CHAIN_EXT)
        private_key = bip44_acc.PrivateKey().Raw().ToBytes()
        signing_key = nacl.signing.SigningKey(private_key)
        public_key = signing_key.verify_key.encode()
        private_public_key = private_key + public_key  # Combine private and public keys (64 bytes)
        try:
            keypair = Keypair.from_bytes(private_public_key)
            addresses.append((str(keypair.pubkey()), private_public_key.hex()))  # Return public key and private key
        except Exception as e:
            print(f"Error deriving keypair for account {account_index}: {e}")
            continue
    return addresses

# Function to fetch SOL balance for a single public key
def fetch_sol_balance(public_key):
    try:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [public_key]}
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SOLANA_RPC_TOKEN}"}
        response = requests.post(SOLANA_RPC_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        if "result" in data:
            lamports = data["result"]["value"]
            return lamports / 1e9  # Convert lamports to SOL
        else:
            print(f"Error fetching SOL balance for {public_key}: {data.get('error', {}).get('message', 'Unknown error')}")
            return None
    except requests.RequestException as e:
        print(f"Network error fetching SOL balance for {public_key}: {e}")
        return None

# Function to fetch SPL token balances for a single public key
def fetch_spl_token_balances(public_key):
    params = {
        "network": "mainnet",
        "address": public_key,
    }
    try:
        result = sol_api.account.get_spl(api_key=MORALIS_API_KEY, params=params)
        return result
    except Exception as e:
        print(f"Error fetching SPL balances for {public_key}: {e}")
        return []

# Main logic
if __name__ == "__main__":
    # Derive public keys and private keys from the mnemonic phrase
    seed_bytes = Bip39SeedGenerator(MNEMONIC_PHRASE).Generate(PASSPHRASE)
    derived_data = derive_solana_addresses(seed_bytes, NUM_ADDRESSES)

    print("\nFetching SOL and SPL Token Balances for Derived Addresses:")
    non_empty_found = False
    for idx, (public_key, private_key) in enumerate(derived_data, start=1):
        # Fetch SOL balance
        sol_balance = fetch_sol_balance(public_key)
        if sol_balance and sol_balance > 0:
            non_empty_found = True
            print(f"\nWallet {idx}: {public_key}")
            print(f"  SOL Balance: {sol_balance:.5f} SOL")
            print(f"  Private Key: {private_key}")

        # Fetch SPL token balances
        tokens = fetch_spl_token_balances(public_key)
        for token in tokens:
            mint = token.get("mint")
            amount = float(token.get("amount", 0))
            decimals = int(token.get("decimals", 0))
            token_name = KNOWN_TOKENS.get(mint, "Unknown Token")
            if (token_name == "USDC" and amount > 1) or (token_name == "Unknown Token" and amount > 1000000):
                if not non_empty_found:
                    print(f"\nWallet {idx}: {public_key}")
                    non_empty_found = True
                print(f"  - {token_name} (Mint: {mint})")
                print(f"    Amount: {amount}")
                print(f"    Private Key: {private_key}")

    if not non_empty_found:
        print("\nNo wallets with non-zero SOL or SPL token balances were found.")
