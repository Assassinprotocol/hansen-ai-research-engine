export interface NetworkProfile {
  name: string;
  networkType: "shelbynet" | "local" | "custom";
  rpcUrl: string;
  aptosRpcUrl: string;
  contractAddress: string;
  locationHint: string;
}

export const NETWORK_PRESETS: Record<string, NetworkProfile> = {
  shelbynet: {
    name: "shelbynet",
    networkType: "shelbynet",
    rpcUrl: "https://shelby.shelbynet.shelby.xyz/shelby",
    aptosRpcUrl: "https://api.shelbynet.shelby.xyz/v1",
    contractAddress: "0x797570358c2208ce0e225f07fe727174c9cc4500072967dd963e645c95c2a07d",
    locationHint: "shelbynet-1",
  },
  private_mainnet: {
    name: "private_mainnet",
    networkType: "custom",
    rpcUrl: process.env.PRIVATE_MAINNET_SHELBY_RPC || "",
    aptosRpcUrl: process.env.PRIVATE_MAINNET_APTOS_RPC || "",
    contractAddress: process.env.PRIVATE_MAINNET_REGISTRY_ADDRESS || "",
    locationHint: "mainnet-1",
  },
  testnet: {
    name: "testnet",
    networkType: "custom",
    rpcUrl: process.env.TESTNET_SHELBY_RPC || "https://shelby.testnet.shelby.xyz/shelby",
    aptosRpcUrl: process.env.TESTNET_APTOS_RPC || "https://api.testnet.aptoslabs.com/v1",
    contractAddress: process.env.TESTNET_REGISTRY_ADDRESS || "",
    locationHint: "testnet-1",
  },
  localnet: {
    name: "localnet",
    networkType: "local",
    rpcUrl: process.env.LOCAL_SHELBY_RPC || "http://127.0.0.1:8080",
    aptosRpcUrl: process.env.LOCAL_APTOS_RPC || "http://127.0.0.1:8080/v1",
    contractAddress: process.env.LOCAL_REGISTRY_ADDRESS || "",
    locationHint: "local-1",
  },
};

export function resolveNetworkConfig(): NetworkProfile {
  const rawTarget = (process.env.ACTIVE_NETWORK || process.env.SHELBY_NETWORK || "shelbynet").toLowerCase().trim();
  const presetKey = rawTarget in NETWORK_PRESETS ? rawTarget : "shelbynet";
  const preset = NETWORK_PRESETS[presetKey];

  const resolvedRpc = process.env.SHELBY_RPC_URL || preset.rpcUrl;
  const resolvedAptosRpc = process.env.APTOS_RPC_URL || preset.aptosRpcUrl;
  const resolvedContract =
    process.env.HANSEN_REGISTRY_ADDRESS ||
    process.env.SHELBY_ACCOUNT ||
    preset.contractAddress;
  const resolvedHint = process.env.SHELBY_LOCATION_HINT || preset.locationHint;

  let resolvedType: "shelbynet" | "local" | "custom" = preset.networkType;
  if (rawTarget === "custom" || (process.env.SHELBY_RPC_URL && process.env.SHELBY_RPC_URL !== preset.rpcUrl)) {
    resolvedType = "custom";
  }

  return {
    name: presetKey,
    networkType: resolvedType,
    rpcUrl: resolvedRpc,
    aptosRpcUrl: resolvedAptosRpc,
    contractAddress: resolvedContract,
    locationHint: resolvedHint,
  };
}
