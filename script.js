document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  const walletOverlay = document.getElementById('wallet-overlay');
  const walletCloseBtn = document.getElementById('wallet-close-btn');

  // Telegram init
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // --- PUB ENTRY ---
  enterBtn.addEventListener('click', () => {
    outside.classList.remove('active');
    outside.style.opacity = '0';
    setTimeout(() => {
      outside.style.display = 'none';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1200);
  });

  // --- WALLET OVERLAY UTILITY ---
  function showWalletOverlay(message) {
    walletOverlay.querySelector('p').textContent = message;
    walletOverlay.classList.remove('hidden');
  }

  walletCloseBtn.addEventListener('click', () => {
    walletOverlay.classList.add('hidden');
  });

  // --- PAID GAME WALLET CHECK ---
  function tryEnterGame(gameId) {
    const user = Telegram.WebApp.initDataUnsafe.user;
    if (!user || !user.id) {
      showWalletOverlay("No Telegram user data. DM the bot and send /start to create a wallet.");
      return;
    }

    // Ask bot if wallet exists for this game
    Telegram.WebApp.sendData(JSON.stringify({
      action: "check_wallet",
      user_id: user.id,
      game: gameId
    }));

    // Listen for bot response only for this attempt
    const handler = (event) => {
      if (event.data === "ALLOWED") {
        Telegram.WebApp.offEvent('message', handler);
        showGame(gameId);
      } else if (event.data.startsWith("DENIED")) {
        Telegram.WebApp.offEvent('message', handler);
        showWalletOverlay(event.data.split(":")[1]?.trim() || 
          "You need to create a wallet before entering this game."
        );
      }
    };
    Telegram.WebApp.onEvent('message', handler);

    // Timeout fallback
    setTimeout(() => {
      Telegram.WebApp.offEvent('message', handler);
      showWalletOverlay("Wallet check timed out. Try again or DM the bot.");
    }, 5000);
  }

  // --- GAME SCREEN SWITCHING ---
  function showGame(gameId) {
    const pub = document.getElementById('view-inside');
    pub.classList.remove('active');
    pub.style.opacity = '0';

    const gameScreen = document.getElementById('game-' + gameId);
    setTimeout(() => {
      pub.style.display = 'none';
      gameScreen.style.display = 'block';
      gameScreen.classList.add('visible');

      if (gameId === 'football') loadFootballCard();
    }, 1000);
  }

  function backToPub() {
    document.querySelectorAll('.game-screen').forEach(screen => {
      screen.classList.remove('visible');
      screen.style.opacity = '0';
    });

    setTimeout(() => {
      document.querySelectorAll('.game-screen').forEach(screen => {
        screen.style.display = 'none';
      });
      const pub = document.getElementById('view-inside');
      pub.style.display = 'flex';
      pub.classList.add('active');
      pub.style.opacity = '1';
    }, 1000);
  }

  // --- FOOTBALL CARD LOGIC ---
  const footballTeams = [
    "Arsenal","Ajax","Bournemouth","Brentford","Brighton","Burnley",
    "Chelsea","Crystal Palace","Everton","Fulham","Liverpool","Luton",
    "Man City","Man United","Newcastle","Nottingham Forest","Sheffield Utd",
    "Tottenham","West Ham","Wolves","Leicester","Leeds","Southampton",
    "Blackburn","Birmingham","Coventry","Ipswich","Middlesbrough","Norwich",
    "Preston","QPR","Sheffield Wed"
  ];

  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) return;

    grid.innerHTML = '';
    footballTeams.forEach((team, index) => {
      const slot = document.createElement('div');
      slot.className = 'team-slot';
      slot.innerHTML = `
        <div>${team}</div>
        <div class="username">[Pick Me]</div>
      `;
      slot.onclick = () => pickTeam(index, team, slot);
      grid.appendChild(slot);
    });
  }

  function pickTeam(index, team, slot) {
    if (!confirm(`Claim ${team} for $1? Wallet already checked.`)) return;

    const username = Telegram.WebApp.initDataUnsafe.user?.username || "You";
    slot.querySelector('.username').textContent = `@${username}`;
    slot.classList.add('claimed');
    slot.onclick = null;

    console.log(`Claimed ${team} by @${username}`);
    // Later: send to bot for real wallet tx & group announcement
  }

  // --- EXPOSE FUNCTIONS GLOBALLY ---
  window.showGame = showGame;
  window.backToPub = backToPub;
  window.tryEnterGame = tryEnterGame;
});
