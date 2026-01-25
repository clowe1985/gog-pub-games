document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Telegram init
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();

    // Immediately check wallet on app load
    const user = Telegram.WebApp.initDataUnsafe.user;
    if (user && user.id) {
      // Disable enter button until wallet check passes
      enterBtn.disabled = true;
      enterBtn.textContent = "Checking wallet...";

      // Send wallet check request to bot
      const sent = Telegram.WebApp.sendData(JSON.stringify({
        action: "check_wallet",
        user_id: user.id
      }));
    console.log("sendData result:", sent);
    } else {
      showLocked("No Telegram user data. Bugger off and try again.");
    }
  }

  // Listen for bot response (Telegram sends it via message event)
  Telegram.WebApp.onEvent('message', (event) => {
    if (event.data === "ALLOWED") {
      enterBtn.disabled = false;
      enterBtn.textContent = "Enter the Pub, you mug";
      // Allow entry now
    } else if (event.data.startsWith("DENIED")) {
      showLocked(event.data.split(":")[1]?.trim() || "No wallet found. Sod off.");
    }
  });

  // Fallback if bot doesn't reply in 5 seconds
  setTimeout(() => {
    if (enterBtn.disabled) {
      showLocked("Wallet check timed out. Try again or bugger off.");
    }
  }, 5000);

  // Enter button (only enabled if wallet OK)
  enterBtn.addEventListener('click', () => {
    outside.classList.remove('active');
    outside.style.opacity = '0';
    setTimeout(() => {
      outside.style.display = 'none';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1200);
  });

  // Game switching functions (your existing ones)
  function showGame(gameId) {
    document.getElementById('view-inside').classList.remove('active');
    document.getElementById('view-inside').style.opacity = '0';

    const gameScreen = document.getElementById('game-' + gameId);
    setTimeout(() => {
      document.getElementById('view-inside').style.display = 'none';
      gameScreen.style.display = 'block';
      gameScreen.classList.add('visible');

      // Load football grid if needed
      if (gameId === 'football') {
        loadFootballCard();
      }
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

  // Football Card teams & logic (your existing code)
  const footballTeams = [
    "Arsenal", "Ajax", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];

  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) return; // safety

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
    if (!confirm(`Claim ${team} for $1? Wallet already checked at door.`)) return;

    const username = Telegram.WebApp.initDataUnsafe.user?.username || "You";
    slot.querySelector('.username').textContent = `@${username}`;
    slot.classList.add('claimed');
    slot.onclick = null;

    console.log(`Claimed ${team} by @${username}`);
    // Later: send to bot for real wallet tx & group announcement
  }
});
