document.addEventListener('DOMContentLoaded', () => {
  const outside = document.getElementById('view-outside');
  const inside = document.getElementById('view-inside');
  const enterBtn = document.getElementById('enter-btn');

  // Force start on outside
  outside.style.display = 'flex';
  outside.classList.add('active');
  outside.style.opacity = '1';
  inside.style.display = 'none';
  inside.classList.remove('active');
  inside.style.opacity = '0';

  // Hide games
  document.querySelectorAll('.game-screen').forEach(screen => {
    screen.style.display = 'none';
    screen.classList.remove('visible');
  });

  // Enter pub
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

  // Show game tab
  window.showGame = function(gameId) {
    const pub = document.getElementById('view-inside');
    pub.style.opacity = '0';

    setTimeout(() => {
      pub.style.display = 'none';
      pub.classList.remove('active');

      const gameScreen = document.getElementById('game-' + gameId);
      if (!gameScreen) {
        console.error("Game screen missing for", gameId);
        return;
      }

      gameScreen.style.display = 'block';
      gameScreen.classList.add('visible');
      gameScreen.style.opacity = '1';

      if (gameId === 'football') {
        loadFootballCard();
      }
    }, 800);
  };

  // Back to pub
  window.backToPub = function() {
    document.querySelectorAll('.game-screen').forEach(screen => {
      screen.style.opacity = '0';
    });

    setTimeout(() => {
      document.querySelectorAll('.game-screen').forEach(screen => {
        screen.style.display = 'none';
        screen.classList.remove('visible');
      });

      inside.style.display = 'flex';
      inside.classList.add('active');
      inside.style.opacity = '1';
    }, 800);
  };

  // Football teams
  const footballTeams = [
    "Arsenal", "Ajax", "Bournemouth", "Brentford", "Brighton", "Burnley",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool", "Luton",
    "Man City", "Man United", "Newcastle", "Nottingham Forest", "Sheffield Utd",
    "Tottenham", "West Ham", "Wolves", "Leicester", "Leeds", "Southampton",
    "Blackburn", "Birmingham", "Coventry", "Ipswich", "Middlesbrough", "Norwich",
    "Preston", "QPR", "Sheffield Wed"
  ];

  // Load grid
  function loadFootballCard() {
    const grid = document.getElementById('football-grid');
    if (!grid) return;

    // Ask bot for current state
    Telegram.WebApp.sendData(JSON.stringify({ action: "get_card_state" }));

    const handler = (event) => {
      if (event.data.startsWith("CARD_STATE:")) {
        const state = JSON.parse(event.data.split("CARD_STATE:")[1]);
        renderFootballGrid(state);
        Telegram.WebApp.offEvent('message', handler);
      }
    };

    Telegram.WebApp.onEvent('message', handler);

    setTimeout(() => {
      Telegram.WebApp.offEvent('message', handler);
    }, 5000);
  }

  function renderFootballGrid(state) {
    const grid = document.getElementById('football-grid');
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
    const username = Telegram.WebApp.initDataUnsafe.user;
    if (!user || !user.username) {
      alert("No Username? Can't claim.");
      return;
  }

  const username = '@' + user.username;

  if (!confirm(`Claim ${team} for $1 as ${username}?`)) return;

  Telegram.WebApp.sendData(JSON.stringify({
    action: "claim_team",
    team: team,
    username: username
  }));

  const handler = (event) => {
    if (event.data === "CLAIM_ SUCCESS") {
      slot.querySelector('.username').textContent = username;
      slot.classList.add('claimed');
      slot.onclick = null;
    } else if (event.data.startsWith("CLAIM_DENIED")) {
      alert(event.data);
    }
    Telegram.WebApp.offEvent('message', handler);
  };

  Telegram.WebApp.onEvent('message', handler);
}
