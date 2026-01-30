// hardhat.config.js — CommonJS style, no ESM nonsense

require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

module.exports = {
  solidity: "0.8.20",
  networks: {
    shidoTestnet: {
      url: "https://rpc-testnet-nodes.shidoscan.com",
      accounts: [process.env.PRIVATE_KEY],
      chainId: 9007,
    },
  },
};
