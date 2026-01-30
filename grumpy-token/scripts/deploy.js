const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with:", deployer.address);

  const marketing = "0xf1B4aCA502213Ebb1a542B239495F5068d28bC50";
  const lp        = "0x11ae8EecFCD1A2aA7EBC5327eBaF6e3C22bf1262";

  const GrumpyOldGit = await hre.ethers.getContractFactory("GrumpyOldGit");
  const token = await GrumpyOldGit.deploy(marketing, lp);

  await token.waitForDeployment();
  console.log("GrumpyOldGit deployed to:", await token.getAddress());
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
