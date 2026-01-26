document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Force correct initial state – outside first, everything else hidden
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';
  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  // Hide all game screens at start
  document.querySelectorAll('.game-screen').forEach(screen => {
    screen.style.display = 'none';
    screen.classList.remove('visible');
  });

  // Enter pub button – fade to inside pub (roast + games menu)
  enterBtn.addEventListener('click', () => {
    outside.style.opacity = '0';
    setTimeout(() => {
      outside.style.display = 'none';
      outside.classList.remove('active');
      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 1200);
  });

  // Telegram init
  if (window.Telegram?.WebApp) {
    Telegram.WebApp.ready();
    Telegram.WebApp.expand();
  }

  // Show game screen – only called when tapping a game button
  window.showGame = function(gameId) {
    const pub = document.getElementById('view-inside');
    pub.classList.remove('active');
    pub.style.opacity = '0';

    const gameScreen = document.getElementById('game-' + gameId);
    if (!gameScreen) return;

    setTimeout(() => {
      pub.style.display = 'none';
      gameScreen.style.display = 'block';
      gameScreen.classList.add('visible');
      gameScreen.style.opacity = '1';

      // Load interactive content only when tab opens
      if (gameId === 'football') {
        loadFootballCard();
      }
    }, 600);
  };

  // Back to pub
  window.backToPub = function() {
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
    }, 600);
  };

  // Football teams list (same as before)
const footballTeams = [
  "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Burnley",
  "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
  "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
  "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
  "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
  "Preston", "QPR", "Sheffield Wed"
];

function fetchCardState() {
  Telegram.WebApp.sendData(JSON.stringify({ action: "get_card_state" }));

  const handler = (event) => {
    if (event.data.startsWith("CARD_STATE:")) {
      const state = JSON.parse(event.data.split("CARD_STATE:")[1]);
      renderFootballGrid(state.teams);
      Telegram.WebApp.offEvent('message', handler);
    }
  };

  Telegram.WebApp.onEvent('message', handler);

  // Timeout
  setTimeout(() => {
    Telegram.WebApp.offEvent('message', handler);
    console.log("Card state timed out");
  }, 5000);
}

function renderFootballGrid(state) {
  const grid = document.getElementById('football-grid');
  if (!grid) return;

  grid.innerHTML = '';

  footballTeams.forEach(team => {
    const claimedBy = state[team] || '[Pick Me]';
    const slot = document.createElement('div');
    slot.className = 'team-slot' + (claimedBy !== '[Pick Me]' ? ' claimed' : '');
    slot.innerHTML = `
      <div>${team}</div>
      <div class="username">${claimedBy}</div>
    `;

    if (claimedBy === '[Pick Me]') {
      slot.onclick = () => claimTeam(team, slot);
    }

    grid.appendChild(slot);
  });
}

function claimTeam(team, slot) {
  const username = '@' + (Telegram.WebApp.initDataUnsafe.user?.username || "You");

  if (!confirm(`Claim ${team} as ${username}?`)) return;

  Telegram.WebApp.sendData(JSON.stringify({
    action: "claim_team",
    team: team,
    username: username
  }));

  const handler = (event) => {
    if (event.data === "CLAIM_SUCCESS") {
      slot.querySelector('.username').textContent = username;
      slot.classList.add('claimed');
      slot.onclick = null;
    } else if (event.data.startsWith("DENIED")) {
      alert(event.data);
    }
    Telegram.WebApp.offEvent('message', handler);
  };

  Telegram.WebApp.onEvent('message', handler);
}

// Hook into showGame
const originalShowGame = showGame;
showGame = function(gameId) {
  originalShowGame(gameId);
  if (gameId === 'football') {
    fetchCardState();  // load real state from bot
  }
};
