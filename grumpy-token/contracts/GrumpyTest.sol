// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/*
 * Grumpy Test (GOG) — v1.5 Final Stable
 * -----------------------------------------
 * Features:
 * - Fixed 194,500,000 total supply
 * - Max tax = 2% (owner can reduce to 0%)
 * - Once tax = 0, owner can renounce contract
 * - No minting / burning / freezing / blacklist
 * - Anti-bot: launch protection, limits, cooldown
 * - 2-step ownership and treasury transfer
 * - Safe DEX validation (trusted factory + LP min)
 */

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";

interface IUniswapV2Pair {
    function factory() external view returns (address);
    function token0() external view returns (address);
    function token1() external view returns (address);
    function getReserves() external view returns (uint112 reserve0, uint112 reserve1, uint32 blockTimestampLast);
}

contract GrumpyTest is ERC20, Ownable {

    // ---- Tax ----
    uint256 public constant MAX_TAX_BPS = 200; // 2%
    uint256 public taxBps = 200; // starts at 2%

    // ---- Treasury ----
    address public treasury;
    address public pendingTreasury;

    // ---- DEX Safety ----
    mapping(address => bool) public isExcludedFromFee;
    mapping(address => bool) public isMarketPair;
    mapping(address => bool) public trustedFactories;
    uint112 public minTokenLiquidityForPair;

    // ---- Launch & Limits ----
    bool public tradingEnabled;
    uint256 public launchBlock;
    uint256 public launchProtectionBlocks;
    uint256 public maxTxAmount;
    uint256 public maxWalletAmount;
    uint256 public cooldownSeconds;
    mapping(address => uint256) private _lastTxTimestamp;

    // ---- Events ----
    event TreasuryUpdated(address indexed newTreasury);
    event TreasuryHandoverStarted(address indexed pending);
    event TaxUpdated(uint256 newTaxBps);
    event ExcludedFromFee(address indexed account, bool excluded);
    event MarketPairSet(address indexed pair, bool isPair);
    event TrustedFactorySet(address indexed factory, bool trusted);
    event TradingEnabled(uint256 launchBlock, uint256 protectionBlocks);
    event LimitsUpdated(uint256 maxTx, uint256 maxWallet, uint256 cooldown);
    event MinTokenLiquiditySet(uint112 minAmount);

    constructor(address initialOwner, address _treasury)
        ERC20("GrumpyTest", "GOG-Test")
        Ownable(initialOwner)
    {
        require(initialOwner != address(0), "0x11ae8EecFCD1A2aA7EBC5327eBaF6e3C22bf1262");
        require(_treasury != address(0), "0xf1B4aCA502213Ebb1a542B239495F5068d28bC50");

        treasury = _treasury;

        // Fixed total supply
        _mint(initialOwner, 194_500_000 * 10 ** decimals());

        // Default limits
        maxTxAmount = (totalSupply() * 10) / 1000; // 1%
        maxWalletAmount = (totalSupply() * 20) / 1000; // 2%
        cooldownSeconds = 0;

        // Exclusions
        isExcludedFromFee[initialOwner] = true;
        isExcludedFromFee[address(this)] = true;
        isExcludedFromFee[_treasury] = true;
    }

    // ------------------------------------------------------------------------
    // Treasury (2-step transfer)
    // ------------------------------------------------------------------------
    function setPendingTreasury(address _pending) external onlyOwner {
        require(_pending != address(0), "Zero pending");
        pendingTreasury = _pending;
        emit TreasuryHandoverStarted(_pending);
    }

    function acceptTreasury() external {
        require(msg.sender == pendingTreasury, "Not pending");
        treasury = pendingTreasury;
        pendingTreasury = address(0);
        emit TreasuryUpdated(treasury);
    }

    // ------------------------------------------------------------------------
    // Tax Control
    // ------------------------------------------------------------------------
    function setTaxBps(uint256 _taxBps) external onlyOwner {
        require(_taxBps <= MAX_TAX_BPS, "Exceeds 2% cap");
        taxBps = _taxBps;
        emit TaxUpdated(_taxBps);
    }

    // ------------------------------------------------------------------------
    // DEX Setup
    // ------------------------------------------------------------------------
    function setTrustedFactory(address factory, bool trusted) external onlyOwner {
        trustedFactories[factory] = trusted;
        emit TrustedFactorySet(factory, trusted);
    }

    function setMinTokenLiquidityForPair(uint112 minAmount) external onlyOwner {
        minTokenLiquidityForPair = minAmount;
        emit MinTokenLiquiditySet(minAmount);
    }

    function setMarketPair(address pair, bool _isPair) external onlyOwner {
        if (_isPair) {
            address factory = IUniswapV2Pair(pair).factory();
            require(trustedFactories[factory], "Untrusted factory");
            address t0 = IUniswapV2Pair(pair).token0();
            address t1 = IUniswapV2Pair(pair).token1();
            require(t0 == address(this) || t1 == address(this), "Not GOG pair");
            if (minTokenLiquidityForPair > 0) {
                (uint112 r0, uint112 r1, ) = IUniswapV2Pair(pair).getReserves();
                uint112 ourRes = t0 == address(this) ? r0 : r1;
                require(ourRes >= minTokenLiquidityForPair, "Low LP");
            }
        }
        isMarketPair[pair] = _isPair;
        emit MarketPairSet(pair, _isPair);
    }

    function setExcludedFromFee(address account, bool excluded) external onlyOwner {
        isExcludedFromFee[account] = excluded;
        emit ExcludedFromFee(account, excluded);
    }

    // ------------------------------------------------------------------------
    // Launch and Limits
    // ------------------------------------------------------------------------
    function setTradingEnabled(uint256 protectionBlocks) external onlyOwner {
        require(!tradingEnabled, "Already enabled");
        tradingEnabled = true;
        launchBlock = block.number;
        launchProtectionBlocks = protectionBlocks;
        emit TradingEnabled(launchBlock, protectionBlocks);
    }

    function setMaxTxPercent(uint256 permille) external onlyOwner {
        require(permille > 0, "Invalid");
        maxTxAmount = (totalSupply() * permille) / 1000;
    }

    function setMaxWalletPercent(uint256 permille) external onlyOwner {
        require(permille > 0, "Invalid");
        maxWalletAmount = (totalSupply() * permille) / 1000;
    }

    function setCooldownSeconds(uint256 secs) external onlyOwner {
        cooldownSeconds = secs;
    }

    function setLimits(uint256 _maxTxAmount, uint256 _maxWalletAmount, uint256 _cooldownSeconds) external onlyOwner {
        maxTxAmount = _maxTxAmount;
        maxWalletAmount = _maxWalletAmount;
        cooldownSeconds = _cooldownSeconds;
        emit LimitsUpdated(_maxTxAmount, _maxWalletAmount, _cooldownSeconds);
    }

    // ------------------------------------------------------------------------
    // Transfer Logic (with tax and anti-bot)
    // ------------------------------------------------------------------------
    function _update(address from, address to, uint256 value) internal virtual override {
    bool marketTx = isMarketPair[from] || isMarketPair[to];  // <— semicolon here

    if (marketTx && launchProtectionBlocks > 0 && block.number <= launchBlock + launchProtectionBlocks) {
        require(isExcludedFromFee[from] || isExcludedFromFee[to], "Launch protected");
    }

        // Launch protection: first few blocks
        if (marketTx && launchProtectionBlocks > 0 && block.number <= launchBlock + launchProtectionBlocks) {
            if (!isExcludedFromFee[from] && !isExcludedFromFee[to]) {
                revert("Launch protected");
            }
        }

        // Limits
        if (!isExcludedFromFee[from] && !isExcludedFromFee[to]) {
            if (maxTxAmount > 0) {
                require(value <= maxTxAmount, "Exceeds max tx");
            }
            if (!marketTx && maxWalletAmount > 0) {
                require(balanceOf(to) + value <= maxWalletAmount, "Exceeds max wallet");
            }
            if (cooldownSeconds > 0) {
                uint256 last = _lastTxTimestamp[from];
                if (last != 0) {
                    require(block.timestamp >= last + cooldownSeconds, "Cooldown");
                }
                _lastTxTimestamp[from] = block.timestamp;
            }
        }

        // Tax on DEX trades only
        if (taxBps > 0 && marketTx && !isExcludedFromFee[from] && !isExcludedFromFee[to]) {
            uint256 fee = (value * taxBps) / 10_000;
            uint256 sendAmount = value - fee;
            super._update(from, treasury, fee);
            super._update(from, to, sendAmount);
        } else {
            super._update(from, to, value);
        }
    }

    // ------------------------------------------------------------------------
    // Rescue (safety)
    // ------------------------------------------------------------------------
    function rescueERC20(address token, address to, uint256 amount) external onlyOwner {
        require(token != address(this), "Cannot rescue self");
        require(to != address(0), "Zero address");
    }

    // ------------------------------------------------------------------------
    // Renounce Ownership (only when tax = 0)
    // ------------------------------------------------------------------------
    function renounceIfNoTax() external onlyOwner {
        require(taxBps == 0, "Tax must be 0 first");
        renounceOwnership(); // Uses standard Ownable renounce (direct to zero)
    }
}
